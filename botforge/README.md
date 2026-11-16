# BotForge 🔥

> **Build your own custom AI chatbot. No code. No cloud. No cost.**

BotForge is a no-code AI chatbot builder that runs 100% on your local network. Anyone — a teacher, shop owner, HR manager, or developer — can create a fully customized AI chatbot in under 2 minutes by describing what they want in plain English.

---

## ✨ Features

| Feature | Description |
|---|---|
| **Meta-LLM Layer** | Converts plain-English descriptions into precision-engineered system prompts automatically |
| **Host / Client Mode** | One server powers the whole office or classroom — clients connect with just an IP address |
| **100% Private LAN Mode** | Ollama runs locally, zero bytes leave your network, ever |
| **Screen Overlay Copilot** | Floating window over any app — hotkey captures screen, LLaVA reads it, answer appears |
| **Private RAG Pipeline** | Upload any PDF or URL, bot answers from your documents only |
| **Skills System** | Extend bots with web search, multilingual replies, lead capture and more |
| **Speed Mode** | Optional Groq API fallback for internet-connected setups |

---

## 🏗️ Architecture

```
HOST MACHINE
├── Ollama (llama3.2 + llava)
├── FastAPI server → LAN IP:8000
├── FAISS vector stores (per bot)
└── SQLite database

CLIENT MACHINE
├── client.py → connects via host IP
├── Bot Builder (create / tweak bots)
├── Chat Interface (streamed responses)
└── Overlay Mode (always-on-top window)
```

---

## 🚀 Quick Start

### 1. Clone & Install

```bash
git clone https://github.com/httpscolbronze/botforge.git
cd botforge
pip install -r requirements.txt
```

### 2. Install Ollama

```bash
# Linux / Mac
curl -fsSL https://ollama.ai/install.sh | sh

# Pull models
ollama pull llama3.2
ollama pull llava
```

### 3. Configure

```bash
cp .env.example .env
# Edit .env — set HOST_IP, HOST_PORT, MODE
```

### 4. Start Host (on your server machine)

```bash
python host.py
```

You'll see your LAN IP printed — share it with clients.

### 5. Connect as Client (on any machine on the same network)

```bash
python client.py
# Enter the host IP when prompted
```

### 6. Launch Overlay (from client menu or directly)

```bash
python overlay/overlay.py --host 192.168.x.x --port 8000
# Press Ctrl+Space over any app to capture screen and ask a question
```

---

## 🗂️ Project Structure

```
botforge/
├── host.py              ← Run on the server machine
├── client.py            ← Run on any client machine
├── core/
│   ├── meta_llm.py      ← Converts form inputs → system prompt
│   ├── rag.py           ← PDF/URL → FAISS vector pipeline
│   ├── chat.py          ← Chat engine (Ollama / Groq)
│   └── db.py            ← SQLite bot storage
├── overlay/
│   └── overlay.py       ← Always-on-top screen overlay
├── requirements.txt
├── .env.example
└── README.md
```

---

## 🔧 Tech Stack

| Layer | Tool |
|---|---|
| LLM Runtime | Ollama (local) |
| Chat Model | llama3.2 / mistral |
| Vision Model | LLaVA (screen reading) |
| Backend | FastAPI + Uvicorn |
| RAG | FAISS + sentence-transformers |
| Overlay UI | Tkinter |
| Screenshots | mss + Pillow |
| Database | SQLite |
| Doc Parsing | PyMuPDF + BeautifulSoup |
| Speed Mode | Groq API (optional) |

---

## 🎯 Use Cases

- **Small Business** — Upload your menu/price list, get a customer support bot instantly
- **Education** — Upload syllabus, create a Socratic tutor that never gives direct answers
- **HR Teams** — Upload policy PDF, employees ask it questions 24/7
- **Developers** — Upload your docs, get a support bot with zero setup
- **Overlay** — Float BotForge over Excel, Word, PDFs — get AI assistance on anything

---

## 📊 Why BotForge?

- 82% of businesses haven't adopted AI — the last mile is broken *(Federal Reserve, 2026)*
- 78% of employees use unsanctioned AI tools at work *(Microsoft, 2026)*
- Chatbot market growing to $41.2B by 2033 *(Grand View Research)*
- BotForge is the first no-code builder with true data sovereignty

---

## 🏆 Built for HackForge 2K26

**Track:** AI & Machine Learning
**Team:** httpscolbronze

---

## 📄 License

MIT License — free to use, modify and distribute.
