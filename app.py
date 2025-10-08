# app.py
import streamlit as st
import asyncio
from dotenv import load_dotenv
import threading

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

# --- Helper Functions for Async Operations ---

def run_async_in_thread(coro):
    """Run an async coroutine in a background thread with its own event loop."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()

def start_response_listener(callback):
    """Start listening for responses in a background thread."""
    def listener_thread():
        run_async_in_thread(st.session_state.gemini_live.receive_responses(callback))
    
    thread = threading.Thread(target=listener_thread, daemon=True)
    thread.start()
    return thread

# --- Callback Functions ---
# These functions are the "glue" between the UI and the backend.

def start_session_callback():
    """Called when the 'Start Session' button is clicked."""
    # Run the async start_session method in a thread
    threading.Thread(
        target=run_async_in_thread,
        args=(st.session_state.gemini_live.start_session(),),
        daemon=True
    ).start()
    
    # Start the response listener thread
    if st.session_state.response_thread is None or not st.session_state.response_thread.is_alive():
        st.session_state.response_thread = start_response_listener(ui_update_callback)

def stop_session_callback():
    """Called when the 'Stop Session' button is clicked."""
    st.session_state.gemini_live.stop_session()
    # Clear the transcript when the session stops
    st.session_state.transcript = []
    st.session_state.response_thread = None

def ui_update_callback(event_type, data):
    """
    This function is passed to the backend to allow it to update the UI's state.
    """
    if event_type == "error":
        st.error(data)
    elif event_type == "text":
        st.session_state.transcript.append(f"**🤖 Gemini:** {data}")
    elif event_type == "tool":
        st.session_state.transcript.append(f"*{data}*")
    
    # Trigger a UI refresh to show the new transcript entry
    if 'rerun_needed' not in st.session_state:
        st.session_state.rerun_needed = True

# --- Main Application Execution ---

# Check if a rerun is needed from a background callback
if st.session_state.get('rerun_needed', False):
    st.session_state.rerun_needed = False
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