import streamlit as st
import threading
import asyncio
from queue import Queue
import time
import uuid

from live import GeminiLive
from streamlit_webrtc import webrtc_streamer, WebRtcMode

# Thread-safe queue for communication between background thread and main thread
transcript_queue = Queue()

def ui_update_callback(event_type, content):
    """Callback to queue UI updates from the background thread."""
    transcript_queue.put((event_type, content))

def start_gemini_session_and_listener(gemini_live_instance):
    """
    Starts the Gemini session and response listener in a background thread.
    Both run sequentially in the same thread to ensure proper coordination.
    """
    def session_thread():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            # First, connect the session
            loop.run_until_complete(gemini_live_instance.start_session())
            # Then, start listening for responses
            loop.run_until_complete(gemini_live_instance.receive_responses(ui_update_callback))
        except Exception as e:
            print(f"Error in session thread: {e}")
            ui_update_callback("error", f"Session error: {e}")
        finally:
            loop.close()
    
    thread = threading.Thread(target=session_thread, daemon=True)
    thread.start()
    return thread

def main():
    st.set_page_config(
        page_title="Gemini 2.0 Live",
        page_icon="🎥",
        layout="wide",
        initial_sidebar_state="collapsed"
    )
    
    st.title("🎥 Gemini 2.0 Live - Voice & Video Chat")
    
    # ✅ Initialize session state with a stable UUID-based key
    if "component_key" not in st.session_state:
        st.session_state.component_key = str(uuid.uuid4())
    
    if "gemini_live" not in st.session_state:
        st.session_state.gemini_live = GeminiLive()
        st.session_state.transcript = []
        st.session_state.session_active = False
        st.session_state.webrtc_started = False
    
    # Process any queued transcript updates
    while not transcript_queue.empty():
        event_type, content = transcript_queue.get()
        if event_type == "text":
            st.session_state.transcript.append({"role": "assistant", "content": content})
            st.rerun()
        elif event_type == "error":
            st.error(content)
    
    # Main UI
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("📹 Video & Audio")
        
        # ✅ Use stable UUID-based key that persists across reruns
        webrtc_ctx = webrtc_streamer(
            key=st.session_state.component_key,
            mode=WebRtcMode.SENDRECV,
            rtc_configuration={
                "iceServers": [{"urls": ["stun:stun.l.google.com:19302"]}]
            },
            media_stream_constraints={
                "video": {
                    "width": {"ideal": 640},
                    "height": {"ideal": 480},
                    "frameRate": {"ideal": 30, "max": 30}
                },
                "audio": {
                    "echoCancellation": True,
                    "noiseSuppression": True,
                    "autoGainControl": True,
                }
            },
            video_frame_callback=st.session_state.gemini_live.send_video_frame,
            audio_frame_callback=st.session_state.gemini_live.send_audio_frame,
            async_processing=False,
        )
        
        # Show status
        if webrtc_ctx and webrtc_ctx.state.playing:
            st.success("🟢 Camera & Microphone Active")
            st.session_state.webrtc_started = True
        elif webrtc_ctx:
            st.info("⚪ Click START above to begin")
        else:
            st.warning("⚠️ Loading WebRTC component...")
    
    with col2:
        st.subheader("🎛️ Controls")
        
        # Only enable buttons if WebRTC has started at least once
        can_control = st.session_state.get("webrtc_started", False)
        
        if not can_control:
            st.info("📌 Click START in the video player to enable controls")
        
        # Start Session button
        start_disabled = st.session_state.session_active or not can_control
        if st.button("▶️ Start Gemini Session", disabled=start_disabled, use_container_width=True):
            st.session_state.session_active = True
            start_gemini_session_and_listener(st.session_state.gemini_live)
            st.success("✅ Session started!")
            st.rerun()
        
        # Stop Session button
        stop_disabled = not st.session_state.session_active
        if st.button("⏹️ Stop Gemini Session", disabled=stop_disabled, use_container_width=True):
            st.session_state.gemini_live.stop_session()
            st.session_state.session_active = False
            st.info("⏹️ Session stopped")
            st.rerun()
        
        # Clear Transcript button
        if st.button("🗑️ Clear Transcript", disabled=not st.session_state.transcript, use_container_width=True):
            st.session_state.transcript = []
            st.rerun()
        
        # Status indicator
        st.divider()
        st.markdown("### Status")
        
        if st.session_state.session_active:
            st.success("🟢 **Gemini Session Active**")
        else:
            st.info("⚪ **Gemini Session Inactive**")
        
        if webrtc_ctx and webrtc_ctx.state.playing:
            st.success("🎥 **WebRTC Streaming**")
        else:
            st.info("📹 **WebRTC Waiting**")
    
    # Display transcript
    st.divider()
    st.subheader("📝 Conversation Transcript")
    
    if st.session_state.transcript:
        # Create a scrollable container
        transcript_container = st.container()
        with transcript_container:
            for idx, message in enumerate(st.session_state.transcript):
                role = message["role"]
                content = message["content"]
                if role == "assistant":
                    st.chat_message("assistant").write(content)
                else:
                    st.chat_message("user").write(content)
    else:
        st.info("💬 Start a Gemini session and speak to see the conversation here!")
    
    # Footer
    st.divider()
    st.caption("🚀 Powered by Google Gemini 2.0 Flash Exp | Built with Streamlit")

if __name__ == "__main__":
    main()