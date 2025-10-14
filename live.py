import asyncio
import base64
import io
import logging
import os
from PIL import Image
import av

from google import genai
from google.genai import types

class GeminiLive:
    """
    Manages all backend logic for the Gemini LiveConnect session.
    This class is completely independent of Streamlit or Flask.
    """
    def __init__(self):
        # Initialize API key
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY environment variable not set")
        
        # Configure Gemini client
        genai.configure(api_key=api_key)
        self.client = genai.Client()
        self.model = "gemini-2.0-flash-exp"
        
        # LiveConnect configuration
        self.config = types.LiveConnectConfig(
            response_modalities=["TEXT", "AUDIO"],
            system_instruction="You are a helpful AI assistant. Be conversational and engaging.",
        )
        
        # Session state
        self.session = None
        self.running = False
        self.event_loop = None

    async def start_session(self):
        """Starts a new Gemini LiveConnect session with improved error handling."""
        print("✅ Starting Gemini session...")
        self.running = True
        
        # Store the event loop
        self.event_loop = asyncio.get_event_loop()
        
        try:
            # Improved connection handling
            print("🔗 Connecting to Gemini Live API...")
            async_live = self.client.aio.live.connect(model=self.model, config=self.config)
            self.session = await async_live.__aenter__()
            print("✅ Connected to Gemini Live successfully!")
            
        except Exception as e:
            print(f"❌ Error starting session: {e}")
            self.running = False
            self.event_loop = None
            
            # Better cleanup on failure
            if hasattr(self, 'session') and self.session:
                try:
                    await self.session.__aexit__(None, None, None)
                except Exception as cleanup_error:
                    print(f"⚠️ Cleanup warning: {cleanup_error}")
                self.session = None
            
            # Re-raise the original error for proper handling
            raise Exception(f"Failed to start Gemini session: {str(e)}")

    def stop_session(self):
        """Stops the current session."""
        print("🛑 Stopping Gemini session...")
        self.running = False
        
        if self.session and self.event_loop:
            try:
                # Schedule cleanup in the event loop
                asyncio.run_coroutine_threadsafe(
                    self.session.__aexit__(None, None, None), 
                    self.event_loop
                )
                print("✅ Session stopped cleanly")
            except Exception as e:
                print(f"⚠️ Error during session cleanup: {e}")
        
        self.session = None
        self.event_loop = None

    def send_audio_frame(self, frame: av.AudioFrame):
        """Converts and sends audio frame to Gemini."""
        if not self.session or not self.running:
            return
        
        try:
            # Convert audio frame to bytes
            audio_array = frame.to_ndarray()
            audio_bytes = audio_array.tobytes()
            audio_b64 = base64.b64encode(audio_bytes).decode('utf-8')
            
            # Send asynchronously
            if self.event_loop:
                asyncio.run_coroutine_threadsafe(
                    self._send_audio_async(audio_b64), 
                    self.event_loop
                )
        except Exception as e:
            print(f"⚠️ Error processing audio frame: {e}")
    
    async def _send_audio_async(self, audio_b64):
        """Sends audio data to Gemini asynchronously."""
        try:
            if self.session:
                await self.session.send({
                    "realtime_input": {
                        "media_chunks": [{
                            "mime_type": "audio/pcm",
                            "data": audio_b64
                        }]
                    }
                })
        except Exception as e:
            print(f"⚠️ Error sending audio: {e}")

    def send_video_frame(self, frame: av.VideoFrame):
        """Converts and sends video frame to Gemini."""
        if not self.session or not self.running:
            return
        
        try:
            # Convert video frame to PIL Image
            pil_image = frame.to_image()
            
            # Convert to base64
            buffer = io.BytesIO()
            pil_image.save(buffer, format='JPEG', quality=85)
            image_b64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
            
            # Send asynchronously
            if self.event_loop:
                asyncio.run_coroutine_threadsafe(
                    self._send_video_async(image_b64), 
                    self.event_loop
                )
        except Exception as e:
            print(f"⚠️ Error processing video frame: {e}")
    
    async def _send_video_async(self, image_b64):
        """Sends image data to Gemini asynchronously."""
        try:
            if self.session:
                await self.session.send({
                    "realtime_input": {
                        "media_chunks": [{
                            "mime_type": "image/jpeg",
                            "data": image_b64
                        }]
                    }
                })
        except Exception as e:
            print(f"⚠️ Error sending video: {e}")

    async def receive_responses(self, ui_callback):
        """Continuously receives responses from Gemini."""
        try:
            async for response in self.session.receive():
                if not self.running:
                    break
                
                # Handle different response types
                if hasattr(response, 'text') and response.text:
                    ui_callback('text', response.text)
                elif hasattr(response, 'audio') and response.audio:
                    ui_callback('audio', response.audio)
                elif hasattr(response, 'tool_call') and response.tool_call:
                    ui_callback('tool_call', response.tool_call)
                    
        except Exception as e:
            print(f"⚠️ Error receiving responses: {e}")
            ui_callback('error', str(e))