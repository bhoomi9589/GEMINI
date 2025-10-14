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

# Load environment variables (for local development)
load_dotenv()

# Thread-safe queue for async communication
transcript_queue = Queue()

# --- Session State Initialization ---
if 'transcript' not in st.session_state:
    st.session_state.transcript = []

if 'session_active' not in st.session_state:
    st.session_state.session_active = False

if 'webrtc_component_key' not in st.session_state:
    st.session_state.webrtc_component_key = f"gemini-live-{uuid.uuid4().hex[:8]}"

# Initialize GeminiLive with proper error handling
if 'gemini_live' not in st.session_state:
    try:
        st.session_state.gemini_live = GeminiLive()
        # Only show success message once
        if 'api_initialized' not in st.session_state:
            st.success("✅ Gemini API connected successfully!")
            st.session_state.api_initialized = True
    except ValueError as e:
        # Handle API key configuration errors
        st.error("❌ **API Key Configuration Error**")
        
        # Parse the error message to show specific instructions
        error_msg = str(e)
        if "GEMINI_API_KEY not found" in error_msg:
            st.markdown("### 🔑 **Setup Instructions:**")
            
            # Check if running locally or on cloud
            try:
                # Try to detect if we're on Streamlit Cloud
                if hasattr(st, 'secrets') and st.secrets:
                    # Running on Streamlit Cloud
                    st.info("☁️ **You're on Streamlit Cloud** - Add your API key to app secrets:")
                    st.code("""
Go to: Manage app → Settings → Secrets
Add: GEMINI_API_KEY = "your_actual_api_key_here"
                    """)
                else:
                    # Running locally
                    st.info("📍 **Local Development** - Set your API key in .env file:")
                    st.code("GEMINI_API_KEY=your_actual_api_key_here")
            except:
                # Show both options if we can't detect
                st.info("📍 **Local Development:** Set GEMINI_API_KEY in your .env file")
                st.info("☁️ **Streamlit Cloud:** Add GEMINI_API_KEY to app secrets")
            
            st.info("🔗 **Get your API key:** https://makersuite.google.com/app/apikey")
            st.warning("⚠️ **Important:** Never commit your API key to Git!")
        else:
            st.error(f"Configuration error: {error_msg}")
        
        st.stop()
    except Exception as e:
        # Handle other initialization errors
        st.error(f"❌ **Unexpected Error:** {str(e)}")
        st.info("💡 **Troubleshooting:**")
        st.info("1. Check your internet connection")
        st.info("2. Verify your API key is valid")
        st.info("3. Try refreshing the page")
        st.stop()

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
                # Add error to transcript queue for UI display
                transcript_queue.put(('error', f"Session failed: {str(e)}"))
        
        # Run in background thread
        thread = threading.Thread(target=lambda: loop.run_until_complete(start_and_listen()))
        thread.daemon = True
        thread.start()
        
        # Add success message to transcript
        transcript_queue.put(('system', "🚀 Starting Gemini Live session..."))
        
    except Exception as e:
        st.error(f"Error starting session: {e}")
        st.session_state.session_active = False

def stop_session_callback():
    """Stop the Gemini Live session."""
    try:
        st.session_state.gemini_live.stop_session()
        st.session_state.session_active = False
        
        # Add stop message to transcript
        transcript_queue.put(('system', "🛑 Session stopped successfully"))
        
    except Exception as e:
        st.error(f"Error stopping session: {e}")
        transcript_queue.put(('error', f"Stop error: {str(e)}"))

def video_frame_callback(frame):
    """Process video frames from WebRTC."""
    if st.session_state.session_active and hasattr(st.session_state, 'gemini_live'):
        try:
            st.session_state.gemini_live.send_video_frame(frame)
        except Exception as e:
            print(f"⚠️ Error processing video frame: {e}")
    return frame

def audio_frame_callback(frame):
    """Process audio frames from WebRTC."""
    if st.session_state.session_active and hasattr(st.session_state, 'gemini_live'):
        try:
            st.session_state.gemini_live.send_audio_frame(frame)
        except Exception as e:
            print(f"⚠️ Error processing audio frame: {e}")
    return frame

# --- Process Queue Updates ---
# Update transcript from queue (non-blocking)
updates_processed = 0
max_updates_per_cycle = 5  # Prevent UI lag

while not transcript_queue.empty() and updates_processed < max_updates_per_cycle:
    try:
        event_type, data = transcript_queue.get_nowait()
        timestamp = f"{st.session_state.get('current_time', 'Now')}"
        
        st.session_state.transcript.append({
            'type': event_type,
            'content': data,
            'timestamp': timestamp
        })
        updates_processed += 1
    except:
        break

# Limit transcript size to prevent memory issues
if len(st.session_state.transcript) > 100:
    st.session_state.transcript = st.session_state.transcript[-100:]

# --- Main UI ---
try:
    draw_interface(
        start_session_callback=start_session_callback,
        stop_session_callback=stop_session_callback,
        video_frame_callback=video_frame_callback,
        audio_frame_callback=audio_frame_callback,
        is_running=st.session_state.session_active,
        transcript=st.session_state.transcript
    )
except Exception as e:
    st.error(f"❌ **UI Error:** {str(e)}")
    st.info("💡 Try refreshing the page. If the problem persists, check the console for details.")
    
    # Show debug info in expander
    with st.expander("🔧 Debug Information"):
        st.code(f"Error details: {str(e)}")
        st.code(f"Session state keys: {list(st.session_state.keys())}")