import streamlit as st
import requests
import json
from streamlit_mic_recorder import speech_to_text

# -----------------------------------------------------------------------------
# PAGE CONFIGURATION
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="NeetiNex - AI Government Scheme Assistant",
    page_icon="🏛️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# -----------------------------------------------------------------------------
# CONFIGURATION & CONSTANTS
# -----------------------------------------------------------------------------
BACKEND_URL = "http://127.0.0.1:8000"
QUERY_ENDPOINTS = ["/chat"]

# -----------------------------------------------------------------------------
# CUSTOM CSS (FIXED FLOATING BOTTOM BAR & SCROLLABLE CHAT)
# -----------------------------------------------------------------------------
st.markdown("""
<style>
    /* Global Reset & Background */
    .stApp {
        background: linear-gradient(135deg, #0f0c20 0%, #151030 40%, #0d1b2a 100%);
        color: #e2e8f0;
        font-family: 'Inter', system-ui, -apple-system, sans-serif;
    }

    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}

    /* Main Container Padding to clear bottom fixed bar */
    .block-container {
        padding-top: 1.5rem;
        padding-bottom: 7rem !important;
        max-width: 950px;
    }

    /* Header Styling */
    .title-text {
        margin: 0;
        font-size: 22px;
        font-weight: 700;
        background: linear-gradient(90deg, #ffffff 0%, #cbd5e1 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        line-height: 1.2;
    }

    .subtitle-text {
        margin: 0;
        font-size: 13px;
        color: #94a3b8;
    }

    .logo-avatar {
        width: 44px;
        height: 44px;
        background: linear-gradient(135deg, #a855f7 0%, #6366f1 50%, #06b6d4 100%);
        border-radius: 12px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-weight: 800;
        font-size: 22px;
        color: #ffffff;
        box-shadow: 0 4px 15px rgba(168, 85, 247, 0.4);
    }

    .status-badge {
        background: rgba(16, 185, 129, 0.15);
        border: 1px solid rgba(16, 185, 129, 0.3);
        color: #34d399;
        padding: 5px 12px;
        border-radius: 20px;
        font-size: 12px;
        font-weight: 600;
        display: inline-flex;
        align-items: center;
        gap: 6px;
    }

    .status-badge.offline {
        background: rgba(239, 68, 68, 0.15);
        border-color: rgba(239, 68, 68, 0.3);
        color: #f87171;
    }

    .status-dot {
        width: 7px;
        height: 7px;
        background-color: #34d399;
        border-radius: 50%;
        box-shadow: 0 0 8px #34d399;
    }

    .status-badge.offline .status-dot {
        background-color: #f87171;
        box-shadow: 0 0 8px #f87171;
    }

    /* Welcome Container */
    .welcome-container {
        text-align: center;
        padding: 48px 24px;
        background: rgba(255, 255, 255, 0.02);
        border: 1px solid rgba(255, 255, 255, 0.05);
        border-radius: 24px;
        margin: 30px auto;
        max-width: 720px;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
    }

    .welcome-logo {
        width: 68px;
        height: 68px;
        background: linear-gradient(135deg, #a855f7 0%, #6366f1 50%, #06b6d4 100%);
        border-radius: 20px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 34px;
        font-weight: 800;
        color: white;
        margin-bottom: 20px;
        box-shadow: 0 8px 25px rgba(168, 85, 247, 0.4);
    }

    .welcome-title {
        font-size: 26px;
        font-weight: 700;
        color: #f8fafc;
        margin-bottom: 12px;
        text-align: center;
    }

    .welcome-desc {
        font-size: 14px;
        color: #94a3b8;
        max-width: 560px;
        margin: 0 auto;
        line-height: 1.6;
        text-align: center;
    }

    /* Floating Fixed Bottom Search Bar */
    .bottom-bar-container {
        position: fixed;
        bottom: 20px;
        left: 50%;
        transform: translateX(-50%);
        width: 100%;
        max-width: 950px;
        padding: 0 1rem;
        z-index: 99999;
    }

    .compact-chat-wrapper {
        background: rgba(18, 15, 34, 0.95);
        backdrop-filter: blur(16px);
        border: 1px solid rgba(168, 85, 247, 0.35);
        border-radius: 18px;
        padding: 6px 12px;
        box-shadow: 0 10px 30px rgba(0, 0, 0, 0.6);
    }

    /* Input Fields Reset */
    .stTextInput > div > div > input {
        background-color: transparent !important;
        border: none !important;
        color: #f8fafc !important;
        font-size: 14px !important;
        padding: 2px 6px !important;
    }

    .stPopover > button {
        background: rgba(255, 255, 255, 0.06) !important;
        border: 1px solid rgba(255, 255, 255, 0.12) !important;
        color: #c084fc !important;
        border-radius: 10px !important;
        height: 38px !important;
        font-weight: 600 !important;
    }

    div[data-testid="stCustomComponentV1"] button {
        background: rgba(255, 255, 255, 0.08) !important;
        border: 1px solid rgba(168, 85, 247, 0.4) !important;
        color: #e2e8f0 !important;
        border-radius: 10px !important;
        height: 38px !important;
        font-size: 13px !important;
        font-weight: 600 !important;
    }

    .stButton > button {
        background: linear-gradient(135deg, #a855f7 0%, #6366f1 100%) !important;
        color: white !important;
        border: none !important;
        border-radius: 10px !important;
        height: 38px !important;
        font-weight: 700 !important;
    }
</style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# SESSION STATE INITIALIZATION
# -----------------------------------------------------------------------------
if "messages" not in st.session_state:
    st.session_state.messages = []

if "active_endpoint" not in st.session_state:
    st.session_state.active_endpoint = None

if "attached_filename" not in st.session_state:
    st.session_state.attached_filename = None

if "user_input" not in st.session_state:
    st.session_state.user_input = ""

if "current_query_to_submit" not in st.session_state:
    st.session_state.current_query_to_submit = None

# -----------------------------------------------------------------------------
# HELPER FUNCTIONS
# -----------------------------------------------------------------------------
def check_backend_connection():
    for ep in QUERY_ENDPOINTS:
        try:
            url = f"{BACKEND_URL}{ep}"
            res = requests.options(url, timeout=1.5)
            if res.status_code in [200, 405, 422]:
                st.session_state.active_endpoint = ep
                return True
        except Exception:
            continue
    
    st.session_state.active_endpoint = QUERY_ENDPOINTS[0]
    try:
        r = requests.get(f"{BACKEND_URL}/docs", timeout=1.5)
        return r.status_code == 200
    except Exception:
        return False

def query_backend(prompt: str):
    endpoint = st.session_state.active_endpoint or QUERY_ENDPOINTS[0]
    full_url = f"{BACKEND_URL}{endpoint}"
    
    payload = {
        "query": prompt,
        "question": prompt,
        "message": prompt
    }
    headers = {"Content-Type": "application/json"}
    
    try:
        response = requests.post(full_url, json=payload, headers=headers, timeout=30)
        if response.status_code == 200:
            data = response.json()
            answer = (
                data.get("answer") or 
                data.get("response") or 
                data.get("result") or 
                "No answer text received from backend."
            )
            sources = data.get("sources") or data.get("source_documents") or []
            return {"success": True, "answer": answer, "sources": sources}
        else:
            return {"success": False, "error": f"Backend status {response.status_code}."}
    except Exception as e:
        return {"success": False, "error": f"Error: {str(e)}"}

def handle_text_submit():
    if st.session_state.user_input and st.session_state.user_input.strip():
        st.session_state.current_query_to_submit = st.session_state.user_input.strip()
        st.session_state.user_input = ""  # Clear state immediately to prevent infinite submission loop

# -----------------------------------------------------------------------------
# HEADER SECTION
# -----------------------------------------------------------------------------
backend_online = check_backend_connection()
col_left, col_right = st.columns([3, 1])

with col_left:
    st.markdown("""
        <div style="display: flex; align-items: center; gap: 14px;">
            <div class="logo-avatar">N</div>
            <div>
                <h1 class="title-text">NeetiNex</h1>
                <p class="subtitle-text">AI-Powered Government Scheme Assistant</p>
            </div>
        </div>
    """, unsafe_allow_html=True)

with col_right:
    status_class = "status-badge" if backend_online else "status-badge offline"
    status_text = "AI Online" if backend_online else "Offline"
    st.markdown(f"""
        <div style="display: flex; justify-content: flex-end; align-items: center; height: 100%;">
            <div class="{status_class}">
                <span class="status-dot"></span> {status_text}
            </div>
        </div>
    """, unsafe_allow_html=True)

st.markdown("<hr style='border: none; height: 1px; background: rgba(255,255,255,0.06); margin: 16px 0 20px 0;'>", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# CHAT MESSAGES DISPLAY AREA
# -----------------------------------------------------------------------------
chat_container = st.container()

with chat_container:
    if not st.session_state.messages:
        st.markdown("""
            <div class="welcome-container">
                <div class="welcome-logo">N</div>
                <h2 class="welcome-title">How can NeetiNex help?</h2>
                <p class="welcome-desc">
                    Ask questions about Rajasthan or Central Government schemes, eligibility requirements, 
                    documentation checklists, or step-by-step application procedures using text or voice.
                </p>
            </div>
        """, unsafe_allow_html=True)
    else:
        for msg in st.session_state.messages:
            with st.chat_message(msg["role"]):
                st.write(msg["content"])
                if msg["role"] == "assistant" and msg.get("sources"):
                    valid_sources = [s for s in msg["sources"] if str(s).strip().lower() not in ["none", "null", ""]]
                    if valid_sources:
                        st.markdown("**Sources / References:**")
                        for src in valid_sources:
                            src_name = src.get("source") if isinstance(src, dict) else str(src)
                            st.markdown(f"- 📄 `{src_name}`")

# -----------------------------------------------------------------------------
# FIXED FLOATING BOTTOM INPUT BAR
# -----------------------------------------------------------------------------
st.markdown('<div class="bottom-bar-container">', unsafe_allow_html=True)
st.markdown('<div class="compact-chat-wrapper">', unsafe_allow_html=True)

col_plus, col_input, col_mic, col_submit = st.columns([0.6, 6.4, 1.6, 0.8])

# 1. Plus (+) Upload Icon
with col_plus:
    with st.popover("➕", help="Upload document"):
        st.markdown("<p style='font-size:12px; font-weight:600; color:#c084fc;'>Upload File</p>", unsafe_allow_html=True)
        uploaded_file = st.file_uploader("Document", type=["pdf", "docx", "txt"], label_visibility="collapsed")
        if uploaded_file:
            st.session_state.attached_filename = uploaded_file.name
            st.success(f"Attached: {uploaded_file.name}")

# 2. Text Input Field
with col_input:
    input_placeholder = "Ask NeetiNex anything..."
    if st.session_state.attached_filename:
        input_placeholder = f"📄 {st.session_state.attached_filename} attached | Ask query..."
    
    st.text_input(
        "Query", 
        placeholder=input_placeholder, 
        label_visibility="collapsed",
        key="user_input",
        on_change=handle_text_submit
    )

# 3. Speech-to-Text Button
with col_mic:
    transcribed_text = speech_to_text(
        language="hi-IN",
        start_prompt="🎙️ Speak",
        stop_prompt="⏹️ Stop",
        just_once=True,
        use_container_width=True,
        key='direct_mic_recorder'
    )
    if transcribed_text and transcribed_text.strip():
        st.session_state.current_query_to_submit = transcribed_text.strip()

# 4. Submit Button
with col_submit:
    if st.button("↑", help="Send Prompt"):
        handle_text_submit()

st.markdown('</div>', unsafe_allow_html=True)
st.markdown('</div>', unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# BACKEND EXECUTION & RERUN PIPELINE
# -----------------------------------------------------------------------------
if st.session_state.current_query_to_submit:
    query_text = st.session_state.current_query_to_submit
    st.session_state.current_query_to_submit = None  # Consume the query instantly
    
    st.session_state.messages.append({"role": "user", "content": query_text})
    
    with chat_container:
        with st.chat_message("assistant"):
            with st.spinner("Searching scheme knowledge base..."):
                result = query_backend(query_text)

            if result["success"]:
                answer_text = result["answer"]
                sources_list = result["sources"]

                st.write(answer_text)

                valid_sources = [s for s in sources_list if str(s).strip().lower() not in ["none", "null", ""]]
                if valid_sources:
                    st.markdown("**Sources / References:**")
                    for src in valid_sources:
                        src_name = src.get("source") if isinstance(src, dict) else str(src)
                        st.markdown(f"- 📄 `{src_name}`")

                st.session_state.messages.append({
                    "role": "assistant",
                    "content": answer_text,
                    "sources": sources_list
                })
            else:
                st.error(result["error"])
    
    st.rerun()