"""
overlay.py — BotForge Overlay Mode
An always-on-top floating window that hovers over any application.
Press the hotkey to capture the screen, ask a question, get an answer.

Usage:
    python overlay/overlay.py --host 192.168.x.x --port 8000
"""

import sys
import os
import base64
import argparse
import threading
import requests
import tkinter as tk
from tkinter import scrolledtext
from io import BytesIO
import mss
from PIL import Image

# ── Config ────────────────────────────────────────────────────────────────────
HOTKEY       = '<Control-space>'
BG_COLOR     = '#0d0d0d'
ACCENT_COLOR = '#00e5ff'
TEXT_COLOR   = '#ffffff'
DIM_COLOR    = '#888888'
FONT_MAIN    = ('Segoe UI', 11)
FONT_SMALL   = ('Segoe UI', 9)
FONT_TITLE   = ('Segoe UI', 12, 'bold')
WINDOW_W     = 420
WINDOW_H     = 560


# ── Overlay Window ────────────────────────────────────────────────────────────

class BotForgeOverlay:
    def __init__(self, host: str, port: str):
        self.host    = host
        self.port    = port
        self.api_url = f'http://{host}:{port}/overlay'
        self.last_screenshot = None

        self.root = tk.Tk()
        self.root.title('BotForge Overlay')
        self.root.geometry(f'{WINDOW_W}x{WINDOW_H}+40+40')
        self.root.configure(bg=BG_COLOR)
        self.root.attributes('-topmost', True)       # always on top
        self.root.attributes('-alpha', 0.95)         # slight transparency
        self.root.resizable(True, True)

        self._build_ui()
        self._bind_hotkey()

        self.root.mainloop()

    def _build_ui(self):
        # ── Title bar ─────────────────────────────────
        title_frame = tk.Frame(self.root, bg=BG_COLOR)
        title_frame.pack(fill='x', padx=10, pady=(10, 0))

        tk.Label(
            title_frame, text='⚡ BotForge', font=FONT_TITLE,
            fg=ACCENT_COLOR, bg=BG_COLOR
        ).pack(side='left')

        tk.Label(
            title_frame, text='OVERLAY', font=FONT_SMALL,
            fg=DIM_COLOR, bg=BG_COLOR
        ).pack(side='left', padx=6)

        tk.Button(
            title_frame, text='✕', font=FONT_SMALL,
            fg=DIM_COLOR, bg=BG_COLOR, bd=0,
            command=self.root.destroy
        ).pack(side='right')

        # ── Divider ───────────────────────────────────
        tk.Frame(self.root, bg=ACCENT_COLOR, height=1).pack(fill='x', padx=10, pady=6)

        # ── Status ────────────────────────────────────
        self.status_var = tk.StringVar(value=f'Connected to {self.host}:{self.port}')
        tk.Label(
            self.root, textvariable=self.status_var,
            font=FONT_SMALL, fg=DIM_COLOR, bg=BG_COLOR
        ).pack(anchor='w', padx=12)

        # ── Hotkey hint ───────────────────────────────
        tk.Label(
            self.root,
            text='Ctrl+Space → capture screen & ask',
            font=FONT_SMALL, fg='#444', bg=BG_COLOR
        ).pack(anchor='w', padx=12, pady=(2, 8))

        # ── Chat display ──────────────────────────────
        self.chat_display = scrolledtext.ScrolledText(
            self.root, font=FONT_MAIN,
            bg='#111', fg=TEXT_COLOR,
            insertbackground=TEXT_COLOR,
            wrap='word', state='disabled',
            relief='flat', bd=0,
        )
        self.chat_display.pack(fill='both', expand=True, padx=10, pady=4)

        self.chat_display.tag_config('you',    foreground=ACCENT_COLOR, font=('Segoe UI', 11, 'bold'))
        self.chat_display.tag_config('bot',    foreground=TEXT_COLOR)
        self.chat_display.tag_config('system', foreground=DIM_COLOR, font=FONT_SMALL)

        # ── Input row ─────────────────────────────────
        input_frame = tk.Frame(self.root, bg=BG_COLOR)
        input_frame.pack(fill='x', padx=10, pady=(4, 10))

        self.input_var = tk.StringVar()
        entry = tk.Entry(
            input_frame, textvariable=self.input_var,
            font=FONT_MAIN, bg='#1a1a1a', fg=TEXT_COLOR,
            insertbackground=TEXT_COLOR, relief='flat', bd=4,
        )
        entry.pack(side='left', fill='x', expand=True, ipady=6)
        entry.bind('<Return>', self._on_send)
        entry.focus()

        tk.Button(
            input_frame, text='Ask',
            font=FONT_SMALL, bg=ACCENT_COLOR, fg='#000',
            relief='flat', padx=10,
            command=self._on_send
        ).pack(side='right', padx=(6, 0))

        tk.Button(
            input_frame, text='📷',
            font=FONT_SMALL, bg='#1a1a1a', fg=ACCENT_COLOR,
            relief='flat', padx=8,
            command=self._capture_and_ask
        ).pack(side='right', padx=(4, 0))

    def _bind_hotkey(self):
        self.root.bind(HOTKEY, lambda e: self._capture_and_ask())

    # ── Chat helpers ──────────────────────────────────────────────────────────

    def _append(self, text: str, tag: str = 'bot'):
        self.chat_display.config(state='normal')
        self.chat_display.insert('end', text, tag)
        self.chat_display.see('end')
        self.chat_display.config(state='disabled')

    def _set_status(self, text: str):
        self.status_var.set(text)
        self.root.update_idletasks()

    # ── Capture & Ask ─────────────────────────────────────────────────────────

    def _capture_and_ask(self):
        question = self.input_var.get().strip() or 'What is on this screen? Explain it clearly and concisely.'
        self.input_var.set('')
        threading.Thread(target=self._run_vision, args=(question,), daemon=True).start()

    def _on_send(self, event=None):
        question = self.input_var.get().strip()
        if not question:
            return
        self.input_var.set('')
        threading.Thread(target=self._run_vision, args=(question,), daemon=True).start()

    def _run_vision(self, question: str):
        self._set_status('📷 Capturing screen...')

        # Minimise overlay so it doesn't appear in screenshot
        self.root.iconify()
        self.root.after(300, lambda: None)

        try:
            screenshot_b64 = self._take_screenshot()
        except Exception as e:
            self.root.deiconify()
            self._append(f'\n[Error capturing screen: {e}]\n', 'system')
            self._set_status('Ready')
            return

        self.root.deiconify()

        self._append(f'\nYou: {question}\n', 'you')
        self._set_status('🤖 Thinking...')

        try:
            r = requests.post(
                self.api_url,
                json={'image': screenshot_b64, 'question': question},
                timeout=120,
            )
            r.raise_for_status()
            answer = r.json().get('answer', '(no response)')
        except Exception as e:
            answer = f'[Error: {e}]'

        self._append(f'BotForge: {answer}\n\n', 'bot')
        self._set_status(f'Connected to {self.host}:{self.port}')

    def _take_screenshot(self) -> str:
        with mss.mss() as sct:
            monitor = sct.monitors[0]
            img = sct.grab(monitor)
            pil_img = Image.frombytes('RGB', img.size, img.bgra, 'raw', 'BGRX')

        # Resize to 1280x720 to keep payload small
        pil_img = pil_img.resize((1280, 720), Image.LANCZOS)

        buffer = BytesIO()
        pil_img.save(buffer, format='JPEG', quality=75)
        return base64.b64encode(buffer.getvalue()).decode()


# ── Entry Point ───────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description='BotForge Overlay')
    parser.add_argument('--host', default=os.getenv('HOST_IP', 'localhost'))
    parser.add_argument('--port', default=os.getenv('HOST_PORT', '8000'))
    args = parser.parse_args()

    print(f'[BotForge Overlay] Connecting to {args.host}:{args.port}')
    print(f'[BotForge Overlay] Hotkey: Ctrl+Space to capture & ask\n')

    BotForgeOverlay(args.host, args.port)


if __name__ == '__main__':
    main()
