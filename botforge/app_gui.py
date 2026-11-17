"""
app_gui.py — BotForge Streamlit GUI with Safe Radial Gradient Background
"""

import os
import requests
import streamlit as st

# ── Page Config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title='BotForge',
    page_icon='⚡',
    layout='centered',
)

# ── Cyberpunk Dark Theme CSS with Safe Background Gradient ────────────────────
st.markdown("""
<style>
    /* Safe Rich Dark Background with Subtle Radial Glow */
    .stApp {
        background: radial-gradient(circle at 15% 15%, rgba(0, 229, 255, 0.08) 0%, transparent 40%),
                    radial-gradient(circle at 85% 85%, rgba(147, 51, 234, 0.08) 0%, transparent 40%),
                    #0b0b0f !important;
        color: #ffffff !important;
    }

    header {visibility: hidden;}
    footer {visibility: hidden;}

    .hero-banner {
        background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
        border-radius: 20px;
        padding: 24px;
        margin-bottom: 20px;
        border: 1px solid rgba(0, 229, 255, 0.3);
        box-shadow: 0 4px 20px rgba(0, 229, 255, 0.1);
    }

    div.stButton > button {
        background: linear-gradient(135deg, #00e5ff 0%, #0088cc 100%) !important;
        color: #000000 !important;
        font-weight: 700 !important;
        border-radius: 14px !important;
        border: none !important;
        padding: 10px 20px !important;
        box-shadow: 0 4px 15px rgba(0, 229, 255, 0.3) !important;
        width: 100% !important;
    }
    div.stButton > button:hover {
        opacity: 0.9 !important;
        color: #000000 !important;
    }

    .stTextInput input, .stTextArea textarea, .stSelectbox select {
        background-color: #16161c !important;
        color: #ffffff !important;
        border: 1px solid rgba(255, 255, 255, 0.15) !important;
        border-radius: 12px !important;
    }

    h1, h2, h3 {
        color: #ffffff !important;
    }
</style>
""", unsafe_allow_html=True)

# ── Connection & State Setup ──────────────────────────────────────────────────
host_ip = os.getenv('HOST_IP', 'localhost')
host_port = os.getenv('HOST_PORT', '8000')
BASE_URL = f'http://{host_ip}:{host_port}'

if 'nav' not in st.session_state:
    st.session_state.nav = 'home'
if 'active_bot_id' not in st.session_state:
    st.session_state.active_bot_id = None
if 'chat_histories' not in st.session_state:
    st.session_state.chat_histories = {}

# Fetch bots
try:
    r = requests.get(f'{BASE_URL}/bots', timeout=2)
    bots = r.json() if r.status_code == 200 else []
except Exception:
    bots = []

# ── NAVIGATION: HOME SCREEN ───────────────────────────────────────────────────
if st.session_state.nav == 'home':
    cols = st.columns([5, 1, 1])
    with cols[0]:
        st.markdown('## ⚡ BotForge')
    with cols[1]:
        st.markdown('🟢 LAN')
    with cols[2]:
        if st.button('⚙️', key='settings_btn'):
            st.session_state.nav = 'settings'
            st.rerun()

    # Hero Banner
    st.markdown("""
    <div class="hero-banner">
        <h3 style="margin:0; color: #00e5ff;">Private LAN Mode</h3>
        <p style="margin:6px 0 0 0; color: #94a3b8; font-size: 14px;">Harness 100% local AI power with zero cloud leaks.</p>
    </div>
    """, unsafe_allow_html=True)

    # Action Grid
    col1, col2 = st.columns(2)
    with col1:
        if st.button('✏️ Forge New Bot', key='forge_btn', use_container_width=True):
            st.session_state.nav = 'create'
            st.rerun()
    with col2:
        if st.button('💬 Open Live Chat', key='chat_btn', use_container_width=True):
            if bots:
                st.session_state.active_bot_id = bots[0]['id']
                st.session_state.nav = 'chat'
                st.rerun()
            else:
                st.warning('Create a bot first!')

    st.markdown('### Active Bots & History')

    if not bots:
        st.info('No bots created yet. Click **Forge New Bot** above to create your first assistant!')
    else:
        for b in bots:
            docs_badge = '📄 RAG Active' if b['has_docs'] else '⚡ Standard'
            if st.button(f"💬 {b['name']}  |  {docs_badge}  →", key=f"bot_{b['id']}", use_container_width=True):
                st.session_state.active_bot_id = b['id']
                st.session_state.nav = 'chat'
                st.rerun()

    st.markdown('---')
    b1, b2, b3, b4 = st.columns(4)
    with b1:
        if st.button('🏠 Home', key='nav_home', use_container_width=True):
            pass
    with b2:
        if st.button('💬 Chats', key='nav_chats', use_container_width=True):
            if bots:
                st.session_state.active_bot_id = bots[0]['id']
                st.session_state.nav = 'chat'
                st.rerun()
    with b3:
        if st.button('🛠️ Forge', key='nav_forge', use_container_width=True):
            st.session_state.nav = 'create'
            st.rerun()
    with b4:
        if st.button('🔌 Host', key='nav_host', use_container_width=True):
            st.session_state.nav = 'settings'
            st.rerun()

# ── NAVIGATION: CREATE BOT SCREEN ─────────────────────────────────────────────
elif st.session_state.nav == 'create':
    if st.button('← Back to Home', key='back_home_create'):
        st.session_state.nav = 'home'
        st.rerun()

    st.markdown('## ✏️ Forge Custom AI Bot')
    st.markdown('Describe your bot in plain English. Our Meta-LLM will build the system prompt automatically.')

    with st.form('create_form'):
        name = st.text_input('Bot Name', placeholder='e.g. Legal Contract Advisor')
        persona = st.text_area('Persona / Role Description', placeholder='e.g. Expert contract reviewer who spots risk clauses...')

        c1, c2 = st.columns(2)
        with c1:
            tone = st.selectbox('Tone', ['Professional', 'Friendly', 'Concise', 'Formal', 'Direct'])
            language = st.selectbox('Language', ['English', 'Hindi', 'Spanish', 'French'])
        with c2:
            length = st.selectbox('Response Length', ['Short', 'Medium', 'Detailed'])
            guardrails = st.text_input('Guardrails', placeholder='e.g. Never give definitive legal advice')

        domain = st.text_input('Domain Knowledge', placeholder='e.g. Employment contracts, NDAs')
        uploaded_file = st.file_uploader('Upload Private Knowledge Base (PDF)', type=['pdf'])
        url_input = st.text_input('Or Ingest Website URL', placeholder='https://example.com/policy')

        submitted = st.form_submit_button('✨ Forge & Save Bot')

        if submitted:
            if not name or not persona:
                st.error('Please enter a Name and Persona.')
            else:
                with st.spinner('⚡ Meta-LLM generating engineered system prompt...'):
                    try:
                        data = {
                            'name': name, 'persona': persona, 'tone': tone,
                            'language': language, 'length': length,
                            'guardrails': guardrails, 'domain': domain, 'url': url_input,
                        }
                        files = {}
                        if uploaded_file is not None:
                            files['file'] = (uploaded_file.name, uploaded_file.getvalue(), 'application/pdf')

                        res = requests.post(f'{BASE_URL}/create-bot', data=data, files=files if files else None, timeout=120)
                        if res.status_code == 200:
                            b_data = res.json()
                            st.success(f'Successfully forged bot: {name}!')
                            st.session_state.active_bot_id = b_data['bot_id']
                            st.session_state.nav = 'chat'
                            st.rerun()
                        else:
                            st.error(f'Error: {res.text}')
                    except Exception as e:
                        st.error(f'Connection failed: {e}')

# ── NAVIGATION: CHAT SCREEN ───────────────────────────────────────────────────
elif st.session_state.nav == 'chat':
    if st.button('← Back to Home', key='back_home_chat'):
        st.session_state.nav = 'home'
        st.rerun()

    active_bot = next((b for b in bots if b['id'] == st.session_state.active_bot_id), None)
    if not active_bot and bots:
        active_bot = bots[0]
        st.session_state.active_bot_id = active_bot['id']

    if not active_bot:
        st.warning('No bots available.')
        if st.button('Create Bot', key='create_bot_fallback'):
            st.session_state.nav = 'create'
            st.rerun()
    else:
        st.markdown(f"### 💬 Chat with {active_bot['name']}")
        if active_bot['has_docs']:
            st.caption('📄 RAG Knowledge Base Connected')

        bot_id = active_bot['id']
        if bot_id not in st.session_state.chat_histories:
            st.session_state.chat_histories[bot_id] = []

        history = st.session_state.chat_histories[bot_id]

        for msg in history:
            with st.chat_message(msg['role']):
                st.markdown(msg['content'])

        if user_msg := st.chat_input('Type your message...'):
            history.append({'role': 'user', 'content': user_msg})
            with st.chat_message('user'):
                st.markdown(user_msg)

            with st.chat_message('assistant'):
                placeholder = st.empty()
                full_reply = ''
                try:
                    api_hist = [{'role': m['role'], 'content': m['content']} for m in history[:-1]]
                    payload = {'message': user_msg, 'history': api_hist}
                    with requests.post(f'{BASE_URL}/chat/{bot_id}', json=payload, stream=True, timeout=120) as r:
                        for chunk in r.iter_content(chunk_size=None, decode_unicode=True):
                            if chunk:
                                full_reply += chunk
                                placeholder.markdown(full_reply + '▌')
                    placeholder.markdown(full_reply)
                except Exception as e:
                    full_reply = f'[Error: {e}]'
                    placeholder.markdown(full_reply)

            history.append({'role': 'assistant', 'content': full_reply})

# ── NAVIGATION: SETTINGS SCREEN ───────────────────────────────────────────────
elif st.session_state.nav == 'settings':
    if st.button('← Back to Home', key='back_home_settings'):
        st.session_state.nav = 'home'
        st.rerun()

    st.markdown('### ⚙️ Host & Connection Settings')
    with st.form('settings_form'):
        new_ip = st.text_input('Host IP Address', value=host_ip)
        new_port = st.text_input('Port Number', value=host_port)
        saved = st.form_submit_button('Save Settings')
        if saved:
            os.environ['HOST_IP'] = new_ip
            os.environ['HOST_PORT'] = new_port
            st.success('Settings updated!')
            st.session_state.nav = 'home'
            st.rerun()
