import asyncio
import base64
import io
import logging
import os
import streamlit as st
from PIL import Image
import av

# Updated imports for Google Generative AI
import google.generativeai as genai
from google.generativeai import types

class GeminiLive:
    """
    Manages all backend logic for the Gemini LiveConnect session.
    This class is completely independent of Streamlit or Flask.
    """
    def __init__(self):
        # Initialize API key - try multiple sources for compatibility
        api_key = None
        
        # Try 1: Environment variable (local development with .env)
        api_key = os.getenv("GEMINI_API_KEY")
        
        # Try 2: Streamlit secrets (cloud deployment)
        if not api_key:
            try:
                api_key = st.secrets["GEMINI_API_KEY"]
            except (KeyError, AttributeError):
                pass
        
        # Try 3: Check if it's still a placeholder
        if not api_key or api_key == "your_actual_gemini_api_key_here":
            raise ValueError(
                "🔑 GEMINI_API_KEY not found!\n\n"
                "📍 Local Development: Set GEMINI_API_KEY in your .env file\n"
                "☁️ Streamlit Cloud: Add GEMINI_API_KEY to app secrets\n"
                "🔗 Get API key: https://makersuite.google.com/app/apikey"
            )
        
        # Configure Gemini client with correct method
        genai.configure(api_key=api_key)
        self.model_name = "gemini-2.0-flash-exp"
        
        # Initialize the model
        self.model = genai.GenerativeModel(self.model_name)
        
        # Session state
        self.session = None
        self.running = False
        self.chat_session = None

    def start_session(self):
        """Starts a new Gemini chat session (simplified for compatibility)."""
        print("✅ Starting Gemini session...")
        self.running = True
        
        try:
            # Start a chat session
            self.chat_session = self.model.start_chat(history=[])
            print("✅ Connected to Gemini successfully!")
            return True
            
        except Exception as e:
            print(f"❌ Error starting session: {e}")
            self.running = False
            self.chat_session = None
            raise Exception(f"Failed to start Gemini session: {str(e)}")

    def stop_session(self):
        """Stops the current session."""
        print("🛑 Stopping Gemini session...")
        self.running = False
        self.chat_session = None
        print("✅ Session stopped cleanly")

    def send_text_message(self, message):
        """Send a text message to Gemini and get response."""
        if not self.chat_session or not self.running:
            return "Session not active. Please start a session first."
        
        try:
            response = self.chat_session.send_message(message)
            return response.text
        except Exception as e:
            print(f"⚠️ Error sending message: {e}")
            return f"Error: {str(e)}"

    def send_image_with_text(self, image, text="What do you see in this image?"):
        """Send an image with text to Gemini."""
        if not self.running:
            return "Session not active. Please start a session first."
        
        try:
            # Convert PIL image if needed
            if hasattr(image, 'save'):
                # It's a PIL image
                response = self.model.generate_content([text, image])
            else:
                # Convert other formats to PIL
                pil_image = Image.fromarray(image)
                response = self.model.generate_content([text, pil_image])
            
            return response.text
        except Exception as e:
            print(f"⚠️ Error processing image: {e}")
            return f"Error processing image: {str(e)}"

    # Simplified frame processing for compatibility
    def send_video_frame(self, frame):
        """Process video frame (simplified)."""
        if not self.running:
            return
        
        try:
            # Convert video frame to PIL Image
            pil_image = frame.to_image()
            
            # Store the latest frame for processing
            self.latest_frame = pil_image
            
        except Exception as e:
            print(f"⚠️ Error processing video frame: {e}")

    def send_audio_frame(self, frame):
        """Process audio frame (placeholder for future implementation)."""
        if not self.running:
            return
        
        # Audio processing can be added here when supported
        pass

    def get_frame_analysis(self, prompt="Describe what you see in the current frame"):
        """Analyze the current video frame."""
        if hasattr(self, 'latest_frame') and self.latest_frame:
            return self.send_image_with_text(self.latest_frame, prompt)
        else:
            return "No frame available for analysis."