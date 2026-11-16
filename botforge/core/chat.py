"""
chat.py — Chat engine for BotForge.
Assembles the final prompt and streams response from Ollama or Groq.
"""

import os
import json
import requests
from dotenv import load_dotenv
from core.rag import retrieve, has_docs

load_dotenv()

OLLAMA_HOST  = os.getenv('OLLAMA_HOST', 'http://localhost:11434')
CHAT_MODEL   = os.getenv('CHAT_MODEL',  'llama3.2')
MODE         = os.getenv('MODE',        'private')
GROQ_API_KEY = os.getenv('GROQ_API_KEY', '')


def build_messages(system_prompt: str, bot_id: str, history: list, user_message: str) -> list:
    """Assemble messages: system prompt + RAG context + history + user message."""
    messages = []

    # Inject retrieved doc chunks if bot has docs
    context = ''
    if has_docs(bot_id):
        context = retrieve(user_message, bot_id)

    full_system = system_prompt
    if context:
        full_system += f'\n\n--- RELEVANT KNOWLEDGE ---\n{context}\n--- END KNOWLEDGE ---'

    messages.append({'role': 'system', 'content': full_system})

    # Last 6 messages of history for context window efficiency
    for msg in history[-6:]:
        messages.append(msg)

    messages.append({'role': 'user', 'content': user_message})
    return messages


def stream_chat(system_prompt: str, bot_id: str, history: list, user_message: str):
    """Generator that yields response tokens one by one."""
    messages = build_messages(system_prompt, bot_id, history, user_message)

    if MODE == 'speed' and GROQ_API_KEY:
        yield from _stream_groq(messages)
    else:
        yield from _stream_ollama(messages)


def _stream_ollama(messages: list):
    payload = {
        'model':    CHAT_MODEL,
        'messages': messages,
        'stream':   True,
    }
    with requests.post(f'{OLLAMA_HOST}/api/chat', json=payload, stream=True, timeout=120) as r:
        r.raise_for_status()
        for line in r.iter_lines():
            if line:
                data = json.loads(line)
                token = data.get('message', {}).get('content', '')
                if token:
                    yield token
                if data.get('done'):
                    break


def _stream_groq(messages: list):
    from groq import Groq
    client = Groq(api_key=GROQ_API_KEY)
    stream = client.chat.completions.create(
        model='llama-3.3-70b-versatile',
        messages=messages,
        stream=True,
    )
    for chunk in stream:
        token = chunk.choices[0].delta.content
        if token:
            yield token


def chat_vision(image_b64: str, question: str) -> str:
    """
    Send a screenshot + question to LLaVA for overlay mode.
    Returns the full response (non-streaming for overlay simplicity).
    """
    payload = {
        'model':  os.getenv('VISION_MODEL', 'llava'),
        'prompt': question,
        'images': [image_b64],
        'stream': False,
    }
    r = requests.post(f'{OLLAMA_HOST}/api/generate', json=payload, timeout=120)
    r.raise_for_status()
    return r.json().get('response', '').strip()
