import streamlit as st
import asyncio
import threading
from queue import Queue
import logging
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
if 'gemini_live' not in st.session_state:
    try:
        st.session_state.gemini_live = GeminiLive()
    except ValueError as e:
        st.error(f"❌ Configuration Error: {e}")
        st.info("💡 Please set your GEMINI_API_KEY in Streamlit secrets or .env file")
        st.stop()

if 'transcript' not in st.session_state:
    st.session_state.transcript = []

if 'session_active' not in st.session_state:
    st.session_state.session_active = False

# --- Callback Functions ---

def ui_update_callback(event_type, data):
    """
    Callback for backend to update UI state.
    Thread-safe via queue.
    """
    try:
        transcript_queue.put((event_type, data))
    except Exception as e:
        print(f"Queue error: {e}")

def start_session_callback():
    """Called when 'Start Session' button is clicked."""
    def session_thread():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            # Start session and listen for responses
            loop.run_until_complete(st.session_state.gemini_live.start_session())
            loop.run_until_complete(
                st.session_state.gemini_live.receive_responses(ui_update_callback)
            )
        except Exception as e:
            ui_update_callback("error", f"Session error: {e}")
        finally:
            try:
                loop.close()
            except:
                pass
    
    # Mark session as active
    st.session_state.session_active = True
    
    # Start background thread
    threading.Thread(target=session_thread, daemon=True).start()

def stop_session_callback():
    """Called when 'Stop Session' button is clicked."""
    st.session_state.gemini_live.stop_session()
    st.session_state.session_active = False

# --- Process Transcript Queue ---
while not transcript_queue.empty():
    try:
        event_type, data = transcript_queue.get_nowait()
        
        if event_type == "error":
            st.error(f"❌ {data}")
        elif event_type == "text":
            st.session_state.transcript.append(f"**🤖 Gemini:** {data}")
        elif event_type == "tool":
            st.session_state.transcript.append(f"*🛠️ {data}*")
        
    except Exception as e:
        print(f"Error processing queue: {e}")
        break

# --- Main Application ---

# Draw the UI
draw_interface(
    start_session_callback=start_session_callback,
    stop_session_callback=stop_session_callback,
    video_frame_callback=st.session_state.gemini_live.send_video_frame,
    audio_frame_callback=st.session_state.gemini_live.send_audio_frame,
    is_running=st.session_state.session_active,
    transcript=st.session_state.transcript
)