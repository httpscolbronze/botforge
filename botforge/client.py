"""
client.py — BotForge Client Mode
Connect to any BotForge host on your LAN.
Provides a terminal chat UI + launches the overlay.

Usage:
    python client.py
"""

import os
import sys
import json
import threading
import requests
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

DEFAULT_HOST = os.getenv('HOST_IP', 'localhost')
DEFAULT_PORT = os.getenv('HOST_PORT', '8000')


# ── Helpers ───────────────────────────────────────────────────────────────────

def base_url(host: str, port: str) -> str:
    return f'http://{host}:{port}'


def check_connection(host: str, port: str) -> bool:
    try:
        r = requests.get(f'{base_url(host, port)}/', timeout=5)
        return r.status_code == 200
    except Exception:
        return False


def list_bots(host: str, port: str) -> list:
    try:
        r = requests.get(f'{base_url(host, port)}/bots', timeout=5)
        return r.json()
    except Exception:
        return []


def stream_chat(host: str, port: str, bot_id: str, message: str, history: list):
    url = f'{base_url(host, port)}/chat/{bot_id}'
    payload = {'message': message, 'history': history}
    with requests.post(url, json=payload, stream=True, timeout=120) as r:
        r.raise_for_status()
        full_response = ''
        for chunk in r.iter_content(chunk_size=None, decode_unicode=True):
            if chunk:
                print(chunk, end='', flush=True)
                full_response += chunk
        print()
        return full_response


def create_bot_interactive(host: str, port: str) -> str:
    print('\n── Create a New Bot ──────────────────────')
    name       = input('Bot name:                ').strip() or 'My Bot'
    persona    = input('Persona (describe it):   ').strip() or 'A helpful assistant'
    tone       = input('Tone [Friendly]:         ').strip() or 'Friendly'
    language   = input('Language [English]:      ').strip() or 'English'
    length     = input('Response length [Medium]:').strip() or 'Medium'
    guardrails = input('Guardrails (or leave blank): ').strip()
    domain     = input('Domain / extra context:  ').strip()
    doc_path   = input('PDF path (or leave blank):   ').strip()
    url        = input('URL to ingest (or blank):    ').strip()

    print('\n[BotForge] Generating your bot...')

    data = {
        'name': name, 'persona': persona, 'tone': tone,
        'language': language, 'length': length,
        'guardrails': guardrails, 'domain': domain, 'url': url,
    }
    files = {}
    if doc_path and Path(doc_path).exists():
        files['file'] = open(doc_path, 'rb')

    r = requests.post(f'{base_url(host, port)}/create-bot', data=data, files=files or None, timeout=120)
    r.raise_for_status()
    result = r.json()

    print(f'\n✅ Bot created!')
    print(f'   ID:     {result["bot_id"]}')
    print(f'   Name:   {result["name"]}')
    print(f'   Docs:   {"Yes" if result["has_docs"] else "No"}')
    print(f'\n   Generated system prompt:')
    print(f'   {result["system_prompt"][:200]}...\n')

    return result['bot_id']


# ── Chat Loop ─────────────────────────────────────────────────────────────────

def chat_loop(host: str, port: str, bot_id: str, bot_name: str):
    history = []
    print(f'\n── Chatting with [{bot_name}] ─────────────────')
    print('   Type your message. /quit to exit. /overlay to launch overlay.\n')

    while True:
        try:
            user_input = input('You: ').strip()
        except (KeyboardInterrupt, EOFError):
            break

        if not user_input:
            continue
        if user_input.lower() in ('/quit', '/exit', '/q'):
            break
        if user_input.lower() == '/overlay':
            print('[BotForge] Launching overlay...')
            threading.Thread(
                target=launch_overlay, args=(host, port), daemon=True
            ).start()
            continue

        print(f'\n{bot_name}: ', end='')
        response = stream_chat(host, port, bot_id, user_input, history)
        history.append({'role': 'user',      'content': user_input})
        history.append({'role': 'assistant', 'content': response})
        print()


# ── Overlay launcher ──────────────────────────────────────────────────────────

def launch_overlay(host: str, port: str):
    overlay_path = Path(__file__).parent / 'overlay' / 'overlay.py'
    os.system(f'python "{overlay_path}" --host {host} --port {port}')


# ── Main Menu ─────────────────────────────────────────────────────────────────

def main():
    print('╔══════════════════════════════════════╗')
    print('║        BotForge — CLIENT MODE        ║')
    print('╚══════════════════════════════════════╝\n')

    host = input(f'Host IP [{DEFAULT_HOST}]: ').strip() or DEFAULT_HOST
    port = input(f'Port    [{DEFAULT_PORT}]: ').strip() or DEFAULT_PORT

    print(f'\nConnecting to {host}:{port}...')
    if not check_connection(host, port):
        print('❌ Could not connect. Make sure host.py is running on that machine.')
        sys.exit(1)
    print('✅ Connected!\n')

    while True:
        print('── Main Menu ─────────────────────────────')
        print('  1. Create a new bot')
        print('  2. Use an existing bot')
        print('  3. Launch overlay mode')
        print('  4. Quit')
        choice = input('\nChoice: ').strip()

        if choice == '1':
            bot_id = create_bot_interactive(host, port)
            bots = list_bots(host, port)
            bot_name = next((b['name'] for b in bots if b['id'] == bot_id), 'Bot')
            chat_loop(host, port, bot_id, bot_name)

        elif choice == '2':
            bots = list_bots(host, port)
            if not bots:
                print('\nNo bots yet. Create one first.\n')
                continue
            print('\n── Available Bots ────────────────────────')
            for i, b in enumerate(bots):
                docs = '📄' if b['has_docs'] else '  '
                print(f'  {i+1}. {docs} [{b["id"]}] {b["name"]}')
            idx = input('\nSelect bot number: ').strip()
            try:
                bot = bots[int(idx) - 1]
                chat_loop(host, port, bot['id'], bot['name'])
            except (ValueError, IndexError):
                print('Invalid selection.\n')

        elif choice == '3':
            print('[BotForge] Launching overlay...')
            launch_overlay(host, port)

        elif choice == '4':
            print('Goodbye!')
            break


if __name__ == '__main__':
    main()
