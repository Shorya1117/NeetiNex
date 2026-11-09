
import streamlit as st
import requests
import json
import base64
import os
import hashlib


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
# LOGO HELPER (BASE64)
# -----------------------------------------------------------------------------

def get_base64_image(image_path):
    if os.path.exists(image_path):
        with open(image_path, "rb") as img_file:
            encoded = base64.b64encode(img_file.read()).decode()
            return f"data:image/png;base64,{encoded}"
    return ""


LOGO_PATH = os.path.join(os.path.dirname(__file__), "logo.png")
logo_base64 = get_base64_image(LOGO_PATH)


# -----------------------------------------------------------------------------
# CONFIGURATION & CONSTANTS
# -----------------------------------------------------------------------------

BACKEND_URL = "http://127.0.0.1:8000"
QUERY_ENDPOINTS = ["/chat"]


# -----------------------------------------------------------------------------
# CUSTOM CSS
# -----------------------------------------------------------------------------

st.markdown("""
<style>
    .stApp {
        background: linear-gradient(135deg, #0f0c20 0%, #151030 40%, #0d1b2a 100%);
        color: #e2e8f0;
        font-family: 'Inter', system-ui, -apple-system, sans-serif;
    }

    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}

    .block-container {
        padding-top: 1.2rem;
        padding-bottom: 7rem !important;
        max-width: 950px;
    }

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
        border-radius: 12px;
        object-fit: cover;
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

    .stTabs [data-baseweb="tab-list"] {
        gap: 12px;
        background: rgba(255, 255, 255, 0.03);
        padding: 6px 10px;
        border-radius: 16px;
        border: 1px solid rgba(255, 255, 255, 0.08);
    }

    .stTabs [data-baseweb="tab"] {
        height: 40px;
        border-radius: 10px;
        color: #94a3b8;
        font-weight: 600;
        font-size: 14px;
        padding: 0 20px;
    }

    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, #a855f7 0%, #6366f1 100%) !important;
        color: #ffffff !important;
    }

    .welcome-container {
        text-align: center;
        padding: 40px 20px;
        background: rgba(255, 255, 255, 0.02);
        border: 1px solid rgba(255, 255, 255, 0.05);
        border-radius: 24px;
        margin: 20px auto;
        max-width: 720px;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
    }

    .welcome-logo {
        width: 64px;
        height: 64px;
        border-radius: 18px;
        object-fit: cover;
        margin-bottom: 16px;
        box-shadow: 0 8px 25px rgba(168, 85, 247, 0.4);
    }

    .welcome-title {
        font-size: 24px;
        font-weight: 700;
        color: #f8fafc;
        margin-bottom: 10px;
        text-align: center;
    }

    .welcome-desc {
        font-size: 14px;
        color: #94a3b8;
        max-width: 540px;
        margin: 0 auto;
        line-height: 1.6;
        text-align: center;
    }

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

    .stTextInput > div > div > input {
        background-color: transparent !important;
        border: none !important;
        color: #f8fafc !important;
        font-size: 14px !important;
        padding: 2px 6px !important;
    }

    .stButton > button {
        background: linear-gradient(135deg, #a855f7 0%, #6366f1 100%) !important;
        color: white !important;
        border: none !important;
        border-radius: 10px !important;
        height: 38px !important;
        font-weight: 700 !important;
        width: 100%;
    }

    .pdf-card {
        background: rgba(255, 255, 255, 0.03);
        border: 1px dashed rgba(168, 85, 247, 0.3);
        border-radius: 16px;
        padding: 16px;
        margin-bottom: 20px;
    }
</style>
""", unsafe_allow_html=True)


# -----------------------------------------------------------------------------
# SESSION STATE INITIALIZATION
# -----------------------------------------------------------------------------

if "scheme_messages" not in st.session_state:
    st.session_state.scheme_messages = []

if "pdf_messages" not in st.session_state:
    st.session_state.pdf_messages = []

if "active_endpoint" not in st.session_state:
    st.session_state.active_endpoint = None

if "attached_filename" not in st.session_state:
    st.session_state.attached_filename = None

if "attached_pdf_hash" not in st.session_state:
    st.session_state.attached_pdf_hash = None

if "pdf_document_id" not in st.session_state:
    st.session_state.pdf_document_id = None

if "scheme_input" not in st.session_state:
    st.session_state.scheme_input = ""

if "pdf_input" not in st.session_state:
    st.session_state.pdf_input = ""

if "current_scheme_query" not in st.session_state:
    st.session_state.current_scheme_query = None

if "current_pdf_query" not in st.session_state:
    st.session_state.current_pdf_query = None


# -----------------------------------------------------------------------------
# HELPER FUNCTIONS
# -----------------------------------------------------------------------------

def upload_pdf_to_backend(uploaded_file):
    try:
        files = {
            "file": (
                uploaded_file.name,
                uploaded_file.getvalue(),
                "application/pdf"
            )
        }

        response = requests.post(
            f"{BACKEND_URL}/pdf/upload",
            files=files,
            timeout=300
        )

        if response.status_code == 200:
            return {
                "success": True,
                "data": response.json()
            }

        return {
            "success": False,
            "error": response.text
        }

    except requests.RequestException as e:
        return {
            "success": False,
            "error": str(e)
        }


def delete_pdf_from_backend(document_id):
    if not document_id:
        return True

    try:
        response = requests.delete(
            f"{BACKEND_URL}/pdf/delete",
            json={"document_id": document_id},
            timeout=30
        )

        if response.status_code == 200:
            return True

        st.warning(
            f"Could not delete the old PDF. "
            f"Backend response: {response.text}"
        )
        return False

    except requests.RequestException as e:
        st.warning(f"PDF cleanup request failed: {e}")
        return False


def clear_pdf_session():
    document_id = st.session_state.get("pdf_document_id")

    if document_id:
        deleted = delete_pdf_from_backend(document_id)

        if not deleted:
            return

    st.session_state.pdf_document_id = None
    st.session_state.attached_filename = None
    st.session_state.attached_pdf_hash = None
    st.session_state.pdf_messages = []
    st.session_state.pdf_input = ""
    st.session_state.current_pdf_query = None
    st.session_state["pdf_tab_uploader"] = None


def check_backend_connection():
    for endpoint in QUERY_ENDPOINTS:
        try:
            response = requests.options(
                f"{BACKEND_URL}{endpoint}",
                timeout=1.5
            )

            if response.status_code in [200, 405, 422]:
                st.session_state.active_endpoint = endpoint
                return True

        except requests.RequestException:
            continue

    st.session_state.active_endpoint = QUERY_ENDPOINTS[0]

    try:
        response = requests.get(
            f"{BACKEND_URL}/docs",
            timeout=1.5
        )
        return response.status_code == 200

    except requests.RequestException:
        return False


def query_scheme_backend(prompt: str):
    endpoint = (
        st.session_state.active_endpoint
        or QUERY_ENDPOINTS[0]
    )

    full_url = f"{BACKEND_URL}{endpoint}"

    payload = {
        "query": prompt,
        "question": prompt,
        "message": prompt
    }

    headers = {"Content-Type": "application/json"}

    try:
        response = requests.post(
            full_url,
            json=payload,
            headers=headers,
            timeout=60
        )

        if response.status_code == 200:
            data = response.json()

            answer = (
                data.get("answer")
                or data.get("response")
                or data.get("result")
                or "No answer text received from backend."
            )

            sources = (
                data.get("sources")
                or data.get("source_documents")
                or []
            )

            return {
                "success": True,
                "answer": answer,
                "sources": sources
            }

        return {
            "success": False,
            "error": (
                f"Backend status {response.status_code}: "
                f"{response.text}"
            )
        }

    except requests.RequestException as e:
        return {
            "success": False,
            "error": f"Error: {str(e)}"
        }


def query_pdf_backend(prompt: str):
    if not st.session_state.pdf_document_id:
        return {
            "success": False,
            "error": "Please upload a PDF first."
        }

    try:
        response = requests.post(
            f"{BACKEND_URL}/pdf/chat",
            json={
                "document_id": st.session_state.pdf_document_id,
                "question": prompt
            },
            timeout=120
        )

        if response.status_code == 200:
            data = response.json()

            return {
                "success": True,
                "answer": data.get(
                    "answer",
                    "No answer received."
                ),
                "sources": data.get("sources", [])
            }

        return {
            "success": False,
            "error": (
                f"PDF backend status {response.status_code}: "
                f"{response.text}"
            )
        }

    except requests.RequestException as e:
        return {
            "success": False,
            "error": f"PDF error: {str(e)}"
        }


def display_sources(sources, pdf_mode=False):
    valid_sources = [
        source for source in sources
        if str(source).strip().lower() not in [
            "none", "null", ""
        ]
    ]

    if not valid_sources:
        return

    st.markdown("**Sources / References:**")

    for source in valid_sources:
        if isinstance(source, dict):
            if pdf_mode:
                source_value = (
                    source.get("source")
                    or source.get("page")
                    or str(source)
                )
            else:
                source_value = (
                    source.get("url")
                    or source.get("source")
                    or str(source)
                )
        else:
            source_value = str(source)

        source_value = str(source_value)

        if source_value.startswith("http"):
            st.markdown(f"- 🔗 [{source_value}]({source_value})")
        else:
            st.markdown(f"- 📄 `{source_value}`")


def handle_scheme_submit():
    query = st.session_state.scheme_input.strip()

    if query:
        st.session_state.current_scheme_query = query
        st.session_state.scheme_input = ""


def handle_pdf_submit():
    query = st.session_state.pdf_input.strip()

    if query:
        st.session_state.current_pdf_query = query
        st.session_state.pdf_input = ""


# -----------------------------------------------------------------------------
# HEADER SECTION
# -----------------------------------------------------------------------------

backend_online = check_backend_connection()

col_left, col_right = st.columns([3, 1])

logo_html = (
    f'<img src="{logo_base64}" class="logo-avatar" alt="NeetiNex Logo">'
    if logo_base64
    else '''
    <div class="logo-avatar"
         style="background:#a855f7;display:flex;
         align-items:center;justify-content:center;
         color:white;font-weight:800;">N</div>
    '''
)

with col_left:
    st.markdown(
        f"""
        <div style="display:flex;align-items:center;gap:14px;">
            {logo_html}
            <div>
                <h1 class="title-text">NeetiNex</h1>
                <p class="subtitle-text">
                    AI-Powered Government Scheme Assistant
                </p>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

with col_right:
    status_class = (
        "status-badge"
        if backend_online
        else "status-badge offline"
    )

    status_text = (
        "AI Online"
        if backend_online
        else "Offline"
    )

    st.markdown(
        f"""
        <div style="display:flex;justify-content:flex-end;
                    align-items:center;height:100%;">
            <div class="{status_class}">
                <span class="status-dot"></span>
                {status_text}
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

st.markdown(
    "<hr style='border:none;height:1px;"
    "background:rgba(255,255,255,0.06);"
    "margin:16px 0 20px 0;'>",
    unsafe_allow_html=True
)


# -----------------------------------------------------------------------------
# TAB NAVIGATION
# -----------------------------------------------------------------------------

tab_schemes, tab_pdf = st.tabs([
    "🏛️ Scheme Assistant",
    "📄 Document Chat (PDF)"
])


# =============================================================================
# TAB 1: SCHEME ASSISTANT
# =============================================================================

welcome_logo_html = (
    f'<img src="{logo_base64}" class="welcome-logo" alt="NeetiNex Logo">'
    if logo_base64
    else '''
    <div class="welcome-logo"
         style="background:#a855f7;display:flex;
         align-items:center;justify-content:center;
         color:white;font-weight:800;font-size:30px;">N</div>
    '''
)

with tab_schemes:
    scheme_chat_container = st.container()

    with scheme_chat_container:
        if not st.session_state.scheme_messages:
            st.markdown(
                f"""
                <div class="welcome-container">
                    {welcome_logo_html}
                    <h2 class="welcome-title">
                        How can NeetiNex help?
                    </h2>
                    <p class="welcome-desc">
                        Ask questions about Rajasthan or Central
                        Government schemes, eligibility requirements,
                        documentation checklists, or step-by-step
                        application procedures.
                    </p>
                </div>
                """,
                unsafe_allow_html=True
            )

        else:
            for message in st.session_state.scheme_messages:
                with st.chat_message(message["role"]):
                    st.write(message["content"])

                    if (
                        message["role"] == "assistant"
                        and message.get("sources")
                    ):
                        display_sources(message["sources"])

    st.markdown(
        '<div class="bottom-bar-container">',
        unsafe_allow_html=True
    )
    st.markdown(
        '<div class="compact-chat-wrapper">',
        unsafe_allow_html=True
    )

    col_input_s, col_sub_s = st.columns([9, 1])

    with col_input_s:
        st.text_input(
            "Scheme Query",
            placeholder=(
                "Ask NeetiNex anything about government schemes..."
            ),
            label_visibility="collapsed",
            key="scheme_input",
            on_change=handle_scheme_submit
        )

    with col_sub_s:
        if st.button(
            "↑",
            help="Send Scheme Prompt",
            key="btn_scheme_send"
        ):
            handle_scheme_submit()

    st.markdown("</div></div>", unsafe_allow_html=True)

    if st.session_state.current_scheme_query:
        scheme_query = st.session_state.current_scheme_query
        st.session_state.current_scheme_query = None

        st.session_state.scheme_messages.append({
            "role": "user",
            "content": scheme_query
        })

        with scheme_chat_container:
            with st.chat_message("assistant"):
                with st.spinner(
                    "Searching scheme knowledge base..."
                ):
                    result = query_scheme_backend(scheme_query)

                if result["success"]:
                    st.write(result["answer"])
                    display_sources(result["sources"])

                    st.session_state.scheme_messages.append({
                        "role": "assistant",
                        "content": result["answer"],
                        "sources": result["sources"]
                    })

                else:
                    st.error(result["error"])

        st.rerun()


# =============================================================================
# TAB 2: DOCUMENT CHAT (PDF MODE)
# =============================================================================

with tab_pdf:
    st.markdown(
        '<div class="pdf-card">',
        unsafe_allow_html=True
    )

    st.markdown(
        """
        <p style="font-size:14px;font-weight:600;
                  color:#c084fc;margin-bottom:8px;">
            📄 Upload Document for Temporary RAG Chat
        </p>
        """,
        unsafe_allow_html=True
    )

    uploaded_pdf = st.file_uploader(
        "Upload PDF",
        type=["pdf"],
        label_visibility="collapsed",
        key="pdf_tab_uploader"
    )

    if uploaded_pdf:
        uploaded_bytes = uploaded_pdf.getvalue()
        uploaded_hash = hashlib.sha256(
            uploaded_bytes
        ).hexdigest()

        # Detect a genuinely different PDF using its content hash.
        if st.session_state.attached_pdf_hash != uploaded_hash:

            old_document_id = st.session_state.pdf_document_id
            can_upload = True

            # Remove the old document before indexing a new one.
            if old_document_id:
                can_upload = delete_pdf_from_backend(
                    old_document_id
                )

            if can_upload:
                with st.spinner(
                    "Extracting text / running OCR and indexing PDF..."
                ):
                    result = upload_pdf_to_backend(uploaded_pdf)

                if result["success"]:
                    data = result["data"]

                    st.session_state.attached_filename = uploaded_pdf.name
                    st.session_state.attached_pdf_hash = uploaded_hash
                    st.session_state.pdf_document_id = data["document_id"]

                    # Start a fresh conversation for the new PDF.
                    st.session_state.pdf_messages = []
                    st.session_state.pdf_input = ""
                    st.session_state.current_pdf_query = None

                    st.success(
                        f"✓ PDF '{uploaded_pdf.name}' "
                        f"indexed successfully!"
                    )

                    pages = data.get("pages", "N/A")
                    chunks = data.get("chunks", "N/A")

                    st.caption(
                        f"Pages processed: {pages} | "
                        f"Chunks created: {chunks}"
                    )

                    st.info(
                        "You can now ask questions about this document."
                    )

                else:
                    st.session_state.pdf_document_id = None
                    st.session_state.attached_filename = None
                    st.session_state.attached_pdf_hash = None

                    st.error(
                        f"PDF upload failed: {result['error']}"
                    )

            else:
                st.error(
                    "The previous PDF could not be removed. "
                    "Please retry before uploading another document."
                )

        else:
            st.success(
                f"✓ Active PDF: "
                f"'{st.session_state.attached_filename}'"
            )

    if st.session_state.pdf_document_id:
        st.button(
            "Remove uploaded PDF",
            key="btn_remove_pdf",
            on_click=clear_pdf_session
        )

    st.markdown("</div>", unsafe_allow_html=True)

    pdf_chat_container = st.container()

    with pdf_chat_container:
        if not st.session_state.pdf_messages:
            if st.session_state.pdf_document_id:
                st.info(
                    "PDF ready! Ask a question about the uploaded document."
                )
            else:
                st.info(
                    "Upload a PDF document above to start chatting "
                    "with your document."
                )

        else:
            for message in st.session_state.pdf_messages:
                with st.chat_message(message["role"]):
                    st.write(message["content"])

                    if (
                        message["role"] == "assistant"
                        and message.get("sources")
                    ):
                        display_sources(
                            message["sources"],
                            pdf_mode=True
                        )

    # PDF query input
    st.markdown(
        '<div class="bottom-bar-container">',
        unsafe_allow_html=True
    )
    st.markdown(
        '<div class="compact-chat-wrapper">',
        unsafe_allow_html=True
    )

    col_input_p, col_sub_p = st.columns([9, 1])

    with col_input_p:
        pdf_placeholder = (
            f"📄 Asking from: "
            f"{st.session_state.attached_filename}..."
            if st.session_state.attached_filename
            else "Upload a PDF above to ask questions..."
        )

        st.text_input(
            "PDF Query",
            placeholder=pdf_placeholder,
            label_visibility="collapsed",
            key="pdf_input",
            on_change=handle_pdf_submit
        )

    with col_sub_p:
        if st.button(
            "↑",
            help="Send PDF Prompt",
            key="btn_pdf_send"
        ):
            handle_pdf_submit()

    st.markdown("</div></div>", unsafe_allow_html=True)

    # PDF query execution
    if st.session_state.current_pdf_query:
        pdf_query = st.session_state.current_pdf_query
        st.session_state.current_pdf_query = None

        if not st.session_state.pdf_document_id:
            st.error(
                "Please upload a PDF document before asking questions."
            )

        else:
            st.session_state.pdf_messages.append({
                "role": "user",
                "content": pdf_query
            })

            with pdf_chat_container:
                with st.chat_message("assistant"):
                    with st.spinner(
                        "Searching uploaded PDF..."
                    ):
                        result = query_pdf_backend(pdf_query)

                    if result["success"]:
                        st.write(result["answer"])

                        display_sources(
                            result["sources"],
                            pdf_mode=True
                        )

                        st.session_state.pdf_messages.append({
                            "role": "assistant",
                            "content": result["answer"],
                            "sources": result["sources"]
                        })

                    else:
                        st.error(result["error"])

            st.rerun()
