"""
overlay.py — BotForge Overlay Mode
A floating window that hovers over any application.
Takes a snapshot of the screen, sends it to LLaVA, and displays the analysis.
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
BG_COLOR     = '#0b0b0f'
ACCENT_COLOR = '#00e5ff'
TEXT_COLOR   = '#ffffff'
DIM_COLOR    = '#94a3b8'
FONT_MAIN    = ('Segoe UI', 10)
FONT_SMALL   = ('Segoe UI', 9)
FONT_TITLE   = ('Segoe UI', 11, 'bold')
WINDOW_W     = 440
WINDOW_H     = 520


class BotForgeOverlayApp:
    def __init__(self, host: str, port: str):
        self.host    = host
        self.port    = port
        self.api_url = f'http://{host}:{port}/overlay'

        self.root = tk.Tk()
        self.root.title('BotForge // Vision Copilot')
        self.root.geometry(f'{WINDOW_W}x{WINDOW_H}+50+50')
        self.root.configure(bg=BG_COLOR)
        self.root.attributes('-topmost', True)
        self.root.attributes('-alpha', 0.96)
        self.root.resizable(True, True)

        self._build_ui()
        self._bind_hotkey()

        self.root.mainloop()

    def _build_ui(self):
        # Title bar frame
        title_frame = tk.Frame(self.root, bg=BG_COLOR)
        title_frame.pack(fill='x', padx=12, pady=(12, 4))

        tk.Label(
            title_frame, text='⚡ BotForge Vision Copilot', font=FONT_TITLE,
            fg=ACCENT_COLOR, bg=BG_COLOR
        ).pack(side='left')

        tk.Button(
            title_frame, text='✕', font=FONT_SMALL,
            fg=DIM_COLOR, bg=BG_COLOR, bd=0, cursor='hand2',
            command=self.root.destroy
        ).pack(side='right')

        # Subtitle info
        sub_frame = tk.Frame(self.root, bg=BG_COLOR)
        sub_frame.pack(fill='x', padx=12, pady=(0, 8))

        self.status_label = tk.Label(
            sub_frame, text=f'Model: LLaVA 7B (Host: {self.host}:{self.port})',
            font=FONT_SMALL, fg=DIM_COLOR, bg=BG_COLOR
        )
        self.status_label.pack(side='left')

        # Divider
        tk.Frame(self.root, bg='#22222d', height=1).pack(fill='x', padx=12, pady=4)

        # Output Text Area
        self.output_box = scrolledtext.ScrolledText(
            self.root, font=FONT_MAIN,
            bg='#16161c', fg=TEXT_COLOR,
            insertbackground=TEXT_COLOR,
            wrap='word', state='normal',
            relief='flat', bd=0,
        )
        self.output_box.pack(fill='both', expand=True, padx=12, pady=8)

        self.output_box.insert('end', '🤖 BotForge Vision ready.\nClick "Take Snapshot & Analyze" or press Ctrl+Space to inspect your screen.\n\n(Note: Local CPU vision inference takes ~30-60s).\n\n')
        self.output_box.config(state='disabled')

        # Action Button Frame
        btn_frame = tk.Frame(self.root, bg=BG_COLOR)
        btn_frame.pack(fill='x', padx=12, pady=(4, 14))

        self.snapshot_btn = tk.Button(
            btn_frame, text='📸 Take Snapshot & Analyze',
            font=('Segoe UI', 10, 'bold'), bg='#00e5ff', fg='#000000',
            relief='flat', cursor='hand2', pady=8,
            command=self.trigger_snapshot
        )
        self.snapshot_btn.pack(fill='x')

    def _bind_hotkey(self):
        self.root.bind(HOTKEY, lambda e: self.trigger_snapshot())

    def _append_output(self, text: str):
        self.output_box.config(state='normal')
        self.output_box.insert('end', text + '\n\n')
        self.output_box.see('end')
        self.output_box.config(state='disabled')

    def trigger_snapshot(self):
        self.snapshot_btn.config(state='disabled', text='⏳ Capturing & Analyzing (CPU Inference)...')
        self.status_label.config(text='Status: Processing image...')
        threading.Thread(target=self._run_vision_pipeline, daemon=True).start()

    def _run_vision_pipeline(self):
        try:
            # 1. Minimize overlay so it doesn't photograph itself
            self.root.iconify()
            self.root.after(400)

            # 2. Capture screenshot via mss
            with mss.mss() as sct:
                monitor = sct.monitors[0]
                img = sct.grab(monitor)
                pil_img = Image.frombytes('RGB', img.size, img.bgra, 'raw', 'BGRX')

            # Resize to 1280x720 for faster transfer
            pil_img = pil_img.resize((1280, 720), Image.LANCZOS)
            buffer = BytesIO()
            pil_img.save(buffer, format='JPEG', quality=70)
            image_b64 = base64.b64encode(buffer.getvalue()).decode()

            self.root.deiconify()
            self._append_output('📸 Snapshot captured! Sending to LLaVA 7B...')

            # 3. Send to FastAPI host
            r = requests.post(
                self.api_url,
                json={'image': image_b64, 'question': 'Analyze what is visible on this screen and provide key insights.'},
                timeout=300
            )
            r.raise_for_status()
            answer = r.json().get('answer', '(No response)')

            self._append_output(f'💡 **Analysis Result:**\n{answer}')

        except Exception as e:
            self.root.deiconify()
            self._append_output(f'❌ **Error:** {str(e)}')

        finally:
            self.snapshot_btn.config(state='normal', text='📸 Take Snapshot & Analyze')
            self.status_label.config(text=f'Model: LLaVA 7B (Host: {self.host}:{self.port})')


def main():
    parser = argparse.ArgumentParser(description='BotForge Overlay')
    parser.add_argument('--host', default=os.getenv('HOST_IP', 'localhost'))
    parser.add_argument('--port', default=os.getenv('HOST_PORT', '8000'))
    args = parser.parse_args()

    BotForgeOverlayApp(args.host, args.port)


if __name__ == '__main__':
    main()
