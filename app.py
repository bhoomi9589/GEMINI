import streamlit as st
import threading
import asyncio
from queue import Queue
import logging
import sys

from live import GeminiLive
from streamlit_webrtc import webrtc_streamer, WebRtcMode

# ✅ Suppress asyncio errors from streamlit-webrtc
logging.basicConfig(
    level=logging.WARNING,
    format='%(levelname)s: %(message)s'
)
logging.getLogger('asyncio').setLevel(logging.CRITICAL)

# Thread-safe queue
transcript_queue = Queue()

def ui_update_callback(event_type, content):
    """Queue UI updates from background thread."""
    try:
        transcript_queue.put((event_type, content))
    except Exception as e:
        print(f"Queue error: {e}", file=sys.stderr)

def start_gemini_session_and_listener(gemini_live_instance):
    """Start Gemini session in background thread."""
    def session_thread():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(gemini_live_instance.start_session())
            loop.run_until_complete(gemini_live_instance.receive_responses(ui_update_callback))
        except Exception as e:
            ui_update_callback("error", f"Session error: {e}")
        finally:
            try:
                loop.close()
            except:
                pass
    
    threading.Thread(target=session_thread, daemon=True).start()

def main():
    st.set_page_config(
        page_title="Gemini 2.0 Live",
        page_icon="🎥",
        layout="wide"
    )
    
    # Initialize session state ONCE
    if "initialized" not in st.session_state:
        st.session_state.initialized = True
        st.session_state.gemini_live = GeminiLive()
        st.session_state.transcript = []
        st.session_state.session_active = False
    
    # Process transcript queue
    while not transcript_queue.empty():
        try:
            event_type, content = transcript_queue.get_nowait()
            if event_type == "text":
                st.session_state.transcript.append({"role": "assistant", "content": content})
            elif event_type == "error":
                st.error(content)
        except:
            break
    
    st.title("🎥 Gemini 2.0 Live - Voice & Video Chat")
    
    # Layout
    col1, col2 = st.columns([3, 1])
    
    with col1:
        # WebRTC component with error handling
        try:
            ctx = webrtc_streamer(
                key="gemini-webrtc",
                mode=WebRtcMode.SENDRECV,
                rtc_configuration={
                    "iceServers": [
                        {"urls": ["stun:stun.l.google.com:19302"]},
                        {"urls": ["stun:stun1.l.google.com:19302"]}
                    ],
                    "iceTransportPolicy": "all"
                },
                media_stream_constraints={
                    "video": {
                        "width": {"ideal": 640, "max": 1280},
                        "height": {"ideal": 480, "max": 720}
                    },
                    "audio": {
                        "echoCancellation": True,
                        "noiseSuppression": True
                    }
                },
                video_frame_callback=st.session_state.gemini_live.send_video_frame,
                audio_frame_callback=st.session_state.gemini_live.send_audio_frame,
                async_processing=False,
            )
            
            if ctx and ctx.state.playing:
                st.success("🟢 Streaming Active")
            else:
                st.info("⚪ Click START above to begin")
                
        except Exception as e:
            st.error(f"WebRTC Error: {e}")
            st.info("Please refresh the page if issues persist")
    
    with col2:
        st.markdown("### Controls")
        
        # Buttons with error handling
        col_a, col_b = st.columns(2)
        
        with col_a:
            if st.button("▶️ Start", disabled=st.session_state.session_active, use_container_width=True):
                try:
                    st.session_state.session_active = True
                    start_gemini_session_and_listener(st.session_state.gemini_live)
                    st.success("Started!")
                except Exception as e:
                    st.error(f"Start error: {e}")
                    st.session_state.session_active = False
                st.rerun()
        
        with col_b:
            if st.button("⏹️ Stop", disabled=not st.session_state.session_active, use_container_width=True):
                try:
                    st.session_state.gemini_live.stop_session()
                    st.session_state.session_active = False
                    st.info("Stopped")
                except Exception as e:
                    st.error(f"Stop error: {e}")
                st.rerun()
        
        if st.button("🗑️ Clear", disabled=not st.session_state.transcript, use_container_width=True):
            st.session_state.transcript = []
            st.rerun()
        
        # Status
        st.markdown("---")
        st.markdown("**Status:**")
        if st.session_state.session_active:
            st.success("🟢 Session Active")
        else:
            st.info("⚪ Session Inactive")
    
    # Transcript
    st.markdown("---")
    st.markdown("### 📝 Transcript")
    
    if st.session_state.transcript:
        for msg in st.session_state.transcript:
            with st.chat_message(msg["role"]):
                st.write(msg["content"])
    else:
        st.info("💬 Start a session to see conversation")
    
    # Footer with troubleshooting
    with st.expander("🔧 Troubleshooting"):
        st.markdown("""
        **If you see errors:**
        1. **Refresh the page** (F5)
        2. **Allow camera/microphone** permissions
        3. **Use Chrome or Edge** browser (recommended)
        4. **Check your internet connection**
        
        **Browser console warnings** about `asyncio` are normal and don't affect functionality.
        """)

if __name__ == "__main__":
    main()