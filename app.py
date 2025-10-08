import streamlit as st
import threading
import asyncio
from queue import Queue
import time

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
    st.title("🎥 Gemini 2.0 Live - Voice & Video Chat")
    
    # ✅ Initialize ALL session state variables FIRST
    if "gemini_live" not in st.session_state:
        st.session_state.gemini_live = GeminiLive()
        st.session_state.transcript = []
        st.session_state.session_active = False
        st.session_state.webrtc_ready = False  # Track when WebRTC is truly ready
        st.session_state.init_timestamp = time.time()  # Add timestamp to force fresh component
    
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
        # ✅ Use timestamp-based unique key to prevent registration issues
        webrtc_key = f"gemini-live-{st.session_state.init_timestamp}"
        
        try:
            webrtc_ctx = webrtc_streamer(
                key=webrtc_key,
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
            
            # ✅ Mark as ready after component renders
            if webrtc_ctx:
                st.session_state.webrtc_ready = True
                
                # Show WebRTC status
                if webrtc_ctx.state.playing:
                    st.success("🟢 Camera & Microphone Active")
                else:
                    st.info("⚪ Click START to begin")
            else:
                st.warning("⚠️ Initializing WebRTC...")
                
        except Exception as e:
            st.error(f"WebRTC Error: {e}")
            st.session_state.webrtc_ready = False
    
    with col2:
        st.subheader("🎛️ Controls")
        
        # ✅ Only show controls after WebRTC is ready
        if st.session_state.get("webrtc_ready", False):
            # Start Session button
            if st.button("▶️ Start Session", disabled=st.session_state.session_active, key="start_btn"):
                st.session_state.session_active = True
                start_gemini_session_and_listener(st.session_state.gemini_live)
                st.success("Session started!")
                time.sleep(0.1)  # Small delay to ensure state update
                st.rerun()
            
            # Stop Session button
            if st.button("⏹️ Stop Session", disabled=not st.session_state.session_active, key="stop_btn"):
                st.session_state.gemini_live.stop_session()
                st.session_state.session_active = False
                st.info("Session stopped!")
                time.sleep(0.1)  # Small delay to ensure state update
                st.rerun()
            
            # Clear Transcript button
            if st.button("🗑️ Clear Transcript", key="clear_btn"):
                st.session_state.transcript = []
                st.rerun()
            
            # ✅ Add status indicator
            st.divider()
            if st.session_state.session_active:
                st.success("🟢 Session Active")
            else:
                st.info("⚪ Session Inactive")
        else:
            st.info("⏳ Initializing WebRTC component...")
            # ✅ Auto-refresh until ready
            if not st.session_state.get("webrtc_ready", False):
                time.sleep(0.5)
                st.rerun()
    
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