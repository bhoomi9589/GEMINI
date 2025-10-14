import os
import streamlit as st
from PIL import Image
import av
import base64
import io

# Try different import approaches
try:
    import google.generativeai as genai
    GENAI_AVAILABLE = True
except ImportError:
    try:
        # Fallback import
        from google import generativeai as genai
        GENAI_AVAILABLE = True
    except ImportError:
        GENAI_AVAILABLE = False
        st.error("❌ Google Generative AI library not available")

class GeminiLive:
    """
    Manages all backend logic for the Gemini session.
    Simplified version for better compatibility.
    """
    def __init__(self):
        if not GENAI_AVAILABLE:
            raise ImportError("Google Generative AI library not available")
            
        # Initialize API key - try multiple sources
        api_key = None
        
        # Try 1: Environment variable (local development)
        api_key = os.getenv("GEMINI_API_KEY")
        
        # Try 2: Streamlit secrets (cloud deployment)
        if not api_key:
            try:
                api_key = st.secrets["GEMINI_API_KEY"]
            except (KeyError, AttributeError, FileNotFoundError):
                pass
        
        # Validate API key
        if not api_key or api_key == "your_actual_gemini_api_key_here":
            raise ValueError(
                "🔑 GEMINI_API_KEY not found!\n\n"
                "📍 Local Development: Set GEMINI_API_KEY in your .env file\n"
                "☁️ Streamlit Cloud: Add GEMINI_API_KEY to app secrets\n"
                "🔗 Get API key: https://makersuite.google.com/app/apikey"
            )
        
        # Configure Gemini
        try:
            genai.configure(api_key=api_key)
            self.model = genai.GenerativeModel("gemini-1.5-flash")  # Use stable model
            print("✅ Gemini API configured successfully")
        except Exception as e:
            raise Exception(f"Failed to configure Gemini API: {str(e)}")
        
        # Session state
        self.running = False
        self.chat_session = None
        self.latest_frame = None

    def start_session(self):
        """Start a Gemini chat session."""
        try:
            self.chat_session = self.model.start_chat(history=[])
            self.running = True
            print("✅ Gemini session started")
            return True
        except Exception as e:
            print(f"❌ Failed to start session: {e}")
            self.running = False
            return False

    def stop_session(self):
        """Stop the session."""
        self.running = False
        self.chat_session = None
        print("🛑 Session stopped")

    def send_text_message(self, message):
        """Send text message to Gemini."""
        if not self.running or not self.chat_session:
            return "Session not active"
        
        try:
            response = self.chat_session.send_message(message)
            return response.text
        except Exception as e:
            return f"Error: {str(e)}"

    def send_image_with_text(self, image, text="What do you see?"):
        """Send image with text to Gemini."""
        if not self.running:
            return "Session not active"
        
        try:
            # Ensure we have a PIL Image
            if hasattr(image, 'save'):
                pil_image = image
            else:
                pil_image = Image.fromarray(image)
            
            # Generate content with image
            response = self.model.generate_content([text, pil_image])
            return response.text
        except Exception as e:
            return f"Error analyzing image: {str(e)}"

    def send_video_frame(self, frame):
        """Process video frame."""
        if not self.running:
            return
        
        try:
            # Convert frame to PIL Image
            self.latest_frame = frame.to_image()
        except Exception as e:
            print(f"Error processing video frame: {e}")

    def send_audio_frame(self, frame):
        """Process audio frame (placeholder)."""
        # Audio processing can be added later
        pass

    def get_frame_analysis(self, prompt="Describe what you see"):
        """Analyze the current frame."""
        if self.latest_frame:
            return self.send_image_with_text(self.latest_frame, prompt)
        return "No frame available"