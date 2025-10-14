import streamlit as st
import uuid
from streamlit_webrtc import webrtc_streamer, WebRtcMode

def draw_interface(
    start_session_callback,
    stop_session_callback,
    video_frame_callback,
    audio_frame_callback,
    is_running,
    transcript
):
    """
    Draws the entire Streamlit UI with universal device support.
    Works on desktop, laptop, and mobile devices.
    """
    st.set_page_config(
        page_title="Gemini 2.0 Live Assistant",
        page_icon="🤖",
        layout="wide",
        initial_sidebar_state="collapsed"
    )
    
    st.title("🤖 Gemini 2.0 Live Assistant")
    st.caption("Real-time multimodal AI powered by Google Gemini 2.0")

    # ✅ Initialize stable component key once per session
    if 'webrtc_component_key' not in st.session_state:
        st.session_state.webrtc_component_key = f"gemini-live-{uuid.uuid4().hex[:8]}"

    # ✅ Initialize transcript if not passed
    if 'transcript' not in st.session_state:
        st.session_state.transcript = []

    # Main layout
    col1, col2 = st.columns([0.6, 0.4])

    with col1:
        st.subheader("📹 Live Camera Feed")
        
        # ✅ Universal WebRTC configuration for ALL devices
        try:
            webrtc_ctx = webrtc_streamer(
                key=st.session_state.webrtc_component_key,
                mode=WebRtcMode.SENDRECV,
                rtc_configuration={
                    "iceServers": [
                        {"urls": ["stun:stun.l.google.com:19302"]},
                        {"urls": ["stun:stun1.l.google.com:19302"]},
                        {"urls": ["stun:stun.stunprotocol.org:3478"]},
                    ]
                },
                media_stream_constraints={
                    "video": {
                        "width": {"min": 320, "ideal": 640, "max": 1280},
                        "height": {"min": 240, "ideal": 480, "max": 720},
                        "frameRate": {"min": 10, "ideal": 15, "max": 30},
                        "facingMode": "user"  # Front camera for mobile
                    },
                    "audio": {
                        "echoCancellation": True,
                        "noiseSuppression": True,
                        "autoGainControl": True,
                        "sampleRate": 16000,
                        "channelCount": 1
                    }
                },
                video_frame_callback=video_frame_callback,
                audio_frame_callback=audio_frame_callback,
                async_processing=True,
                desired_playing_state=is_running
            )
                
        except Exception as e:
            st.error(f"❌ Camera/Microphone Error: {str(e)}")
            st.info("📱 **Mobile Users**: Tap 'Allow' when prompted for camera/microphone access")
            st.info("🖥️ **Desktop Users**: Check browser permissions for camera/microphone")

    with col2:
        st.subheader("🎛️ Controls & Transcript")
        
        # Control buttons
        if not is_running:
            if st.button("🚀 Start Live Session", type="primary", use_container_width=True, key="start_btn"):
                start_session_callback()
                st.rerun()
        else:
            if st.button("⏹️ Stop Session", type="secondary", use_container_width=True, key="stop_btn"):
                stop_session_callback()
                st.rerun()
        
        # Clear transcript
        if st.button("🗑️ Clear Transcript", use_container_width=True, disabled=not transcript, key="clear_btn"):
            st.session_state.transcript = []
            st.rerun()
        
        st.markdown("---")
        
        # Status indicator
        st.markdown("**Session Status:**")
        if is_running:
            st.success("🟢 **LIVE** - AI is listening and watching")
        else:
            st.info("🔴 **STOPPED** - Click 'Start' to begin")
        
        st.markdown("---")
        
        # Transcript display
        st.markdown("**Conversation:**")
        
        if transcript:
            # Create scrollable transcript container
            with st.container():
                for i, entry in enumerate(reversed(transcript[-10:])):  # Show last 10 entries
                    if entry.get('type') == 'ai':
                        st.markdown(f"🤖 **AI**: {entry['content']}")
                    elif entry.get('type') == 'user':
                        st.markdown(f"👤 **You**: {entry['content']}")
                    elif entry.get('type') == 'ai_audio':
                        st.markdown(f"🔊 **AI**: {entry['content']}")
                    elif entry.get('type') == 'error':
                        st.error(f"❌ {entry['content']}")
                    
                    if i < len(transcript[-10:]) - 1:
                        st.markdown("---")
        else:
            st.markdown("💬 *Conversation will appear here...*")
    
    # Mobile-friendly troubleshooting
    with st.expander("🔧 Device Support & Troubleshooting"):
        st.markdown("""
        ### 📱 **Mobile Devices (iOS/Android)**
        - **Chrome/Safari**: Fully supported with camera + microphone
        - **Permissions**: Tap "Allow" when prompted for camera/mic access
        - **Performance**: Works best on newer devices (2019+)
        - **Network**: Requires stable internet connection
        
        ### 🖥️ **Desktop/Laptop**
        - **Chrome/Edge**: Best performance and compatibility
        - **Firefox**: Supported with minor limitations
        - **Safari**: macOS - fully supported
        - **Permissions**: Check browser settings if camera/mic blocked
        
        ### 🔧 **Common Issues**
        - **No Video**: Check camera permissions in browser settings
        - **No Audio**: Check microphone permissions and ensure not muted
        - **Poor Quality**: Try closing other browser tabs or apps
        - **Connection Issues**: Refresh page and try again
        
        ### 🌐 **Browser Settings**
        1. Click the 🔒 lock icon in address bar
        2. Allow Camera and Microphone access
        3. Refresh the page if needed
        
        ### 📊 **System Requirements**
        - **Internet**: 2+ Mbps upload speed recommended
        - **RAM**: 4GB+ recommended for smooth operation
        - **Browser**: Latest version of Chrome, Edge, Safari, or Firefox
        """)
    
    # Footer
    st.markdown("---")
    st.caption("🚀 Powered by Google Gemini 2.0 Flash Exp | Built with Streamlit & WebRTC")
    st.caption("📱 Works on mobile, tablet, and desktop | 🌐 Universal device support")