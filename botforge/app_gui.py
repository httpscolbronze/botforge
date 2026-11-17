"""
app_gui.py — BotForge Streamlit GUI Client
A gorgeous, modern web dashboard for BotForge.
Includes: Host connection, Bot Creator form with PDF upload, and Live Streaming Chat.

Usage:
    streamlit run app_gui.py
"""

import os
import requests
import streamlit as st

# ── Page Config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title='BotForge — No-Code AI Builder',
    page_icon='⚡',
    layout='wide',
    initial_sidebar_state='expanded',
)

# ── Custom Dark Cyberpunk Styling ─────────────────────────────────────────────
st.markdown("""
<style>
    .stApp {
        background-color: #0d0d0d;
        color: #ffffff;
    }
    sidebar .stSidebar {
        background-color: #111111;
    }
    .stTextInput input, .stTextArea textarea, .stSelectbox select {
        background-color: #1a1a1a !important;
        color: #ffffff !important;
        border: 1px solid #333333 !important;
        border-radius: 6px !important;
    }
    .stButton button {
        background-color: #00e5ff !important;
        color: #000000 !important;
        font-weight: bold !important;
        border-radius: 6px !important;
        border: none !important;
        transition: 0.2s;
    }
    .stButton button:hover {
        background-color: #00b3cc !important;
        color: #000000 !important;
    }
    h1, h2, h3 {
        color: #00e5ff !important;
    }
    .stAlert {
        background-color: #1a1a1a;
        color: #00e5ff;
        border: 1px solid #00e5ff;
    }
</style>
""", unsafe_allow_html=True)

# ── Sidebar: Connection Settings ──────────────────────────────────────────────
st.sidebar.title('⚡ BotForge Control')
st.sidebar.markdown('---')

host_ip = st.sidebar.text_input('Host IP', value='localhost')
host_port = st.sidebar.text_input('Port', value='8000')
BASE_URL = f'http://{host_ip}:{host_port}'

# Health check connection status
try:
    r = requests.get(f'{BASE_URL}/', timeout=2)
    if r.status_code == 200:
        st.sidebar.success('🟢 Connected to Host')
    else:
        st.sidebar.error('🔴 Host responded with error')
except Exception:
    st.sidebar.error('🔴 Disconnected (Check host.py)')

st.sidebar.markdown('---')
st.sidebar.info('**BotForge v1.0**\n\nNo-code AI chatbot builder with private LAN mode & RAG pipeline.')

# ── Main Header ───────────────────────────────────────────────────────────────
st.title('⚡ BotForge Dashboard')
st.markdown('*Build, deploy, and chat with custom AI bots in seconds — zero coding required.*')

# Fetch existing bots
try:
    bots_res = requests.get(f'{BASE_URL}/bots', timeout=3)
    bots_list = bots_res.json() if bots_res.status_code == 200 else []
except Exception:
    bots_list = []

# ── Tabs Navigation ───────────────────────────────────────────────────────────
tab_create, tab_chat, tab_info = st.tabs(['🛠️ Forge a Bot', '💬 Live Chat', '📊 System Info'])

# ──────────────────────────────────────────────────────────────────────────────
# TAB 1: FORGE A BOT
# ──────────────────────────────────────────────────────────────────────────────
with tab_create:
    st.subheader('Create a New Custom Chatbot')
    st.markdown('Fill out the form below. Our Meta-LLM will automatically write an engineered system prompt for your bot.')

    with st.form('bot_forge_form'):
        col1, col2 = st.columns(2)

        with col1:
            bot_name = st.text_input('Bot Name', placeholder='e.g. Pizza Support Bot')
            persona = st.text_area('Persona / Description', placeholder='e.g. Friendly and helpful customer support agent for an Italian pizzeria.')
            tone = st.selectbox('Tone', ['Friendly', 'Professional', 'Casual', 'Formal', 'Socratic', 'Sarcastic'])
            language = st.selectbox('Language', ['English', 'Hindi', 'Spanish', 'French', 'Auto-detect'])

        with col2:
            length = st.selectbox('Response Length', ['Short', 'Medium', 'Detailed'])
            guardrails = st.text_input('Guardrails / Rules', placeholder='e.g. Never mention competitors. Always suggest calling us.')
            domain = st.text_input('Domain / Extra Context', placeholder='e.g. Menu items, store timings, pricing')
            uploaded_file = st.file_uploader('Upload Knowledge Base (PDF)', type=['pdf'])
            url_input = st.text_input('Or Ingest Website URL', placeholder='https://example.com/faq')

        submitted = st.form_submit_button('🚀 Forge Bot Now')

        if submitted:
            if not bot_name or not persona:
                st.error('Please provide at least a Bot Name and Persona.')
            else:
                with st.spinner('⚡ Meta-LLM crafting system prompt & indexing knowledge base...'):
                    try:
                        data = {
                            'name': bot_name,
                            'persona': persona,
                            'tone': tone,
                            'language': language,
                            'length': length,
                            'guardrails': guardrails,
                            'domain': domain,
                            'url': url_input,
                        }
                        files = {}
                        if uploaded_file is not None:
                            files['file'] = (uploaded_file.name, uploaded_file.getvalue(), 'application/pdf')

                        res = requests.post(f'{BASE_URL}/create-bot', data=data, files=files if files else None, timeout=120)

                        if res.status_code == 200:
                            res_data = res.json()
                            st.success(f'✨ Bot "{bot_name}" successfully forged!')
                            st.markdown(f'**Bot ID:** `{res_data["bot_id"]}`')
                            st.markdown(f'**Shareable Link:** `{res_data["share_url"]}`')
                            with st.expander('🔍 View Generated System Prompt'):
                                st.code(res_data['system_prompt'], language='markdown')
                            st.balloons()
                        else:
                            st.error(f'Failed to create bot: {res.text}')
                    except Exception as e:
                        st.error(f'Connection error: {e}')

# ──────────────────────────────────────────────────────────────────────────────
# TAB 2: LIVE CHAT
# ──────────────────────────────────────────────────────────────────────────────
with tab_chat:
    if not bots_list:
        st.warning('No bots found. Create one in the **Forge a Bot** tab first!')
    else:
        # Bot selector
        bot_options = {f'{b["name"]} (ID: {b["id"]})': b['id'] for b in bots_list}
        selected_label = st.selectbox('Select Bot to Chat With', list(bot_options.keys()))
        current_bot_id = bot_options[selected_label]

        # Fetch full bot details
        try:
            bot_detail_res = requests.get(f'{BASE_URL}/bot/{current_bot_id}', timeout=3)
            bot_detail = bot_detail_res.json() if bot_detail_res.status_code == 200 else {}
        except Exception:
            bot_detail = {}

        if bot_detail:
            st.markdown(f'### Chatting with: `{bot_detail["name"]}`')
            if bot_detail.get('has_docs'):
                st.caption('📄 Knowledge base active (RAG enabled)')

            # Initialize chat history in session state
            if 'chat_history' not in st.session_state:
                st.session_state.chat_history = {}

            if current_bot_id not in st.session_state.chat_history:
                st.session_state.chat_history[current_bot_id] = []

            history = st.session_state.chat_history[current_bot_id]

            # Display chat messages
            for message in history:
                with st.chat_message(message['role']):
                    st.markdown(message['content'])

            # Chat input
            if user_prompt := st.chat_input('Type your message...'):
                # Append user message
                history.append({'role': 'user', 'content': user_prompt})
                with st.chat_message('user'):
                    st.markdown(user_prompt)

                # Stream assistant response
                with st.chat_message('assistant'):
                    message_placeholder = st.empty()
                    full_response = ''

                    try:
                        # Prepare history format for API
                        api_history = [{'role': m['role'], 'content': m['content']} for m in history[:-1]]
                        payload = {'message': user_prompt, 'history': api_history}

                        with requests.post(f'{BASE_URL}/chat/{current_bot_id}', json=payload, stream=True, timeout=120) as r:
                            for chunk in r.iter_content(chunk_size=None, decode_unicode=True):
                                if chunk:
                                    full_response += chunk
                                    message_placeholder.markdown(full_response + '▌')
                        message_placeholder.markdown(full_response)
                    except Exception as e:
                        full_response = f'[Error connecting to model: {e}]'
                        message_placeholder.markdown(full_response)

                history.append({'role': 'assistant', 'content': full_response})

# ──────────────────────────────────────────────────────────────────────────────
# TAB 3: SYSTEM INFO
# ──────────────────────────────────────────────────────────────────────────────
with tab_info:
    st.subheader('System Architecture & Status')
    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric('Active Bots', len(bots_list))
    with col2:
        st.metric('Host Status', 'Online' if st.sidebar.status else 'Offline')
    with col3:
        st.metric('Backend Engine', 'FastAPI + Ollama')

    st.markdown('---')
    st.markdown('### How to launch local services')
    st.code("""
# 1. Start Ollama
ollama serve

# 2. Start BotForge Host Server
python host.py

# 3. Run this Streamlit GUI Dashboard
streamlit run app_gui.py
    """, language='bash')
