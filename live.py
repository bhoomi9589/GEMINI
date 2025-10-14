import os
import asyncio
import base64
import io
import av
from PIL import Image

from google import genai
from google.genai import types

class GeminiLive:
    """
    Manages all backend logic for the Gemini LiveConnect session.
    This class is completely independent of Streamlit or Flask.
    """
    def __init__(self):
        # --- Gemini API Setup ---
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            # First, check for Streamlit secrets
            try:
                import streamlit as st
                api_key = st.secrets.get("GEMINI_API_KEY")
            except (ImportError, AttributeError):
                pass
        
        if not api_key:
            raise ValueError("GEMINI_API_KEY not found. Please set it in your .env file or Streamlit secrets.")
        
        # Initialize the new Google Gen AI client
        self.client = genai.Client(api_key=api_key)
        
        self.model = "models/gemini-2.0-flash-exp"
        self.config = {
            "response_modalities": ["AUDIO"],
        }
        self.session = None
        self.running = False
        self.event_loop = None

    async def start_session(self):
        """Starts a new Gemini LiveConnect session."""
        print("✅ Starting Gemini session...")
        self.running = True
        
        # Store the event loop
        self.event_loop = asyncio.get_event_loop()
        
        try:
            # Connect using the new AsyncLive API
            self.session = await self.client.aio.live.connect(model=self.model, config=self.config).__aenter__()
            print("✅ Connected to Gemini Live!")
        except Exception as e:
            print(f"❌ Error starting session: {e}")
            self.running = False
            self.event_loop = None
            raise

    def stop_session(self):
        """Stops the current Gemini LiveConnect session."""
        print("🛑 Stopping Gemini session...")
        self.running = False

    def send_audio_frame(self, frame: av.AudioFrame):
        """Processes and sends an audio frame from WebRTC to Gemini (synchronous, thread-safe)."""
        if not self.running or not self.session or not self.event_loop:
            return
        
        try:
            # Convert audio frame to bytes
            audio_data = frame.to_ndarray().tobytes()
            audio_b64 = base64.b64encode(audio_data).decode('utf-8')
            
            # Thread-safe task scheduling
            asyncio.run_coroutine_threadsafe(
                self._send_audio_async(audio_b64),
                self.event_loop
            )
        except Exception as e:
            print(f"Error scheduling audio send: {e}")
    
    async def _send_audio_async(self, audio_b64):
        """Internal async method to send audio."""
        if not self.running or not self.session:
            return
        try:
            await self.session.send(
                {"data": audio_b64, "mime_type": "audio/pcm"},
                end_of_turn=False
            )
        except Exception as e:
            print(f"Error sending audio: {e}")

    def send_video_frame(self, frame: av.VideoFrame):
        """Processes and sends a video frame from WebRTC to Gemini (synchronous, thread-safe)."""
        if not self.running or not self.session or not self.event_loop:
            return

        try:
            # Convert frame to JPEG
            img = frame.to_image()
            image_io = io.BytesIO()
            img.save(image_io, format="jpeg")
            image_io.seek(0)
            
            image_data = image_io.getvalue()
            image_b64 = base64.b64encode(image_data).decode('utf-8')
            
            # Thread-safe task scheduling
            asyncio.run_coroutine_threadsafe(
                self._send_video_async(image_b64),
                self.event_loop
            )
        except Exception as e:
            print(f"Error scheduling video send: {e}")
    
    async def _send_video_async(self, image_b64):
        """Internal async method to send video."""
        if not self.running or not self.session:
            return
        try:
            await self.session.send(
                {"data": image_b64, "mime_type": "image/jpeg"},
                end_of_turn=False
            )
        except Exception as e:
            print(f"Error sending video frame: {e}")

    async def receive_responses(self, ui_callback):
        """Continuously listens for responses from Gemini and sends them to the UI."""
        if not self.running or not self.session:
            return
        
        try:
            print("👂 Listening for Gemini responses...")
            async for response in self.session.receive():
                # Check if we should stop
                if not self.running:
                    print("⏹️ Stop requested, breaking receive loop")
                    break
                    
                # Use the callback to send data back to the UI thread
                if hasattr(response, 'text') and response.text:
                    ui_callback("text", response.text)
                if hasattr(response, 'server_content'):
                    server_content = response.server_content
                    if hasattr(server_content, 'model_turn') and server_content.model_turn:
                        for part in server_content.model_turn.parts:
                            if hasattr(part, 'text') and part.text:
                                ui_callback("text", part.text)
        except asyncio.CancelledError:
            print("🔴 Receive task cancelled")
        except Exception as e:
            print(f"❌ Error receiving response: {e}")
            ui_callback("error", f"Connection error: {e}")
        finally:
            # Proper cleanup
            print("🧹 Cleaning up Gemini session...")
            if self.session:
                try:
                    if hasattr(self.session, 'close'):
                        await self.session.close()
                    elif hasattr(self.session, 'disconnect'):
                        await self.session.disconnect()
                    print("✅ Session closed gracefully")
                except Exception as e:
                    print(f"⚠️ Error during cleanup: {e}")
                finally:
                    self.session = None
            
            self.running = False
            self.event_loop = None
            print("✅ Response listener cleaned up")