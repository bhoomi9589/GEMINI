# Gemini Live Assistant 🤖

A real-time multimodal assistant powered by Google's Gemini 2.0 with live video and audio streaming capabilities.

## Features

### 🎥 Media Input
- **Camera Mode**: Real-time video from webcam + microphone
- **Screen Share Mode**: Capture screen/window + microphone
- **Audio-Only Mode**: Microphone input without video
- **Live Video Feed**: See exactly what the AI sees

### 🎛️ Session Controls
- **Start/Stop**: Begin or end AI conversation sessions
- **Pause/Resume**: Temporarily pause streaming without disconnecting
- **Smart State Management**: Session stays connected during pause

### 🤖 AI Capabilities
- Real-time multimodal understanding (video + audio)
- Voice responses from Gemini 2.0
- Live conversation transcript
- Powered by Google's latest Gemini model

### 🌐 Advanced Features
- WebRTC-based media streaming with TURN server support
- Three flexible input modes for different use cases
- Visual status indicators (Active 🟢, Paused 🟡, Idle 💤)
- Browser-based diagnostics for troubleshooting
- Professional, responsive UI design

## Prerequisites

- Python 3.11+
- A Gemini API key from [Google AI Studio](https://aistudio.google.com/app/apikey)
- Webcam and microphone access
- Modern web browser with WebRTC support

## Local Setup

### 1. Clone and Install

```bash
cd e:\gemini
pip install -r requirements.txt
```

### 2. Configure API Key

Create a `.env` file in the project root:

```bash
GEMINI_API_KEY=your_actual_api_key_here
```

Or copy from the example:

```bash
copy .env.example .env
```

Then edit `.env` and add your API key.

### 3. Run the App

```bash
streamlit run app.py
```

Or:

```bash
python -m streamlit run app.py
```

The app will open at `http://localhost:8501`

### 4. Grant Permissions

When you first open the app:
1. Your browser will prompt for camera/microphone access
2. Click **"Allow"** to grant permissions
3. Click **"Run media check"** button if the stream doesn't start automatically
4. Click **"Start Session"** to begin talking with Gemini

## Deployment to Streamlit Cloud

### 1. Requirements

Your `requirements.txt` is already configured with:
- `google-genai` (NEW official SDK for Gemini 2.0)
- `streamlit-webrtc` (for video/audio streaming)
- Other dependencies

### 2. Streamlit Cloud Setup

1. Push your code to GitHub
2. Go to [share.streamlit.io](https://share.streamlit.io/)
3. Connect your GitHub repository
4. **IMPORTANT**: Set main file to `app.py` (not `ui.py`)
5. In **Advanced settings** → **Secrets**, add:

```toml
GEMINI_API_KEY = "your_actual_api_key_here"
```

### 3. Important Notes for Deployment

#### ✅ HTTPS (Solved)
Streamlit Cloud serves over HTTPS automatically, which is required for camera/microphone access.

#### ⚠️ WebRTC Connectivity
The app now includes TURN server configuration for better NAT traversal:

```python
{
    "iceServers": [
        {"urls": ["stun:stun.l.google.com:19302"]},
        {
            "urls": ["turn:openrelay.metered.ca:80"],
            "username": "openrelayproject",
            "credential": "openrelayproject"
        }
    ]
}
```

If you still experience connection issues, you may need to:
- Use a private TURN server (services like Twilio, Xirsys)
- Host on a VPS with proper WebRTC support

#### 🔧 Diagnostic Tools
The app includes built-in diagnostics:
- Click **"Run media check"** to test browser permissions
- Check browser console (F12) for WebRTC errors
- View connection status messages in the UI

## Troubleshooting

### Camera/Microphone Not Working

1. **Check browser permissions**: 
   - Click the lock icon in the address bar
   - Ensure camera and microphone are allowed
   
2. **Run the diagnostic**:
   - Click "Run media check" button in the UI
   - Review the output for permission errors
   
3. **Check console**:
   - Open browser DevTools (F12)
   - Look for WebRTC or getUserMedia errors

4. **HTTPS requirement**:
   - Browsers require HTTPS for camera/mic (except localhost)
   - Streamlit Cloud provides HTTPS automatically
   
5. **WebRTC connection issues**:
   - Some networks block WebRTC
   - Corporate firewalls may interfere
   - Try from a different network

### API Errors

- **"GEMINI_API_KEY not found"**: Set your API key in `.env` or Streamlit secrets
- **"404" or model errors**: Ensure you're using a valid model name (e.g., `gemini-2.0-flash-exp`)
- **Rate limiting**: Check your API quota at [Google AI Studio](https://aistudio.google.com/)

### Import Errors

This project uses the **NEW** `google-genai` SDK (not the deprecated `google-generativeai`).

If you see import errors:
```bash
pip uninstall google-generativeai
pip install --upgrade google-genai
```

## Project Structure

```
e:/gemini/
├── app.py                 # Main Streamlit application
├── live.py                # Gemini Live API backend logic
├── ui.py                  # UI components and WebRTC setup
├── requirements.txt       # Python dependencies
├── packages.txt           # System packages (for Linux deployment)
├── .env                   # API keys (local, not committed)
├── .env.example           # Template for API keys
└── README.md              # This file
```

## Technology Stack

- **Frontend**: Streamlit
- **AI**: Google Gemini 2.0 (Live API)
- **Media Streaming**: WebRTC via streamlit-webrtc
- **Video Processing**: PyAV, PIL
- **Async**: asyncio

## API Migration Note

This project has been updated to use the **new Google Gen AI SDK** (`google-genai`).

The old SDK (`google-generativeai`) is deprecated and will be sunset on **August 31, 2025**.

Migration changes:
- ✅ Updated from `google-generativeai` to `google-genai`
- ✅ Changed from `from google import genai` (old) to `from google import genai` (new SDK)
- ✅ Updated to use `Client.aio.live.connect()` API
- ✅ Model updated to `gemini-2.0-flash-exp`

## License

MIT

## Support

For issues with:
- **Gemini API**: [Google AI Forum](https://discuss.ai.google.dev/)
- **Streamlit**: [Streamlit Community](https://discuss.streamlit.io/)
- **WebRTC**: Check browser console and network configuration
