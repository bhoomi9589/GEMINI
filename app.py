import streamlit as st
import threading
import asyncio
from queue import Queue
import logging

from live import GeminiLive
from streamlit_webrtc import webrtc_streamer, WebRtcMode

# Configure logging to suppress verbose output
logging.basicConfig(level=logging.WARNING)

# Thread-safe queue
transcript_queue = Queue()

def ui_update_callback(event_type, content):
    """Queue UI updates from background thread."""
    transcript_queue.put((event_type, content))

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
            loop.close()
    
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
        event_type, content = transcript_queue.get()
        if event_type == "text":
            st.session_state.transcript.append({"role": "assistant", "content": content})
        elif event_type == "error":
            st.error(content)
    
    st.title("🎥 Gemini 2.0 Live - Voice & Video Chat")
    
    # Layout
    col1, col2 = st.columns([3, 1])
    
    with col1:
        # WebRTC component with fixed key
        ctx = webrtc_streamer(
            key="gemini-webrtc",
            mode=WebRtcMode.SENDRECV,
            rtc_configuration={"iceServers": [{"urls": ["stun:stun.l.google.com:19302"]}]},
            media_stream_constraints={"video": True, "audio": True},
            video_frame_callback=st.session_state.gemini_live.send_video_frame,
            audio_frame_callback=st.session_state.gemini_live.send_audio_frame,
            async_processing=False,
        )
        
        if ctx and ctx.state.playing:
            st.success("🟢 Streaming")
        else:
            st.info("⚪ Click START above")
    
    with col2:
        st.markdown("### Controls")
        
        # Buttons
        if st.button("▶️ Start", disabled=st.session_state.session_active, use_container_width=True):
            st.session_state.session_active = True
            start_gemini_session_and_listener(st.session_state.gemini_live)
            st.rerun()
        
        if st.button("⏹️ Stop", disabled=not st.session_state.session_active, use_container_width=True):
            st.session_state.gemini_live.stop_session()
            st.session_state.session_active = False
            st.rerun()
        
        if st.button("🗑️ Clear", disabled=not st.session_state.transcript, use_container_width=True):
            st.session_state.transcript = []
            st.rerun()
        
        # Status
        st.markdown("---")
        if st.session_state.session_active:
            st.success("🟢 Active")
        else:
            st.info("⚪ Inactive")
    
    # Transcript
    st.markdown("---")
    st.markdown("### 📝 Transcript")
    
    if st.session_state.transcript:
        for msg in st.session_state.transcript:
            with st.chat_message(msg["role"]):
                st.write(msg["content"])
    else:
        st.info("Start a session to see conversation")

if __name__ == "__main__":
    main()