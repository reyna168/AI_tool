"""Telegram Bot / Discord Webhook 推播（純文字分段，避免 Markdown 轉義失敗）。"""
import logging
import os

import requests

log = logging.getLogger("push")


def _chunks(text, limit):
    buf = ""
    for line in text.split("\n"):
        if len(buf) + len(line) + 1 > limit:
            yield buf
            buf = ""
        buf += line + "\n"
    if buf.strip():
        yield buf


def send(text):
    sent = []
    tok, chat = os.getenv("TELEGRAM_BOT_TOKEN"), os.getenv("TELEGRAM_CHAT_ID")
    if tok and chat:
        for part in _chunks(text, 3800):
            r = requests.post(f"https://api.telegram.org/bot{tok}/sendMessage",
                              json={"chat_id": chat, "text": part, "disable_web_page_preview": True}, timeout=20)
            r.raise_for_status()
        sent.append("telegram")
    hook = os.getenv("DISCORD_WEBHOOK_URL")
    if hook:
        for part in _chunks(text, 1900):
            requests.post(hook, json={"content": part}, timeout=20).raise_for_status()
        sent.append("discord")
    if not sent:
        log.info("未設定 Telegram/Discord，僅輸出本機 .md")
    return sent
