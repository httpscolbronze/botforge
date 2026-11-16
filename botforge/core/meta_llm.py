"""
meta_llm.py — The Meta-LLM layer.
Converts plain-English user inputs from the Bot Builder form
into a precise, production-grade system prompt.
"""

import os
import requests
from dotenv import load_dotenv

load_dotenv()

OLLAMA_HOST  = os.getenv('OLLAMA_HOST', 'http://localhost:11434')
CHAT_MODEL   = os.getenv('CHAT_MODEL',  'llama3.2')
MODE         = os.getenv('MODE',        'private')
GROQ_API_KEY = os.getenv('GROQ_API_KEY', '')


META_INSTRUCTION = """You are a prompt engineering expert.
Your ONLY job is to convert the user's plain-English bot description into a precise system prompt.
Output ONLY the system prompt text — no explanation, no preamble, no quotes around it.
The system prompt must define: persona, tone, language, response style, domain expertise, and guardrails.
Make it specific, professional, and production-ready."""


def generate_system_prompt(config: dict) -> str:
    """
    config keys:
      name        - bot name
      persona     - plain English description e.g. "friendly customer support for a bakery"
      tone        - Formal / Friendly / Casual / Blunt
      language    - English / Hindi / Auto-detect
      length      - Short / Medium / Detailed
      guardrails  - e.g. "never mention competitors, always end with a CTA"
      domain      - optional extra context
    """
    user_input = f"""
Bot Name: {config.get('name', 'Assistant')}
Persona: {config.get('persona', 'A helpful AI assistant')}
Tone: {config.get('tone', 'Friendly')}
Language: {config.get('language', 'English')}
Response Length: {config.get('length', 'Medium')}
Guardrails: {config.get('guardrails', 'None')}
Domain / Extra Context: {config.get('domain', 'General purpose')}

Convert the above into a system prompt.
"""

    if MODE == 'speed' and GROQ_API_KEY:
        return _groq_generate(user_input)
    return _ollama_generate(user_input)


def _ollama_generate(user_input: str) -> str:
    payload = {
        'model': CHAT_MODEL,
        'messages': [
            {'role': 'system', 'content': META_INSTRUCTION},
            {'role': 'user',   'content': user_input},
        ],
        'stream': False,
    }
    r = requests.post(f'{OLLAMA_HOST}/api/chat', json=payload, timeout=60)
    r.raise_for_status()
    return r.json()['message']['content'].strip()


def _groq_generate(user_input: str) -> str:
    from groq import Groq
    client = Groq(api_key=GROQ_API_KEY)
    response = client.chat.completions.create(
        model='llama-3.3-70b-versatile',
        messages=[
            {'role': 'system', 'content': META_INSTRUCTION},
            {'role': 'user',   'content': user_input},
        ],
    )
    return response.choices[0].message.content.strip()
