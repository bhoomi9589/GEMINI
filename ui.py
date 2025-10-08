# ui.py
import streamlit as st
import streamlit.components.v1 as components
from streamlit_webrtc import webrtc_streamer, WebRtcMode, RTCConfiguration

def draw_interface(
    start_session_callback,
    stop_session_callback,
    video_frame_callback,
    audio_frame_callback,
    is_running,
    transcript
):
    """
    Draws the entire Streamlit UI.
    It receives callback functions from app.py to handle logic.
    """
    st.set_page_config(page_title="Gemini Live Assistant", page_icon="🤖", layout="wide")
    st.title("🤖 Gemini Live Assistant")
    st.caption("A real-time multimodal assistant powered by Gemini.")

    # Session state for pause/resume and mode selection
    if 'is_paused' not in st.session_state:
        st.session_state.is_paused = False
    if 'media_mode' not in st.session_state:
        st.session_state.media_mode = "Camera"

    col1, col2 = st.columns([0.6, 0.4])

    with col1:
        # Mode selector
        st.subheader("📹 Media Input")
        mode_col1, mode_col2 = st.columns([2, 1])
        
        with mode_col1:
            media_mode = st.selectbox(
                "Select Mode:",
                ["Camera", "Screen Share", "None"],
                index=["Camera", "Screen Share", "None"].index(st.session_state.media_mode),
                key="media_mode_selector",
                disabled=is_running,
                help="Choose your input source. Camera: webcam + mic, Screen Share: screen + mic, None: mic only"
            )
            st.session_state.media_mode = media_mode
        
        with mode_col2:
            if is_running:
                status_color = "🟢" if not st.session_state.is_paused else "🟡"
                status_text = "Active" if not st.session_state.is_paused else "Paused"
                st.markdown(f"### {status_color} {status_text}")

        # Configure media constraints based on mode
        if media_mode == "Camera":
            media_constraints = {"video": True, "audio": True}
            st.caption("🎥 Using webcam and microphone")
        elif media_mode == "Screen Share":
            media_constraints = {"video": {"mediaSource": "screen"}, "audio": True}
            st.caption("🖥️ Using screen share and microphone")
        else:  # None
            media_constraints = {"video": False, "audio": True}
            st.caption("🎤 Using microphone only")

        # Video feed container
        video_container = st.container()
        
        with video_container:
            if media_mode != "None":
                # Start the WebRTC streamer with video
                ctx = webrtc_streamer(
                    key=f"live-assistant-{media_mode}",
                    mode=WebRtcMode.SENDRECV,  # Show video feed locally
                    rtc_configuration=RTCConfiguration(
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
                    ),
                    media_stream_constraints=media_constraints,
                    video_frame_callback=video_frame_callback if is_running and not st.session_state.is_paused else None,
                    audio_frame_callback=audio_frame_callback if is_running and not st.session_state.is_paused else None,
                    async_processing=True,
                    video_html_attrs={
                        "style": {"width": "100%", "margin": "0 auto", "border-radius": "10px"},
                        "controls": False,
                        "autoPlay": True,
                        "muted": True  # Mute local playback to avoid echo
                    }
                )

                # Show diagnostics if needed
                if ctx is None:
                    st.warning("⚠️ WebRTC context not created. The streamer failed to initialize.")
                elif not getattr(ctx.state, "playing", False):
                    st.info("📹 Waiting for media stream... Please allow camera/microphone access.")
                    with st.expander("🔧 Troubleshooting"):
                        st.markdown("""
                        **Quick checks:**
                        - Make sure the page is served over HTTPS (required for camera/mic)
                        - Check the browser's permission prompt and click "Allow"
                        - Open browser console for errors (F12 → Console)
                        - For Screen Share: you may need to select which screen/window to share
                        """)
                        _render_media_check_js()
            else:
                # Audio only mode
                ctx = webrtc_streamer(
                    key="live-assistant-audio-only",
                    mode=WebRtcMode.SENDONLY,
                    rtc_configuration=RTCConfiguration(
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
                    ),
                    media_stream_constraints=media_constraints,
                    audio_frame_callback=audio_frame_callback if is_running and not st.session_state.is_paused else None,
                    async_processing=True,
                )
                
                st.info("🎤 Audio-only mode: Microphone input active")
                
                if ctx is None:
                    st.warning("⚠️ WebRTC context not created.")
                elif not getattr(ctx.state, "playing", False):
                    st.info("🎤 Waiting for microphone access...")
                    _render_media_check_js()

    with col2:
        st.subheader("🎛️ Session Controls")

        # Session control buttons
        button_cols = st.columns(2)
        
        with button_cols[0]:
            if not is_running:
                if st.button("🚀 Start Session", use_container_width=True, type="primary"):
                    st.session_state.is_paused = False
                    start_session_callback()
            else:
                if st.button("🛑 Stop Session", use_container_width=True, type="secondary"):
                    st.session_state.is_paused = False
                    stop_session_callback()
        
        with button_cols[1]:
            if is_running:
                if not st.session_state.is_paused:
                    if st.button("⏸️ Pause", use_container_width=True):
                        st.session_state.is_paused = True
                        st.rerun()
                else:
                    if st.button("▶️ Resume", use_container_width=True, type="primary"):
                        st.session_state.is_paused = False
                        st.rerun()

        # Status indicator
        if is_running:
            if st.session_state.is_paused:
                st.warning("⏸️ Session is paused. Click Resume to continue.")
            else:
                st.success("✅ Session active. AI is listening and responding.")
        else:
            st.info("💤 No active session. Click Start to begin.")

        st.markdown("---")
        
        # Transcript section
        st.subheader("💬 Conversation")
        transcript_container = st.container()
        with transcript_container:
            if transcript:
                for entry in transcript:
                    st.markdown(entry)
            else:
                st.caption("_Conversation will appear here..._")


def _render_media_check_js():
        """Inject a small piece of JS to test getUserMedia and enumerate media devices.

        This renders a minimal UI inside the Streamlit page with results so the user
        can see whether the browser can access camera/microphone and what devices
        are available. It does not send any data to the server; it only runs in the
        user's browser for diagnostics.
        """
        html = """
        <div style='font-family: Arial, sans-serif;'>
            <div id='media-check-output' style='white-space: pre-wrap; background:#f6f8fa; padding:10px; border-radius:6px;'></div>
            <button id='media-check-btn' style='margin-top:8px;'>Run media check</button>
        </div>
        <script>
        const out = document.getElementById('media-check-output');
        const btn = document.getElementById('media-check-btn');

        function log(msg){ out.textContent += msg + '\n'; }

        async function runCheck(){
            out.textContent = '';
            if (!navigator.mediaDevices || !navigator.mediaDevices.enumerateDevices) {
                log('navigator.mediaDevices.enumerateDevices NOT supported in this browser.');
                return;
            }
            try{
                const devices = await navigator.mediaDevices.enumerateDevices();
                log('Found devices: ' + devices.length);
                devices.forEach(d => log(`${d.kind} - ${d.label || '[label hidden]'} - id:${d.deviceId}`));
            } catch(e){ log('Error enumerating devices: ' + e); }

            // Try to request a short-lived media stream. The browser will prompt for permission.
            try{
                log('\nRequesting camera+microphone permission...');
                const stream = await navigator.mediaDevices.getUserMedia({video: true, audio: true});
                const tracks = stream.getTracks();
                log('getUserMedia succeeded. Active tracks: ' + tracks.length);
                tracks.forEach(t => log('Track: ' + t.kind + ' state=' + t.readyState));
                // Stop immediately to avoid capturing unintended media
                tracks.forEach(t => t.stop());
                log('Stopped tracks.');
            } catch(e){ log('getUserMedia failed or was denied: ' + e); }
        }

        btn.addEventListener('click', runCheck);
        // Optionally run once on load (commented out to avoid auto-prompting):
        // runCheck();
        </script>
        """

        components.html(html, height=220)