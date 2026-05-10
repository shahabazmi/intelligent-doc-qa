import hashlib
import requests
import streamlit as st

API = "http://localhost:8000"
HTTP_TIMEOUT = (10, 300)

st.set_page_config(
    page_title="Enterprise Doc AI",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Styling ───────────────────────────────────────────────────────────────────
st.markdown("""
<style>
/* ── Base ── */
.stApp { background: #0d1117; color: #e6edf3; }
#MainMenu, footer, header { visibility: hidden; }

/* ── Sidebar ── */
[data-testid="stSidebar"] {
    background: #010409 !important;
    border-right: 1px solid #21262d !important;
    min-width: 260px !important;
    max-width: 260px !important;
}
[data-testid="stSidebar"] p,
[data-testid="stSidebar"] span,
[data-testid="stSidebar"] label { color: #8b949e !important; font-size: 0.83rem !important; }

/* ── Buttons ── */
.stButton > button {
    background: #161b22 !important;
    color: #c9d1d9 !important;
    border: 1px solid #30363d !important;
    border-radius: 8px !important;
    font-size: 0.84rem !important;
    font-weight: 500 !important;
    transition: all 0.18s ease !important;
    padding: 6px 12px !important;
}
.stButton > button:hover {
    background: rgba(31,111,235,0.14) !important;
    border-color: #388bfd !important;
    color: #79c0ff !important;
}

/* ── Chat messages ── */
[data-testid="stChatMessage"] {
    background: #161b22 !important;
    border: 1px solid #21262d !important;
    border-radius: 14px !important;
    margin: 8px 0 !important;
    padding: 14px !important;
    box-shadow: 0 2px 8px rgba(0,0,0,0.25) !important;
}
[data-testid="stChatMessage"] p { color: #c9d1d9 !important; line-height: 1.75 !important; }

/* ── Chat input (no red border) ── */
[data-testid="stBottom"] {
    background: #0d1117 !important;
    border-top: 1px solid #21262d !important;
    padding-top: 4px !important;
}
[data-testid="stBottom"] > div,
[data-testid="stBottom"] > div > div { border: none !important; box-shadow: none !important; outline: none !important; }
[data-testid="stChatInput"],
[data-testid="stChatInput"] > div,
[data-testid="stChatInput"] > div > div { border: none !important; box-shadow: none !important; outline: none !important; }
[data-testid="stChatInput"] textarea {
    background: #161b22 !important;
    border: 1px solid #30363d !important;
    border-radius: 14px !important;
    color: #e6edf3 !important;
    font-size: 0.95rem !important;
    outline: none !important;
    box-shadow: none !important;
}
[data-testid="stChatInput"] textarea:focus {
    border-color: #388bfd !important;
    box-shadow: 0 0 0 3px rgba(56,139,253,0.12) !important;
    outline: none !important;
}
[data-testid="stChatInput"] textarea:invalid,
[data-testid="stChatInput"] textarea:required,
[data-testid="stChatInput"] textarea:focus-visible,
[data-testid="stChatInput"] textarea:focus:invalid { box-shadow: none !important; outline: none !important; }
*:focus { outline-color: #388bfd !important; }
input:invalid, textarea:invalid { box-shadow: none !important; }

/* ── Popover attach button (paperclip icon near chat input) ── */
[data-testid="stPopover"] > div > button {
    background: #161b22 !important;
    border: 1px solid #30363d !important;
    border-radius: 10px !important;
    color: #8b949e !important;
    font-size: 1.05rem !important;
    padding: 6px 14px !important;
    transition: all 0.18s ease !important;
}
[data-testid="stPopover"] > div > button:hover {
    border-color: #388bfd !important;
    color: #79c0ff !important;
    background: rgba(56,139,253,0.1) !important;
}
/* File uploader inside popover */
div[data-testid="stFileUploaderDropzone"] {
    background: #161b22 !important;
    border: 1px dashed #30363d !important;
    border-radius: 10px !important;
    padding: 10px 14px !important;
    transition: border-color 0.2s ease !important;
}
div[data-testid="stFileUploaderDropzone"]:hover { border-color: #388bfd !important; }

/* ── Text input (rename) ── */
[data-testid="stTextInput"] input {
    background: #21262d !important;
    border: 1px solid #388bfd !important;
    color: #e6edf3 !important;
    border-radius: 8px !important;
    font-size: 0.85rem !important;
}

/* ── Alerts ── */
.stSuccess { background: #0d1f0d !important; border: 1px solid #238636 !important; border-radius: 8px !important; }
.stError   { background: #2b0d0d !important; border: 1px solid #da3633 !important; border-radius: 8px !important; }
.stInfo    { background: #0d1726 !important; border: 1px solid #388bfd !important; border-radius: 8px !important; }

/* ── Misc ── */
hr { border-color: #21262d !important; margin: 8px 0 !important; }
h1, h2, h3, h4 { color: #e6edf3 !important; }
p, li, .stMarkdown p { color: #c9d1d9 !important; line-height: 1.75 !important; }
strong { color: #e6edf3 !important; }
code { background: #1c2128 !important; color: #a5d6ff !important; border-radius: 4px !important; padding: 2px 6px !important; }
pre  { background: #161b22 !important; border: 1px solid #30363d !important; border-radius: 8px !important; padding: 12px !important; }
.stSpinner { border-top-color: #388bfd !important; }
[data-testid="stSidebar"]::-webkit-scrollbar { width: 4px; }
[data-testid="stSidebar"]::-webkit-scrollbar-track { background: transparent; }
[data-testid="stSidebar"]::-webkit-scrollbar-thumb { background: #21262d; border-radius: 4px; }
</style>
""", unsafe_allow_html=True)


# ── API helpers ───────────────────────────────────────────────────────────────
def _post(path, **kw):
    return requests.post(f"{API}{path}", timeout=HTTP_TIMEOUT, **kw)

def _get(path):
    return requests.get(f"{API}{path}", timeout=(5, 30))

def _delete(path):
    return requests.delete(f"{API}{path}", timeout=(10, 30))

def _fetch_documents():
    try:
        r = _get("/documents")
        return r.json() if r.ok else []
    except requests.RequestException:
        return []

def _fetch_conversations():
    try:
        r = _get("/conversations")
        return r.json() if r.ok else []
    except requests.RequestException:
        return []


# ── Session state ─────────────────────────────────────────────────────────────
for key, val in {
    "msgs": [],
    "pending_query": None,
    "conversation_id": None,
    "renaming_conv": None,
    "uploaded_hashes": set(),
}.items():
    if key not in st.session_state:
        st.session_state[key] = val


# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    # Brand
    st.markdown("""
    <div style="padding:18px 4px 10px 4px;">
        <div style="font-size:1.2rem;font-weight:700;letter-spacing:-0.3px;
                    background:linear-gradient(135deg,#58a6ff,#79c0ff);
                    -webkit-background-clip:text;-webkit-text-fill-color:transparent;">
            🤖 Enterprise Doc AI
        </div>
        <div style="font-size:0.75rem;color:#484f58;margin-top:2px;">
            Powered by local AI · private &amp; fast
        </div>
    </div>
    """, unsafe_allow_html=True)

    # New Conversation — immediately show rename input
    if st.button("＋  New Conversation", use_container_width=True):
        try:
            r = _post("/conversations")
            if r.ok:
                cid = r.json()["id"]
                st.session_state.conversation_id = cid
                st.session_state.msgs = []
                st.session_state.renaming_conv = cid  # open rename right away
                st.rerun()
        except requests.RequestException:
            st.error("Backend offline. Run: `uvicorn backend.main:app --reload --reload-dir backend`")

    st.divider()

    # ── Conversation list ─────────────────────────────────────────────────────
    conversations = _fetch_conversations()
    if conversations:
        for conv in conversations:
            cid       = conv["id"]
            raw_title = (conv.get("title") or "").strip()
            title     = raw_title if raw_title else cid[:12] + "…"
            is_active   = cid == st.session_state.conversation_id
            is_renaming = st.session_state.renaming_conv == cid

            if is_renaming:
                new_title = st.text_input(
                    "Rename", value=raw_title,
                    key=f"rename_input_{cid}",
                    label_visibility="collapsed",
                    placeholder="Give this conversation a name…",
                )
                c1, c2 = st.columns(2)
                with c1:
                    if st.button("✓ Save", key=f"save_{cid}", use_container_width=True):
                        if new_title.strip():
                            try:
                                _post(f"/conversations/{cid}/rename", data={"title": new_title.strip()})
                            except requests.RequestException:
                                pass
                        st.session_state.renaming_conv = None
                        st.rerun()
                with c2:
                    if st.button("Cancel", key=f"cancel_{cid}", use_container_width=True):
                        st.session_state.renaming_conv = None
                        st.rerun()
            else:
                prefix = "▶ " if is_active else ""
                c_title, c_edit, c_del = st.columns([6, 1, 1])
                with c_title:
                    display = (prefix + title)[:28]
                    if st.button(display, key=f"conv_{cid}", use_container_width=True, help=title):
                        st.session_state.conversation_id = cid
                        try:
                            r = _get(f"/conversations/{cid}")
                            if r.ok:
                                st.session_state.msgs = [
                                    {"role": m["role"], "content": m["content"]}
                                    for m in r.json()["messages"]
                                ]
                        except requests.RequestException:
                            pass
                        st.rerun()
                with c_edit:
                    if st.button("✏", key=f"edit_{cid}", help="Rename"):
                        st.session_state.renaming_conv = cid
                        st.rerun()
                with c_del:
                    if st.button("✕", key=f"del_{cid}", help="Delete"):
                        try:
                            _delete(f"/conversations/{cid}")
                        except requests.RequestException:
                            pass
                        if st.session_state.conversation_id == cid:
                            st.session_state.conversation_id = None
                            st.session_state.msgs = []
                        st.rerun()
    else:
        st.caption("No conversations yet — start chatting below.")

    # ── Indexed documents (sidebar, below conversations) ──────────────────────
    sidebar_docs = _fetch_documents()
    if sidebar_docs:
        st.divider()
        st.markdown(
            '<div style="font-size:0.75rem;font-weight:600;color:#484f58;'
            'text-transform:uppercase;letter-spacing:0.6px;padding:4px 0 6px 0;">'
            '📄 Indexed Documents</div>',
            unsafe_allow_html=True,
        )
        for doc in sidebar_docs:
            ext  = doc["original_filename"].rsplit(".", 1)[-1].lower()
            icon = {"pdf": "📕", "docx": "📘", "txt": "📃"}.get(ext, "📎")
            c1, c2 = st.columns([5, 1])
            with c1:
                name = doc["original_filename"]
                display_name = name if len(name) <= 22 else name[:20] + "…"
                st.caption(f"{icon} {display_name}  ·  {doc['chunk_count']} chunks")
            with c2:
                if st.button("✕", key=f"rm_{doc['id']}", help="Remove document"):
                    with st.spinner("Removing…"):
                        try:
                            _delete(f"/documents/{doc['id']}")
                        except requests.RequestException:
                            pass
                    st.session_state.uploaded_hashes = set()
                    st.rerun()
        if st.button("🗑  Remove all documents", use_container_width=True):
            try:
                _post("/documents/clear")
            except requests.RequestException:
                pass
            st.session_state.uploaded_hashes = set()
            st.rerun()


# ── Main area ─────────────────────────────────────────────────────────────────

# Empty state
if not st.session_state.msgs:
    st.markdown("""
    <div style="display:flex;flex-direction:column;align-items:center;justify-content:center;
                min-height:52vh;text-align:center;padding:40px 20px;">
        <div style="font-size:4rem;margin-bottom:14px;
                    filter:drop-shadow(0 0 20px rgba(88,166,255,0.4));">🤖</div>
        <div style="font-size:1.65rem;font-weight:700;margin-bottom:10px;letter-spacing:-0.5px;
                    background:linear-gradient(135deg,#58a6ff,#a5d6ff);
                    -webkit-background-clip:text;-webkit-text-fill-color:transparent;">
            Enterprise Doc AI
        </div>
        <div style="font-size:0.93rem;color:#8b949e;max-width:460px;line-height:1.85;">
            Attach documents with the <strong style="color:#c9d1d9;">📎 button below</strong>
            and ask questions — or just start chatting about anything.
        </div>
        <div style="margin-top:26px;display:flex;gap:10px;flex-wrap:wrap;justify-content:center;">
            <span style="background:#161b22;border:1px solid #30363d;border-radius:20px;
                         padding:6px 16px;font-size:0.81rem;color:#8b949e;">📄 PDF · DOCX · TXT</span>
            <span style="background:#161b22;border:1px solid #30363d;border-radius:20px;
                         padding:6px 16px;font-size:0.81rem;color:#8b949e;">🔍 Deep document search</span>
            <span style="background:#161b22;border:1px solid #30363d;border-radius:20px;
                         padding:6px 16px;font-size:0.81rem;color:#8b949e;">🌐 General knowledge</span>
            <span style="background:#161b22;border:1px solid #30363d;border-radius:20px;
                         padding:6px 16px;font-size:0.81rem;color:#8b949e;">🌦 Live weather</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

# Chat history
for msg in st.session_state.msgs:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])


# ── Attach button (paperclip popover — sits right above the chat input) ───────
docs_now = _fetch_documents()
doc_badge = f" · {len(docs_now)} indexed" if docs_now else ""
_col, _spacer = st.columns([1, 9])
with _col:
    with st.popover(f"📎{doc_badge}"):
        st.markdown(
            "**Attach documents**  \n"
            "<span style='color:#8b949e;font-size:0.82rem;'>PDF · DOCX · TXT · images — "
            "select multiple files at once</span>",
            unsafe_allow_html=True,
        )
        uploaded_files = st.file_uploader(
            "Choose files",
            type=["pdf", "docx", "txt", "png", "jpg", "jpeg"],
            accept_multiple_files=True,
            key="file_uploader",
            label_visibility="collapsed",
        )
        if uploaded_files:
            for uf in uploaded_files:
                file_bytes = uf.getvalue()
                fhash = hashlib.sha256(file_bytes).hexdigest()
                if fhash not in st.session_state.uploaded_hashes:
                    with st.spinner(f"Indexing {uf.name}…"):
                        try:
                            r = _post("/upload", files={"file": (uf.name, file_bytes)})
                        except requests.RequestException as e:
                            st.error(f"Upload failed — is the backend running?\n`{e}`")
                            r = None
                    if r is not None:
                        if r.ok:
                            st.session_state.uploaded_hashes.add(fhash)
                            st.rerun()
                        else:
                            st.error(f"Upload error: {r.text[:300]}")


# ── Handle pending query ──────────────────────────────────────────────────────
if st.session_state.pending_query is not None:
    q = st.session_state.pending_query
    st.session_state.pending_query = None

    with st.spinner("Thinking…"):
        try:
            data = {"query": q}
            if st.session_state.conversation_id:
                data["conversation_id"] = st.session_state.conversation_id
            r = _post("/query", data=data)
        except requests.RequestException as e:
            answer = (
                "❌ **Backend is not running.**\n\n"
                "Start it in a terminal:\n"
                "```\nuvicorn backend.main:app --reload --reload-dir backend\n```\n\n"
                f"`{e}`"
            )
            st.session_state.msgs.append({"role": "assistant", "content": answer})
        else:
            if r.ok:
                d = r.json()
                answer = (d.get("answer") or "").strip()
                if not answer:
                    answer = (
                        "⚠️ The model returned an empty response.\n\n"
                        "Make sure Ollama is running: `ollama serve`\n"
                        "And the model is pulled: `ollama pull llama3.2:3b`"
                    )
                elif d.get("sources"):
                    answer += "\n\n---\n**Sources:**"
                    for s in d["sources"]:
                        snippet = (s.get("text") or "")[:160].replace("\n", " ")
                        answer += f"\n- 📄 `{s.get('file','?')}` — p{s.get('page','?')}: _{snippet}_"
                st.session_state.msgs.append({"role": "assistant", "content": answer})
            else:
                st.session_state.msgs.append({
                    "role": "assistant",
                    "content": f"❌ **Error {r.status_code}**\n```\n{r.text[:400]}\n```",
                })
    st.rerun()


# ── Chat input ────────────────────────────────────────────────────────────────
if q := st.chat_input("Ask anything — documents, general knowledge, or just chat…"):
    st.session_state.msgs.append({"role": "user", "content": q})

    # Auto-create conversation so it appears in the sidebar immediately
    if not st.session_state.conversation_id:
        try:
            r = _post("/conversations")
            if r.ok:
                st.session_state.conversation_id = r.json()["id"]
        except requests.RequestException:
            pass

    st.session_state.pending_query = q
    st.rerun()
