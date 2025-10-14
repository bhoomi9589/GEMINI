import asyncio
import logging
import streamlit as st
import threading
import uuid
import time
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

def initialize_session_state():
    """Initialize all session state variables"""
    if 'transcript' not in st.session_state:
        st.session_state.transcript = []

    if 'session_active' not in st.session_state:
        st.session_state.session_active = False

    if 'webrtc_component_key' not in st.session_state:
        st.session_state.webrtc_component_key = f"gemini-live-{uuid.uuid4().hex[:8]}"

    if 'last_analysis_time' not in st.session_state:
        st.session_state.last_analysis_time = 0

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

# Initialize session state first
initialize_session_state()

# --- Callback Functions ---

def start_session_callback():
    """Start the Gemini session."""
    try:
        success = st.session_state.gemini_live.start_session()
        if success:
            st.session_state.session_active = True
            transcript_queue.put(('system', "🚀 Gemini session started successfully!"))
        else:
            st.session_state.session_active = False
            transcript_queue.put(('error', "Failed to start session"))
        
    except Exception as e:
        st.error(f"Error starting session: {e}")
        st.session_state.session_active = False

def stop_session_callback():
    """Stop the Gemini session."""
    try:
        st.session_state.gemini_live.stop_session()
        st.session_state.session_active = False
        transcript_queue.put(('system', "🛑 Session stopped successfully"))
        
    except Exception as e:
        st.error(f"Error stopping session: {e}")
        transcript_queue.put(('error', f"Stop error: {str(e)}"))

def video_frame_callback(frame):
    """Process video frames from WebRTC."""
    # Safe session state access
    try:
        session_active = getattr(st.session_state, 'session_active', False)
        gemini_live = getattr(st.session_state, 'gemini_live', None)
        
        if session_active and gemini_live:
            try:
                gemini_live.send_video_frame(frame)
                
                # Auto-analyze frame every 5 seconds
                current_time = time.time()
                last_analysis_time = getattr(st.session_state, 'last_analysis_time', 0)
                
                if current_time - last_analysis_time > 5:
                    def analyze_frame():
                        try:
                            analysis = gemini_live.get_frame_analysis(
                                "Briefly describe what you see in this frame."
                            )
                            transcript_queue.put(('ai', f"👁️ I see: {analysis}"))
                        except Exception as e:
                            print(f"Analysis error: {e}")
                    
                    # Run analysis in background
                    thread = threading.Thread(target=analyze_frame)
                    thread.daemon = True
                    thread.start()
                    
                    st.session_state.last_analysis_time = current_time
                    
            except Exception as e:
                print(f"⚠️ Error processing video frame: {e}")
    except Exception as e:
        print(f"⚠️ Error in video callback: {e}")
    
    return frame

def audio_frame_callback(frame):
    """Process audio frames from WebRTC."""
    # Safe session state access
    try:
        session_active = getattr(st.session_state, 'session_active', False)
        gemini_live = getattr(st.session_state, 'gemini_live', None)
        
        if session_active and gemini_live:
            try:
                gemini_live.send_audio_frame(frame)
            except Exception as e:
                print(f"⚠️ Error processing audio frame: {e}")
    except Exception as e:
        print(f"⚠️ Error in audio callback: {e}")
    
    return frame

# --- Process Queue Updates ---
updates_processed = 0
max_updates_per_cycle = 5

while not transcript_queue.empty() and updates_processed < max_updates_per_cycle:
    try:
        event_type, data = transcript_queue.get_nowait()
        timestamp = time.strftime("%H:%M:%S")
        
        st.session_state.transcript.append({
            'type': event_type,
            'content': data,
            'timestamp': timestamp
        })
        updates_processed += 1
    except:
        break

# Limit transcript size
if len(st.session_state.transcript) > 50:
    st.session_state.transcript = st.session_state.transcript[-50:]

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