import asyncio
import logging
import streamlit as st
import threading
import uuid
from queue import Queue
from dotenv import load_dotenv

# Import backend logic and UI
from live import GeminiLive
from ui import draw_interface

# Configure logging
logging.basicConfig(level=logging.WARNING, format='%(levelname)s: %(message)s')
logging.getLogger('asyncio').setLevel(logging.CRITICAL)

# Load environment variables
load_dotenv()

# Thread-safe queue for async communication
transcript_queue = Queue()

# --- Session State Initialization ---
if 'transcript' not in st.session_state:
    st.session_state.transcript = []

if 'session_active' not in st.session_state:
    st.session_state.session_active = False

# ✅ Add this safety check
if 'webrtc_component_key' not in st.session_state:
    st.session_state.webrtc_component_key = f"gemini-live-{uuid.uuid4().hex[:8]}"

if 'gemini_live' not in st.session_state:
    st.session_state.gemini_live = GeminiLive()

# --- Callback Functions ---

def ui_update_callback(event_type, data):
    """Called by GeminiLive when new data arrives."""
    if event_type == 'text':
        # Add AI response to transcript
        transcript_queue.put(('ai', data))
    elif event_type == 'audio':
        # Handle audio response (could play audio)
        transcript_queue.put(('ai_audio', 'Audio response received'))
    elif event_type == 'error':
        transcript_queue.put(('error', f"Error: {data}"))

def start_session_callback():
    """Start the Gemini Live session."""
    try:
        # Start session in background thread
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        async def start_and_listen():
            try:
                await st.session_state.gemini_live.start_session()
                st.session_state.session_active = True
                
                # Start listening for responses
                await st.session_state.gemini_live.receive_responses(ui_update_callback)
            except Exception as e:
                st.session_state.session_active = False
                st.error(f"Failed to start session: {e}")
        
        # Run in background thread
        thread = threading.Thread(target=lambda: loop.run_until_complete(start_and_listen()))
        thread.daemon = True
        thread.start()
        
    except Exception as e:
        st.error(f"Error starting session: {e}")
        st.session_state.session_active = False

def stop_session_callback():
    """Stop the Gemini Live session."""
    try:
        st.session_state.gemini_live.stop_session()
        st.session_state.session_active = False
        st.success("Session stopped successfully!")
    except Exception as e:
        st.error(f"Error stopping session: {e}")

def video_frame_callback(frame):
    """Process video frames from WebRTC."""
    if st.session_state.session_active:
        st.session_state.gemini_live.send_video_frame(frame)
    return frame

def audio_frame_callback(frame):
    """Process audio frames from WebRTC."""
    if st.session_state.session_active:
        st.session_state.gemini_live.send_audio_frame(frame)
    return frame

# --- Process Queue Updates ---
# Update transcript from queue
while not transcript_queue.empty():
    event_type, data = transcript_queue.get()
    if event_type in ['ai', 'ai_audio', 'error']:
        st.session_state.transcript.append({
            'type': event_type,
            'content': data,
            'timestamp': st.session_state.get('timestamp', 'Unknown')
        })

# --- Main UI ---
draw_interface(
    start_session_callback=start_session_callback,
    stop_session_callback=stop_session_callback,
    video_frame_callback=video_frame_callback,
    audio_frame_callback=audio_frame_callback,
    is_running=st.session_state.session_active,
    transcript=st.session_state.transcript
)