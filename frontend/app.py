import hashlib
import html as html_mod
import requests
import streamlit as st

API = "http://localhost:8000"
HTTP_TIMEOUT = (10, 300)

st.set_page_config(
    page_title="enterprise-doc-ai",
    page_icon="◆",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Styling ───────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Instrument+Serif:ital@0;1&family=Geist:wght@300;400;500;600;700&family=Geist+Mono:wght@400;500;600&display=swap');

/* ── Design tokens ── */
:root {
    --bg:          #0a0a0c;
    --bg-2:        #0f0f15;
    --surface:     #14141d;
    --surface-2:   #1a1a24;
    --surface-3:   #20202c;
    --border:      #25252f;
    --border-soft: #1a1a22;
    --hairline:    rgba(255,255,255,0.05);
    --text:        #ededf3;
    --text-2:      #b4b4c2;
    --text-3:      #76768a;
    --text-4:      #45455a;
    --accent:      #a78bfa;
    --accent-2:    #c4b5fd;
    --accent-soft: rgba(167,139,250,0.10);
    --accent-ring: rgba(167,139,250,0.28);
    --cream:       #f0e6d2;
    --success:     #34d399;
    --danger:      #f87171;
    --radius-lg:   14px;
    --radius-md:   10px;
    --radius-sm:   7px;
    --shadow-1:    0 1px 2px rgba(0,0,0,0.5), 0 0 0 1px rgba(255,255,255,0.02);
    --shadow-2:    0 16px 40px rgba(0,0,0,0.5), 0 0 0 1px rgba(255,255,255,0.03);
    --font-display:"Instrument Serif", "Times New Roman", Georgia, serif;
    --font-body:   "Geist", -apple-system, BlinkMacSystemFont, "SF Pro Text", system-ui, sans-serif;
    --font-mono:   "Geist Mono", "SF Mono", ui-monospace, Menlo, monospace;
    --sidebar-w:   300px;
}
body:has([data-testid="stSidebar"][aria-expanded="false"]) { --sidebar-w: 0px; }

/* ── Base ── */
html, body, .stApp, .stMarkdown, p, button, input, textarea {
    font-family: var(--font-body);
}
/* Restore Material Icons font for Streamlit icon glyphs */
[data-testid="stIconMaterial"],
.material-symbols-rounded,
.material-symbols-outlined,
span[translate="no"][class*="ed4y4ls"] {
    font-family: "Material Symbols Rounded", "Material Symbols Outlined", "Material Icons" !important;
    font-weight: normal !important;
    font-style: normal !important;
    line-height: 1 !important;
    letter-spacing: normal !important;
    text-transform: none !important;
    white-space: nowrap !important;
    word-wrap: normal !important;
    direction: ltr !important;
    -webkit-font-feature-settings: 'liga' !important;
    -webkit-font-smoothing: antialiased !important;
}
.stApp {
    background:
      radial-gradient(900px 480px at 80% -10%, rgba(167,139,250,0.06), transparent 60%),
      radial-gradient(700px 400px at -10% 100%, rgba(240,230,210,0.025), transparent 60%),
      var(--bg) !important;
    color: var(--text) !important;
    -webkit-font-smoothing: antialiased;
    text-rendering: optimizeLegibility;
    font-feature-settings: "ss01", "cv11";
}
/* Soft grain overlay */
.stApp::before {
    content: "";
    position: fixed; inset: 0;
    pointer-events: none; z-index: 0;
    opacity: 0.035;
    background-image: url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='160' height='160'><filter id='n'><feTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='2' stitchTiles='stitch'/></filter><rect width='100%' height='100%' filter='url(%23n)' opacity='0.6'/></svg>");
}
#MainMenu, footer { visibility: hidden; }
[data-testid="stHeader"] { background: transparent !important; }

::selection { background: rgba(167,139,250,0.32); color: #fff; }

/* main content rhythm */
.block-container {
    max-width: 780px !important;
    padding-top: 2.4rem !important;
    padding-bottom: 9rem !important;
    position: relative; z-index: 1;
}

/* ── Sidebar ── */
[data-testid="stSidebar"] {
    background: #0c0c12 !important;
    border-right: 1px solid var(--border) !important;
    min-width: 300px !important;
    max-width: 300px !important;
}
[data-testid="stSidebar"] > div:first-child { background: transparent !important; padding-top: 0.4rem !important; }
[data-testid="stSidebar"] p,
[data-testid="stSidebar"] span,
[data-testid="stSidebar"] label {
    color: var(--text-2) !important;
    font-size: 0.83rem !important;
}
[data-testid="stSidebar"] hr {
    border-color: var(--hairline) !important;
    margin: 12px 0 !important;
}
[data-testid="stSidebar"]::-webkit-scrollbar { width: 5px; }
[data-testid="stSidebar"]::-webkit-scrollbar-track { background: transparent; }
[data-testid="stSidebar"]::-webkit-scrollbar-thumb { background: var(--surface-2); border-radius: 6px; }
[data-testid="stSidebar"]::-webkit-scrollbar-thumb:hover { background: var(--surface-3); }
[data-testid="stSidebarCollapseButton"] button,
[data-testid="stSidebarCollapsedControl"] button {
    background: var(--surface) !important;
    border: 1px solid var(--border) !important;
    border-radius: 10px !important;
    color: var(--text) !important;
    box-shadow: var(--shadow-1) !important;
}

/* ── Brand ── */
.brand {
    padding: 8px 4px 18px 4px;
    border-bottom: 1px solid var(--hairline);
    margin-bottom: 4px;
}
.brand-row {
    display: flex; align-items: center; gap: 12px;
}
.brand-monogram {
    width: 34px; height: 34px;
    display: inline-flex; align-items: center; justify-content: center;
    background: linear-gradient(180deg, var(--surface-2), var(--bg-2));
    border: 1px solid var(--border);
    border-radius: 9px;
    font-family: var(--font-display);
    font-style: italic;
    font-size: 1.45rem;
    color: var(--cream);
    line-height: 1;
    padding-bottom: 3px;
    box-shadow: inset 0 1px 0 rgba(255,255,255,0.04), 0 4px 12px rgba(0,0,0,0.35);
}
.brand-name {
    font-family: var(--font-mono);
    font-size: 0.93rem;
    font-weight: 500;
    color: var(--text);
    letter-spacing: -0.2px;
}
.brand-name .brand-dim { color: var(--text-3); }
.brand-tagline {
    font-family: var(--font-display);
    font-style: italic;
    font-size: 0.86rem;
    color: var(--text-3);
    margin-top: 8px;
    padding-left: 46px;
    letter-spacing: 0.1px;
}

/* Section labels */
.section-label {
    font-family: var(--font-mono);
    font-size: 0.66rem;
    font-weight: 500;
    color: var(--text-4);
    text-transform: uppercase;
    letter-spacing: 1.4px;
    padding: 14px 4px 8px 4px;
    display: flex; align-items: center; gap: 8px;
}
.section-label::before {
    content: ""; width: 14px; height: 1px;
    background: var(--text-4);
    display: inline-block;
}
.section-label .count {
    color: var(--text-3);
    font-weight: 500;
    letter-spacing: 0;
    margin-left: auto;
}

/* ── Buttons (default — use descendant combinator to handle tooltip-wrapped buttons) ── */
.stApp .stButton button,
.stApp [data-testid="stBaseButton-secondary"] {
    background: transparent !important;
    color: var(--text-2) !important;
    border: 1px solid transparent !important;
    border-radius: var(--radius-sm) !important;
    font-size: 0.84rem !important;
    font-weight: 400 !important;
    transition: background 0.15s ease, border-color 0.15s ease, color 0.15s ease !important;
    padding: 6px 10px !important;
    box-shadow: none !important;
}
.stApp .stButton button:hover,
.stApp [data-testid="stBaseButton-secondary"]:hover {
    background: var(--surface) !important;
    border-color: var(--border-soft) !important;
    color: var(--text) !important;
}
.stApp .stButton button p,
.stApp [data-testid="stBaseButton-secondary"] p {
    font-family: var(--font-body) !important;
    font-size: 0.84rem !important;
    color: inherit !important;
}

/* Active conversation tint (rows whose label starts with ●) */
[data-testid="stSidebar"] .stButton button:has(p:first-letter) { }

/* Primary "New Conversation" — the second top-level child of the sidebar's vertical block */
[data-testid="stSidebar"] [data-testid="stSidebarUserContent"] > div > [data-testid="stVerticalBlock"] > [data-testid="stElementContainer"]:nth-of-type(2) .stButton button {
    background: var(--surface) !important;
    border: 1px solid var(--border) !important;
    color: var(--text) !important;
    font-weight: 500 !important;
    text-align: center !important;
    justify-content: center !important;
    padding: 9px 12px !important;
    box-shadow: var(--shadow-1) !important;
}
[data-testid="stSidebar"] [data-testid="stSidebarUserContent"] > div > [data-testid="stVerticalBlock"] > [data-testid="stElementContainer"]:nth-of-type(2) .stButton button:hover {
    background: var(--accent-soft) !important;
    border-color: var(--accent) !important;
    color: var(--accent) !important;
}

/* ── Chat messages ── */
[data-testid="stChatMessage"] {
    background: transparent !important;
    border: none !important;
    border-radius: 0 !important;
    margin: 4px 0 !important;
    padding: 14px 0 !important;
    box-shadow: none !important;
    animation: fadeUp 0.4s cubic-bezier(.2,.7,.2,1);
    position: relative;
}
[data-testid="stChatMessage"] + [data-testid="stChatMessage"] {
    border-top: 1px solid var(--hairline) !important;
}
@keyframes fadeUp {
    from { opacity: 0; transform: translateY(4px); }
    to   { opacity: 1; transform: translateY(0); }
}
[data-testid="stChatMessage"] p {
    color: var(--text) !important;
    line-height: 1.74 !important;
    font-size: 0.96rem !important;
    font-family: var(--font-body);
}
[data-testid="stChatMessage"] p strong { color: var(--text); }
[data-testid="stChatMessage"] li { color: var(--text-2); line-height: 1.7 !important; }

/* Avatar – styled tile; preserve Material Icons font so the glyph renders */
[data-testid="stChatMessageAvatarUser"],
[data-testid="stChatMessageAvatarAssistant"] {
    width: 30px !important; height: 30px !important;
    border-radius: 8px !important;
    font-size: 1rem !important;
    color: var(--text-2) !important;
    background: linear-gradient(180deg, var(--surface-2), var(--bg-2)) !important;
    border: 1px solid var(--border) !important;
    box-shadow: inset 0 1px 0 rgba(255,255,255,0.04), var(--shadow-1) !important;
}
[data-testid="stChatMessageAvatarAssistant"] {
    background: linear-gradient(180deg, rgba(167,139,250,0.15), rgba(167,139,250,0.04)) !important;
    border-color: rgba(167,139,250,0.3) !important;
    color: var(--accent-2) !important;
}

/* ── Chat input — ChatGPT/Claude style with native paperclip ── */
[data-testid="stBottom"] {
    background:
      linear-gradient(180deg, rgba(10,10,12,0) 0%, rgba(10,10,12,0.96) 35%) !important;
    border-top: none !important;
    padding: 14px 0 22px 0 !important;
}
[data-testid="stBottom"] > div { background: transparent !important; }
[data-testid="stBottom"] > div,
[data-testid="stBottom"] > div > div {
    border: none !important; box-shadow: none !important; outline: none !important;
}

/* The outer chat-input bar — this is the visible "card" */
[data-testid="stChatInput"] {
    max-width: 760px !important;
    margin: 0 auto !important;
    background: var(--surface) !important;
    border: 1px solid var(--border) !important;
    border-radius: 20px !important;
    box-shadow: var(--shadow-2) !important;
    overflow: hidden !important;
    transition: border-color 0.18s ease, box-shadow 0.18s ease !important;
}
[data-testid="stChatInput"]:focus-within {
    border-color: var(--accent) !important;
    box-shadow: 0 0 0 4px var(--accent-ring), var(--shadow-2) !important;
}
[data-testid="stChatInput"] > div,
[data-testid="stChatInput"] > div > div {
    background: transparent !important;
    border: none !important; box-shadow: none !important; outline: none !important;
}
/* Kill BaseWeb's inner wrapper light background */
[data-testid="stChatInput"] div {
    background-color: transparent !important;
}

/* Inner textarea — transparent so the outer card shows through */
[data-testid="stChatInput"] textarea {
    background: transparent !important;
    border: none !important;
    color: var(--text) !important;
    font-family: var(--font-body) !important;
    font-size: 0.97rem !important;
    line-height: 1.55 !important;
    padding: 16px 18px !important;
    outline: none !important;
    box-shadow: none !important;
    min-height: 50px !important;
}
[data-testid="stChatInput"] textarea::placeholder { color: var(--text-3) !important; }
[data-testid="stChatInput"] textarea:focus {
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
}
[data-testid="stChatInput"] textarea:invalid,
[data-testid="stChatInput"] textarea:focus-visible,
[data-testid="stChatInput"] textarea:focus:invalid { box-shadow: none !important; outline: none !important; }
*:focus { outline-color: var(--accent) !important; }
input:invalid, textarea:invalid { box-shadow: none !important; }

/* Action row (paperclip on left, send on right) — sits below textarea */
[data-testid="stChatInput"] > div > div:last-child,
[data-testid="stChatInput"] [data-testid="stChatInputFileUploadButton"] {
    background: transparent !important;
}

/* Native attach (paperclip) button — left of action row */
[data-testid="stChatInputFileUploadButton"] {
    margin-left: 10px !important;
}
[data-testid="stChatInputFileUploadButton"] button,
[data-testid="stChatInputFileUploadButton"] [aria-label="Upload files"] {
    background: transparent !important;
    border: 1px solid transparent !important;
    border-radius: 50% !important;
    color: var(--text-3) !important;
    width: 34px !important; height: 34px !important;
    min-width: 34px !important;
    display: inline-flex !important; align-items: center !important; justify-content: center !important;
    transition: background 0.15s ease, border-color 0.15s ease, color 0.15s ease !important;
}
[data-testid="stChatInputFileUploadButton"] button:hover {
    background: var(--accent-soft) !important;
    border-color: var(--accent-ring) !important;
    color: var(--accent) !important;
}
[data-testid="stChatInputFileUploadButton"] svg {
    color: var(--text-3) !important;
    fill: currentColor !important;
    width: 18px !important; height: 18px !important;
}
[data-testid="stChatInputFileUploadButton"] button:hover svg {
    color: var(--accent) !important;
}

/* Send button (right of action row) */
[data-testid="stChatInputSubmitButton"],
[data-testid="stChatInput"] button[data-testid="stChatInputSubmitButton"] {
    background: var(--accent) !important;
    border: none !important;
    border-radius: 10px !important;
    color: #0a0a0c !important;
    width: 34px !important; height: 34px !important;
    margin-right: 10px !important;
    box-shadow: 0 6px 16px rgba(167,139,250,0.32) !important;
    transition: filter 0.15s ease, transform 0.15s ease !important;
}
[data-testid="stChatInputSubmitButton"]:hover {
    filter: brightness(1.08); transform: translateY(-1px);
}
[data-testid="stChatInputSubmitButton"] svg {
    fill: #0a0a0c !important; color: #0a0a0c !important;
    width: 18px !important; height: 18px !important;
}
[data-testid="stChatInputSubmitButton"][disabled] {
    background: var(--surface-3) !important;
    color: var(--text-3) !important;
    box-shadow: none !important;
}
[data-testid="stChatInputSubmitButton"][disabled] svg { fill: var(--text-3) !important; color: var(--text-3) !important; }

/* Attached-files chip strip (above textarea when files are queued) */
[data-testid="stChatInput"] [data-testid="stFileUploaderFileName"] {
    color: var(--text-2) !important;
    font-family: var(--font-mono) !important;
    font-size: 0.78rem !important;
}

/* ── Text input (rename) ── */
[data-testid="stTextInput"] input {
    background: var(--surface-2) !important;
    border: 1px solid var(--accent) !important;
    color: var(--text) !important;
    border-radius: var(--radius-sm) !important;
    font-size: 0.85rem !important;
    box-shadow: 0 0 0 3px var(--accent-ring) !important;
    font-family: var(--font-body) !important;
}

/* ── Alerts ── */
.stSuccess { background: rgba(52,211,153,0.08) !important; border: 1px solid rgba(52,211,153,0.35) !important; border-radius: var(--radius-md) !important; }
.stError   { background: rgba(248,113,113,0.08) !important; border: 1px solid rgba(248,113,113,0.35) !important; border-radius: var(--radius-md) !important; }
.stInfo    { background: var(--accent-soft) !important; border: 1px solid var(--accent-ring) !important; border-radius: var(--radius-md) !important; }

/* ── Typography ── */
hr { border-color: var(--hairline) !important; margin: 10px 0 !important; }
h1, h2, h3, h4 { color: var(--text) !important; letter-spacing: -0.3px; font-family: var(--font-body); }
p, li, .stMarkdown p { color: var(--text-2); line-height: 1.72; }
strong { color: var(--text) !important; }
em, i { font-family: var(--font-display); font-style: italic; }
code {
    background: var(--surface-2) !important;
    color: var(--accent-2) !important;
    border-radius: 5px !important;
    padding: 2px 7px !important;
    font-family: var(--font-mono) !important;
    font-size: 0.85em !important;
}
pre {
    background: var(--bg-2) !important;
    border: 1px solid var(--border) !important;
    border-radius: var(--radius-md) !important;
    padding: 14px !important;
    font-family: var(--font-mono) !important;
}
pre code { background: transparent !important; padding: 0 !important; }
kbd {
    background: var(--surface-2);
    border: 1px solid var(--border);
    border-bottom-width: 2px;
    border-radius: 6px;
    padding: 1px 7px;
    font-family: var(--font-mono);
    font-size: 0.82em;
    color: var(--text);
}
.stSpinner > div > div { border-top-color: var(--accent) !important; }

/* ── Welcome / empty state ── */
.welcome {
    display: flex; flex-direction: column; align-items: flex-start;
    min-height: 52vh; padding: 26px 4px 40px 4px;
    animation: fadeUp 0.6s cubic-bezier(.2,.7,.2,1);
}
.welcome-eyebrow {
    font-family: var(--font-mono);
    font-size: 0.72rem;
    color: var(--text-3);
    letter-spacing: 2.5px;
    text-transform: uppercase;
    margin-bottom: 18px;
    display: flex; align-items: center; gap: 10px;
}
.welcome-eyebrow .dot {
    width: 6px; height: 6px; background: var(--accent); border-radius: 50%;
    box-shadow: 0 0 12px var(--accent);
    animation: pulse 2.4s ease-in-out infinite;
}
@keyframes pulse {
    0%, 100% { opacity: 0.6; transform: scale(1); }
    50%      { opacity: 1; transform: scale(1.18); }
}
.welcome-head {
    display: flex; align-items: center; gap: 18px;
    margin-bottom: 14px;
}
.welcome-logo {
    width: 56px; height: 56px;
    border-radius: 14px;
    background: linear-gradient(180deg, var(--surface-2), var(--bg-2));
    border: 1px solid var(--border);
    display: inline-flex; align-items: center; justify-content: center;
    font-family: var(--font-display);
    font-style: italic;
    font-size: 2.2rem;
    color: var(--cream);
    padding-bottom: 6px;
    box-shadow: inset 0 1px 0 rgba(255,255,255,0.05),
                0 12px 32px rgba(0,0,0,0.4);
    flex-shrink: 0;
    position: relative;
}
.welcome-logo::after {
    content: ""; position: absolute; inset: -10px;
    border-radius: 22px;
    background: radial-gradient(closest-side, rgba(167,139,250,0.22), transparent 70%);
    z-index: -1; filter: blur(14px);
}
.welcome-title {
    font-family: var(--font-mono);
    font-size: 1.85rem; font-weight: 500;
    letter-spacing: -1.2px; color: var(--text);
    line-height: 1; margin: 0;
}
.welcome-tagline {
    font-family: var(--font-display);
    font-style: italic;
    font-size: 1.35rem;
    color: var(--text-2);
    margin: 2px 0 28px 0;
    letter-spacing: -0.2px;
    line-height: 1.3;
    max-width: 540px;
}
.welcome-tagline .amp {
    color: var(--accent-2); font-size: 1.2em; padding: 0 2px;
}
.welcome-body {
    font-size: 0.95rem; color: var(--text-3);
    max-width: 560px; line-height: 1.75; margin-bottom: 30px;
}
.welcome-body strong { color: var(--text-2); }
.welcome-pills {
    display: flex; gap: 8px; flex-wrap: wrap;
    max-width: 620px;
}
.pill {
    background: var(--surface);
    border: 1px solid var(--hairline);
    border-radius: 999px;
    padding: 7px 14px;
    font-size: 0.78rem;
    color: var(--text-2);
    font-family: var(--font-mono);
    letter-spacing: 0.1px;
    transition: all 0.2s ease;
    display: inline-flex; align-items: center; gap: 7px;
}
.pill::before {
    content: ""; width: 4px; height: 4px;
    background: var(--text-4); border-radius: 50%;
}
.pill:hover {
    border-color: var(--accent-ring);
    color: var(--text);
    background: var(--accent-soft);
}
.pill:hover::before { background: var(--accent); box-shadow: 0 0 6px var(--accent); }

/* ── Source cards ── */
.src-wrap { margin: 18px 0 4px 0; }
.src-label {
    font-family: var(--font-mono);
    font-size: 0.66rem; font-weight: 500;
    color: var(--text-4); text-transform: uppercase; letter-spacing: 1.6px;
    margin: 0 0 10px 0;
    display: flex; align-items: center; gap: 8px;
}
.src-label::before {
    content: ""; width: 16px; height: 1px; background: var(--text-4);
}
.src-grid {
    display: grid; gap: 8px;
    grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
}
.src-card {
    background: var(--surface);
    border: 1px solid var(--border-soft);
    border-radius: var(--radius-md);
    padding: 11px 13px;
    transition: all 0.18s ease;
    position: relative;
}
.src-card::before {
    content: ""; position: absolute; top: 11px; right: 13px;
    width: 4px; height: 4px; border-radius: 50%;
    background: var(--text-4);
}
.src-card:hover {
    border-color: var(--accent-ring);
    background: var(--accent-soft);
    transform: translateY(-1px);
}
.src-card:hover::before { background: var(--accent); }
.src-head {
    display: flex; align-items: center; gap: 6px; margin-bottom: 7px;
}
.src-name {
    color: var(--text); font-family: var(--font-mono);
    font-size: 0.78rem; font-weight: 500;
    flex: 1; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.src-page {
    color: var(--text-3); font-family: var(--font-mono);
    font-size: 0.7rem;
}
.src-snippet {
    font-size: 0.79rem;
    color: var(--text-3);
    line-height: 1.55;
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
    font-family: var(--font-display);
    font-style: italic;
}

/* ── Sidebar document item ── */
.doc-row {
    display: flex; align-items: center; gap: 10px;
    padding: 9px 10px;
    border-radius: var(--radius-sm);
    background: var(--surface);
    border: 1px solid var(--hairline);
    margin: 4px 0;
    transition: border-color 0.15s ease, background 0.15s ease;
}
.doc-row:hover { border-color: var(--border); background: var(--surface-2); }
.doc-icon {
    font-family: var(--font-mono);
    font-size: 0.62rem; font-weight: 600;
    color: var(--text-3);
    background: var(--bg-2);
    border: 1px solid var(--border);
    border-radius: 4px;
    padding: 2px 5px;
    letter-spacing: 0.5px;
    flex-shrink: 0;
}
.doc-meta { display: flex; flex-direction: column; min-width: 0; flex: 1; gap: 1px; }
.doc-name {
    color: var(--text); font-size: 0.83rem; font-weight: 400;
    white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
    font-family: var(--font-body);
}
.doc-sub {
    color: var(--text-3); font-size: 0.7rem;
    font-family: var(--font-mono);
}

/* Active conversation dot indicator (used in button label) */

/* ── Responsiveness ── */
@media (max-width: 920px) {
    .block-container { padding-left: 1rem !important; padding-right: 1rem !important; }
}
@media (max-width: 720px) {
    .welcome-title { font-size: 1.45rem; }
    .welcome-tagline { font-size: 1.1rem; }
    .src-grid { grid-template-columns: 1fr; }
}
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


def _render_sources_html(sources):
    """Safe HTML for source cards."""
    if not sources:
        return ""
    cards = []
    for s in sources:
        fname = str(s.get("file", "?"))
        page = html_mod.escape(str(s.get("page", "?")))
        name_esc = html_mod.escape(fname)
        snippet = (s.get("text") or "")[:220].replace("\n", " ").strip()
        snippet_esc = html_mod.escape(snippet)
        cards.append(
            '<div class="src-card">'
            f'<div class="src-head">'
            f'<span class="src-name" title="{name_esc}">{name_esc}</span>'
            f'<span class="src-page">p.{page}</span>'
            '</div>'
            f'<div class="src-snippet">{snippet_esc}</div>'
            '</div>'
        )
    return (
        '<div class="src-wrap">'
        '<div class="src-label">Cited sources</div>'
        f'<div class="src-grid">{"".join(cards)}</div>'
        '</div>'
    )


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
    st.markdown("""
    <div class="brand">
        <div class="brand-row">
            <span class="brand-monogram">E</span>
            <span class="brand-name">enterprise<span class="brand-dim">-doc-ai</span></span>
        </div>
        <div class="brand-tagline">A local-first research workspace</div>
    </div>
    """, unsafe_allow_html=True)

    # New Conversation
    if st.button("＋  New Conversation", use_container_width=True):
        try:
            r = _post("/conversations")
            if r.ok:
                cid = r.json()["id"]
                st.session_state.conversation_id = cid
                st.session_state.msgs = []
                st.session_state.renaming_conv = cid
                st.rerun()
        except requests.RequestException:
            st.error("Backend offline. Run: `uvicorn backend.main:app --reload --reload-dir backend`")

    # Conversations list
    conversations = _fetch_conversations()
    n_conv = len(conversations) if conversations else 0
    st.markdown(
        f'<div class="section-label">Conversations<span class="count">{n_conv:02d}</span></div>',
        unsafe_allow_html=True,
    )
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
                prefix = "●  " if is_active else "○  "
                c_title, c_edit, c_del = st.columns([6, 1, 1])
                with c_title:
                    display = (prefix + title)[:30]
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

    # Indexed documents
    sidebar_docs = _fetch_documents()
    if sidebar_docs:
        st.markdown(
            f'<div class="section-label">Documents<span class="count">{len(sidebar_docs):02d}</span></div>',
            unsafe_allow_html=True,
        )
        for doc in sidebar_docs:
            name = doc["original_filename"]
            ext  = name.rsplit(".", 1)[-1].lower()
            display_name = name if len(name) <= 26 else name[:24] + "…"
            chunks = doc["chunk_count"]

            c1, c2 = st.columns([6, 1])
            with c1:
                st.markdown(
                    f'<div class="doc-row">'
                    f'<span class="doc-icon">{html_mod.escape(ext.upper())}</span>'
                    f'<span class="doc-meta">'
                    f'<span class="doc-name" title="{html_mod.escape(name)}">{html_mod.escape(display_name)}</span>'
                    f'<span class="doc-sub">{chunks} chunks</span>'
                    f'</span></div>',
                    unsafe_allow_html=True,
                )
            with c2:
                if st.button("✕", key=f"rm_{doc['id']}", help="Remove document"):
                    with st.spinner("Removing…"):
                        try:
                            _delete(f"/documents/{doc['id']}")
                        except requests.RequestException:
                            pass
                    st.session_state.uploaded_hashes = set()
                    st.rerun()

        if st.button("Remove all documents", use_container_width=True):
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
    <div class="welcome">
        <div class="welcome-eyebrow"><span class="dot"></span>Workspace · ready</div>
        <div class="welcome-head">
            <div class="welcome-logo">E</div>
            <h1 class="welcome-title">enterprise-doc-ai</h1>
        </div>
        <div class="welcome-tagline">
            A private research workspace<br/>
            for documents <span class="amp">&amp;</span> ideas, running locally.
        </div>
        <p class="welcome-body">
            Attach files with the <strong>📎 pin inside the search bar</strong> below
            and ask anything — citations included. No data leaves your machine.
        </p>
        <div class="welcome-pills">
            <span class="pill">pdf · docx · txt</span>
            <span class="pill">hybrid retrieval</span>
            <span class="pill">cited answers</span>
            <span class="pill">fully local</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

# Chat history
for msg in st.session_state.msgs:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg.get("sources"):
            st.markdown(_render_sources_html(msg["sources"]), unsafe_allow_html=True)


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
                sources = d.get("sources") or []
                if not answer:
                    answer = (
                        "⚠️ The model returned an empty response.\n\n"
                        "Make sure Ollama is running: `ollama serve`\n"
                        "And the model is pulled: `ollama pull llama3.2:3b`"
                    )
                st.session_state.msgs.append({
                    "role": "assistant",
                    "content": answer,
                    "sources": sources,
                })
            else:
                st.session_state.msgs.append({
                    "role": "assistant",
                    "content": f"❌ **Error {r.status_code}**\n```\n{r.text[:400]}\n```",
                })
    st.rerun()


# ── Chat input — native paperclip is built in via accept_file ────────────────
chat_response = st.chat_input(
    "Ask anything — documents, knowledge, or just chat…",
    accept_file="multiple",
    file_type=["pdf", "docx", "txt", "png", "jpg", "jpeg"],
)

if chat_response:
    text  = getattr(chat_response, "text", None) or (chat_response if isinstance(chat_response, str) else "")
    files = getattr(chat_response, "files", []) or []

    # Index any attached files first (SHA256 dedupe preserved)
    for uf in files:
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
                else:
                    st.error(f"Upload error: {r.text[:300]}")

    if text and text.strip():
        st.session_state.msgs.append({"role": "user", "content": text})
        if not st.session_state.conversation_id:
            try:
                r = _post("/conversations")
                if r.ok:
                    st.session_state.conversation_id = r.json()["id"]
            except requests.RequestException:
                pass
        st.session_state.pending_query = text

    st.rerun()
