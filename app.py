import streamlit as st
import threading
import asyncio
from queue import Queue

from live import GeminiLive
from streamlit_webrtc import webrtc_streamer, WebRtcMode

# Thread-safe queue for communication between background thread and main thread
transcript_queue = Queue()

def ui_update_callback(event_type, content):
    """Callback to queue UI updates from the background thread."""
    transcript_queue.put((event_type, content))

def run_async_in_thread(coro):
    """Run an async coroutine in a new thread with its own event loop."""
    def thread_func():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(coro)
        finally:
            loop.close()
    
    thread = threading.Thread(target=thread_func, daemon=True)
    thread.start()
    return thread

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
    st.title("🎥 Gemini 2.0 Live - Voice & Video Chat")
    
    # ✅ Initialize ALL session state variables FIRST
    if "gemini_live" not in st.session_state:
        st.session_state.gemini_live = GeminiLive()
        st.session_state.transcript = []
        st.session_state.session_active = False
        st.session_state.webrtc_initialized = False
        st.session_state.webrtc_playing = False
    
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
        # ✅ Only create WebRTC component after session state is ready
        if st.session_state.gemini_live:
            webrtc_ctx = webrtc_streamer(
                key="gemini-live-stream",
                mode=WebRtcMode.SENDRECV,
                rtc_configuration={"iceServers": [{"urls": ["stun:stun.l.google.com:19302"]}]},
                media_stream_constraints={
                    "video": {"width": {"ideal": 640}, "height": {"ideal": 480}},
                    "audio": True
                },
                video_frame_callback=st.session_state.gemini_live.send_video_frame,
                audio_frame_callback=st.session_state.gemini_live.send_audio_frame,
                async_processing=False,
                sendback_audio=False,
            )
            
            # ✅ Mark as initialized after first render
            if not st.session_state.webrtc_initialized:
                st.session_state.webrtc_initialized = True
            
            # Show WebRTC status
            if webrtc_ctx and webrtc_ctx.state.playing:
                st.success("🟢 Camera & Microphone Active")
            else:
                st.info("⚪ Click START to begin")
        else:
            st.warning("⚠️ Initializing...")
    
    with col2:
        st.subheader("🎛️ Controls")
        
        # ✅ Only show controls after WebRTC is initialized
        if st.session_state.get("webrtc_initialized", False):
            # Start Session button
            if st.button("▶️ Start Session", disabled=st.session_state.session_active):
                st.session_state.session_active = True
                start_gemini_session_and_listener(st.session_state.gemini_live)
                st.success("Session started!")
                st.rerun()
            
            # Stop Session button
            if st.button("⏹️ Stop Session", disabled=not st.session_state.session_active):
                st.session_state.gemini_live.stop_session()
                st.session_state.session_active = False
                st.info("Session stopped!")
                st.rerun()
            
            # Clear Transcript button
            if st.button("🗑️ Clear Transcript"):
                st.session_state.transcript = []
                st.rerun()
        else:
            st.info("⏳ Initializing WebRTC component...")
    
    # Display transcript
    st.subheader("📝 Conversation")
    if st.session_state.transcript:
        for message in st.session_state.transcript:
            role = message["role"]
            content = message["content"]
            if role == "assistant":
                st.chat_message("assistant").write(content)
            else:
                st.chat_message("user").write(content)
    else:
        st.info("Start a session and speak to begin the conversation!")

if __name__ == "__main__":
    main()