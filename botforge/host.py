"""
host.py — BotForge Host Mode
Run this on your strongest machine. Starts Ollama + FastAPI server on your LAN.
All clients connect to this machine's IP.

Usage:
    python host.py
"""

import os
import sys
import json
import base64
import asyncio
import tempfile
import subprocess
import requests
from pathlib import Path
from dotenv import load_dotenv

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse, HTMLResponse
import aiofiles
import uvicorn

load_dotenv()

# ── Bootstrap ─────────────────────────────────────────────────────────────────
sys.path.insert(0, str(Path(__file__).parent))
from core.db       import init_db, create_bot, get_bot, update_bot, list_bots
from core.meta_llm import generate_system_prompt
from core.rag      import ingest_pdf, ingest_url, has_docs
from core.chat     import stream_chat, chat_vision

app = FastAPI(title='BotForge Host', version='1.0')

app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_methods=['*'],
    allow_headers=['*'],
)

HOST_PORT = int(os.getenv('HOST_PORT', 8000))


# ── Startup ───────────────────────────────────────────────────────────────────
@app.on_event('startup')
async def startup():
    init_db()
    print('\n🔥 BotForge Host is running!')
    print(f'   Local:   http://localhost:{HOST_PORT}')
    _show_lan_ip()
    print('   Clients: enter your IP above in client.py\n')


def _show_lan_ip():
    import socket
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
        s.close()
        print(f'   LAN:     http://{ip}:{HOST_PORT}  ← share this with clients')
    except Exception:
        print('   LAN:     (could not detect IP)')


# ── System Status & Active Models ──────────────────────────────────────────
@app.get('/status')
async def system_status():
    ollama_host = os.getenv('OLLAMA_HOST', 'http://localhost:11434').rstrip('/')
    chat_model = os.getenv('CHAT_MODEL', 'gemma3:1b')
    vision_model = os.getenv('VISION_MODEL', 'llava:7b')

    models = []
    try:
        r = requests.get(f'{ollama_host}/api/tags', timeout=2)
        if r.status_code == 200:
            models = [m.get('name') for m in r.json().get('models', [])]
    except Exception:
        pass

    return {
        'status': 'online',
        'chat_model': chat_model,
        'vision_model': vision_model,
        'available_models': models
    }


# ── Web UI / Health ──────────────────────────────────────────────────────────
@app.get('/', response_class=HTMLResponse)
async def serve_ui():
    html_path = Path(__file__).parent / 'botforge.html'
    if html_path.exists():
        async with aiofiles.open(html_path, 'r', encoding='utf-8') as f:
            return await f.read()
    return {'status': 'BotForge Host is running', 'version': '1.0'}


# ── Bot Builder ───────────────────────────────────────────────────────────────
@app.post('/create-bot')
async def create_bot_endpoint(
    name:       str = Form(...),
    persona:    str = Form(...),
    tone:       str = Form('Friendly'),
    language:   str = Form('English'),
    length:     str = Form('Medium'),
    guardrails: str = Form(''),
    domain:     str = Form(''),
    file: UploadFile = File(None),
    url:        str = Form(''),
):
    config = {
        'name': name, 'persona': persona, 'tone': tone,
        'language': language, 'length': length,
        'guardrails': guardrails, 'domain': domain,
    }

    # Generate system prompt via Meta-LLM
    print(f'[Meta-LLM] Generating system prompt for "{name}"...')
    system_prompt = generate_system_prompt(config)
    print(f'[Meta-LLM] Done.')

    # Save bot to DB
    bot_id = create_bot(name, system_prompt, config)

    # Ingest document if provided
    has_document = False
    if file and file.filename:
        suffix = Path(file.filename).suffix
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(await file.read())
            tmp_path = tmp.name
        print(f'[RAG] Ingesting {file.filename}...')
        ingest_pdf(tmp_path, bot_id)
        os.unlink(tmp_path)
        update_bot(bot_id, {'has_docs': 1})
        has_document = True
        print(f'[RAG] Done.')

    elif url.strip():
        print(f'[RAG] Ingesting URL: {url}...')
        ingest_url(url.strip(), bot_id)
        update_bot(bot_id, {'has_docs': 1})
        has_document = True
        print(f'[RAG] Done.')

    return {
        'bot_id':        bot_id,
        'name':          name,
        'system_prompt': system_prompt,
        'has_docs':      has_document,
        'share_url':     f'http://localhost:{HOST_PORT}/chat/{bot_id}',
    }


@app.get('/bot/{bot_id}')
def get_bot_endpoint(bot_id: str):
    bot = get_bot(bot_id)
    if not bot:
        raise HTTPException(status_code=404, detail='Bot not found')
    return bot


@app.get('/bots')
def list_bots_endpoint():
    return list_bots()


@app.post('/update-bot/{bot_id}')
async def update_bot_endpoint(bot_id: str, body: dict):
    bot = get_bot(bot_id)
    if not bot:
        
        raise HTTPException(status_code=404, detail='Bot not found')
    # Regenerate system prompt if config changed
    if any(k in body for k in ['persona', 'tone', 'language', 'length', 'guardrails', 'domain']):
        config = {**bot['config'], **body}
        body['system_prompt'] = generate_system_prompt(config)
        body['config'] = config
    update_bot(bot_id, body)
    return {'status': 'updated', 'bot_id': bot_id}


# ── Chat ──────────────────────────────────────────────────────────────────────
@app.post('/chat/{bot_id}')
async def chat_endpoint(bot_id: str, body: dict):
    bot = get_bot(bot_id)
    if not bot:
        raise HTTPException(status_code=404, detail='Bot not found')

    user_message = body.get('message', '').strip()
    history      = body.get('history', [])

    if not user_message:
        raise HTTPException(status_code=400, detail='Message cannot be empty')

    def generate():
        for token in stream_chat(bot['system_prompt'], bot_id, history, user_message):
            yield token

    return StreamingResponse(generate(), media_type='text/plain')


# ── Overlay Vision ────────────────────────────────────────────────────────────
@app.post('/overlay')
async def overlay_endpoint(body: dict):
    """
    Called by the overlay client.
    Receives a base64 screenshot + question, returns LLaVA's answer.
    """
    image_b64 = body.get('image')
    question  = body.get('question', 'What is on this screen? Explain it clearly.')

    if not image_b64:
        raise HTTPException(status_code=400, detail='No image provided')

    answer = chat_vision(image_b64, question)
    return {'answer': answer}


# ── Entry Point ───────────────────────────────────────────────────────────────
if __name__ == '__main__':
    print('╔══════════════════════════════════════╗')
    print('║         BotForge — HOST MODE         ║')
    print('╚══════════════════════════════════════╝')
    uvicorn.run('host:app', host='0.0.0.0', port=HOST_PORT, reload=False)
