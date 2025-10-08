# app.py
import streamlit as st
import asyncio
from dotenv import load_dotenv
import threading
import queue

# Import the backend logic and the UI drawing function
from live import GeminiLive
from ui import draw_interface

# Load environment variables from .env file for local development
load_dotenv()

# --- Session State Initialization ---
# This ensures that our backend object and transcript persist across Streamlit reruns.
if 'gemini_live' not in st.session_state:
    try:
        # Instantiate our backend logic class
        st.session_state.gemini_live = GeminiLive()
    except ValueError as e:
        # If API key is missing, show an error and stop.
        st.error(str(e))
        st.stop()

if 'transcript' not in st.session_state:
    st.session_state.transcript = []

if 'event_loop' not in st.session_state:
    st.session_state.event_loop = None

if 'response_thread' not in st.session_state:
    st.session_state.response_thread = None

if 'transcript_queue' not in st.session_state:
    st.session_state.transcript_queue = queue.Queue()

# --- Helper Functions for Async Operations ---

def run_async_in_thread(coro):
    """Run an async coroutine in a background thread with its own event loop."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()

def start_response_listener(gemini_live_instance, transcript_queue):
    """Start listening for responses in a background thread."""
    def ui_update_callback(event_type, data):
        """Thread-safe callback that uses a queue instead of session_state."""
        transcript_queue.put((event_type, data))
    
    def listener_thread():
        run_async_in_thread(gemini_live_instance.receive_responses(ui_update_callback))
    
    thread = threading.Thread(target=listener_thread, daemon=True)
    thread.start()
    return thread

# --- Callback Functions ---
# These functions are the "glue" between the UI and the backend.

def start_session_callback():
    """Called when the 'Start Session' button is clicked."""
    # Get references before starting thread
    gemini_live = st.session_state.gemini_live
    transcript_queue = st.session_state.transcript_queue
    
    # Run the async start_session method in a thread
    threading.Thread(
        target=run_async_in_thread,
        args=(gemini_live.start_session(),),
        daemon=True
    ).start()
    
    # Start the response listener thread with queue for thread-safe communication
    if st.session_state.response_thread is None or not st.session_state.response_thread.is_alive():
        st.session_state.response_thread = start_response_listener(gemini_live, transcript_queue)

def stop_session_callback():
    """Called when the 'Stop Session' button is clicked."""
    st.session_state.gemini_live.stop_session()
    # Clear the transcript when the session stops
    st.session_state.transcript = []
    st.session_state.response_thread = None
    # Clear the queue
    while not st.session_state.transcript_queue.empty():
        try:
            st.session_state.transcript_queue.get_nowait()
        except queue.Empty:
            break

# --- Main Application Execution ---

# Process any messages from the background thread
messages_processed = False
while not st.session_state.transcript_queue.empty():
    try:
        event_type, data = st.session_state.transcript_queue.get_nowait()
        if event_type == "error":
            st.error(data)
        elif event_type == "text":
            st.session_state.transcript.append(f"**🤖 Gemini:** {data}")
            messages_processed = True
        elif event_type == "tool":
            st.session_state.transcript.append(f"*{data}*")
            messages_processed = True
    except queue.Empty:
        break

# If we processed messages, trigger a rerun to show them
if messages_processed:
    st.rerun()

# Draw the user interface, passing in the necessary functions and state
draw_interface(
    start_session_callback=start_session_callback,
    stop_session_callback=stop_session_callback,
    video_frame_callback=st.session_state.gemini_live.send_video_frame,
    audio_frame_callback=st.session_state.gemini_live.send_audio_frame,
    is_running=st.session_state.gemini_live.running,
    transcript=st.session_state.transcript
)