import streamlit as st
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

    # Main layout
    col1, col2 = st.columns([0.6, 0.4])

    with col1:
        st.subheader("📹 Live Camera Feed")
        
        # ✅ Universal WebRTC configuration for ALL devices
        try:
            ctx = webrtc_streamer(
                key="gemini-live-assistant",
                mode=WebRtcMode.SENDRECV,
                rtc_configuration={
                    "iceServers": [
                        {"urls": ["stun:stun.l.google.com:19302"]},
                        {"urls": ["stun:stun1.l.google.com:19302"]},
                        {"urls": ["stun:stun2.l.google.com:19302"]},
                    ],
                    "iceTransportPolicy": "all"
                },
                media_stream_constraints={
                    "video": {
                        # ✅ Flexible constraints for any device
                        "width": {"min": 320, "ideal": 640, "max": 1920},
                        "height": {"min": 240, "ideal": 480, "max": 1080},
                        "frameRate": {"min": 10, "ideal": 30, "max": 60},
                        # ✅ Mobile support
                        "facingMode": "user",  # Front camera by default
                        # ✅ Desktop support
                        "aspectRatio": {"ideal": 1.333333}
                    },
                    "audio": {
                        # ✅ Universal audio constraints
                        "echoCancellation": {"ideal": True},
                        "noiseSuppression": {"ideal": True},
                        "autoGainControl": {"ideal": True},
                        # ✅ Mobile optimization
                        "sampleRate": {"ideal": 48000},
                        "channelCount": {"ideal": 1},
                        # ✅ Latency optimization
                        "latency": {"ideal": 0.01}
                    }
                },
                video_frame_callback=video_frame_callback,
                audio_frame_callback=audio_frame_callback,
                async_processing=False,
                # ✅ No audio sendback to prevent echo
                sendback_audio=False,
            )
            
            # Status indicator
            if ctx:
                if ctx.state.playing:
                    st.success("🟢 Camera & Microphone Active")
                else:
                    st.info("⚪ Click START in the video player above")
                    st.caption("📱 On mobile: Allow camera and microphone permissions")
            else:
                st.warning("⏳ Initializing WebRTC component...")
                
        except Exception as e:
            st.error(f"⚠️ WebRTC Error: {e}")
            st.info("💡 Try refreshing the page or checking permissions")

    with col2:
        st.subheader("🎛️ Controls & Transcript")
        
        # Control buttons
        if not is_running:
            if st.button("🚀 Start Session", use_container_width=True, type="primary"):
                try:
                    start_session_callback()
                    st.success("✅ Session Started!")
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Start Error: {e}")
        else:
            if st.button("🛑 Stop Session", use_container_width=True):
                try:
                    stop_session_callback()
                    st.info("⏹️ Session Stopped")
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Stop Error: {e}")
        
        # Clear transcript
        if st.button("🗑️ Clear Transcript", use_container_width=True, disabled=not transcript):
            st.session_state.transcript = []
            st.rerun()
        
        st.markdown("---")
        
        # Status indicator
        st.markdown("**Session Status:**")
        if is_running:
            st.success("🟢 Active - Listening")
        else:
            st.info("⚪ Inactive")
        
        st.markdown("---")
        
        # Transcript display
        st.markdown("**Conversation:**")
        
        if transcript:
            # Scrollable transcript container
            transcript_container = st.container(height=400)
            with transcript_container:
                for entry in transcript:
                    if entry.startswith("**🤖 Gemini:**"):
                        # Assistant message
                        content = entry.replace("**🤖 Gemini:**", "").strip()
                        with st.chat_message("assistant"):
                            st.markdown(content)
                    elif entry.startswith("*🛠️"):
                        # Tool call
                        st.info(entry.strip("*"))
                    else:
                        # User message
                        with st.chat_message("user"):
                            st.markdown(entry)
        else:
            st.info("💬 Start a session and speak to begin!")
    
    # Mobile-friendly troubleshooting
    with st.expander("🔧 Device Support & Troubleshooting"):
        st.markdown("""
        ### 📱 Mobile Devices (iOS/Android)
        - **Camera Access:** Tap "Allow" when prompted
        - **Microphone:** Enable in browser settings
        - **Best Browsers:** Chrome, Safari, Edge
        - **Portrait Mode:** Rotate device for better view
        
        ### 💻 Desktop/Laptop
        - **Built-in Camera:** Automatically detected
        - **External Webcam:** Select from browser prompt
        - **Microphone:** Choose from system devices
        - **Best Browsers:** Chrome, Edge, Firefox
        
        ### 🔧 Common Issues
        
        **"Camera not found":**
        - Check device permissions in browser settings
        - Try refreshing the page (F5)
        - Restart your browser
        
        **"No audio":**
        - Ensure microphone is not muted
        - Check system audio settings
        - Try another browser tab
        
        **"Connection failed":**
        - Check internet connection
        - Disable VPN temporarily
        - Allow WebRTC in firewall
        
        ### 🌐 Supported Devices
        ✅ iPhone (iOS 14+)  
        ✅ Android phones (Android 10+)  
        ✅ Windows laptops  
        ✅ MacBooks  
        ✅ Linux desktop  
        ✅ Chromebooks  
        ✅ Tablets (iPad, Android)  
        """)
    
    # Footer
    st.markdown("---")
    st.caption("🚀 Powered by Google Gemini 2.0 Flash Exp | Built with Streamlit & WebRTC")
    st.caption("📱 Works on mobile, tablet, and desktop | 🌐 Universal device support")