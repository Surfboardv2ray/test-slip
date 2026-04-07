#!/usr/bin/env python3
from __future__ import annotations

import base64
import binascii
import html
import json
import re
import urllib.error
import urllib.request
from pathlib import Path


INPUT_FILE = "tg/config.txt"
INTERMEDIATE_FILE = "dns/dns_.txt"
OUTPUT_FILE = "dns/dns.txt"

SLIPNET_PREFIX = "slipnet://"

TELEGRAM_API_BASE = "https://api.telegram.org"
MAX_TELEGRAM_MESSAGE = 3900  # safety margin under Telegram's message limit

# Match IPv4:port:flag items, optionally comma-separated.
IPV4_OCTET = r"(?:25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)"
DNS_ITEM_RE = re.compile(
    rf"^({IPV4_OCTET}(?:\.{IPV4_OCTET}){{3}}):(\d{{1,5}}):(\d+)$"
)


def is_valid_base64(value: str) -> bool:
    value = value.strip()
    if not value:
        return False

    if len(value) % 4 == 1:
        return False

    padded = value + "=" * (-len(value) % 4)

    try:
        base64.b64decode(padded, validate=True)
        return True
    except (binascii.Error, ValueError):
        return False


def decode_base64(value: str) -> str | None:
    value = value.strip()
    if not is_valid_base64(value):
        return None

    padded = value + "=" * (-len(value) % 4)

    try:
        decoded = base64.b64decode(padded, validate=True)
        return decoded.decode("utf-8")
    except (binascii.Error, ValueError, UnicodeDecodeError):
        return None


def normalize_dns_section(dns_section: str) -> str | None:
    items = [item.strip() for item in dns_section.split(",") if item.strip()]
    if not items:
        return None

    normalized_items: list[str] = []

    for item in items:
        match = DNS_ITEM_RE.fullmatch(item)
        if not match:
            return None

        ip = match.group(1)
        port = match.group(2)
        normalized_items.append(f"{ip}:{port}")

    return ",".join(normalized_items)


def extract_dns_section(decoded_text: str) -> str | None:
    parts = decoded_text.split("|")
    if len(parts) < 5:
        return None

    dns_section = parts[4].strip()
    if not dns_section:
        return None

    return normalize_dns_section(dns_section)


def split_text(lines: list[str], limit: int = MAX_TELEGRAM_MESSAGE, header: str = "Parsed DNS for Slipnet:\n\n"):
    chunks: list[list[str]] = []
    current: list[str] = []
    current_len = len(header)

    for line in lines:
        if not line.strip():
            continue

        formatted_line = f"🧬 <code>{html.escape(line)}</code>"
        line_len = len(formatted_line) + 1  # +1 for newline

        if current and current_len + line_len > limit:
            chunks.append(current)
            current = [line]
            current_len = len(header) + line_len
        else:
            current.append(line)
            current_len += line_len

    if current:
        chunks.append(current)

    return chunks


def format_chunk(lines: list[str]) -> str:
    body = "\n".join(
        f"🧬 <code>{html.escape(line)}</code>"
        for line in lines
        if line.strip()
    )
    return f"Parsed DNS for Slipnet:\n\n{body}"


def send_telegram_message(token: str, chat_id: str, text: str) -> None:
    url = f"{TELEGRAM_API_BASE}/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }

    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            body = response.read().decode("utf-8", errors="replace")
            result = json.loads(body)
            if not result.get("ok"):
                raise RuntimeError(f"Telegram API returned ok=false: {body}")
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP error from Telegram API: {e.code} - {error_body}") from e
    except Exception as e:
        raise RuntimeError(f"Failed to send Telegram message: {e}") from e


def send_telegram_chunks(token: str, chat_id: str, lines: list[str]) -> int:
    chunks = split_text(lines)
    for chunk in chunks:
        message = format_chunk(chunk)
        send_telegram_message(token, chat_id, message)
    return len(chunks)


def main() -> None:
    try:
        with open(INPUT_FILE, "r", encoding="utf-8", errors="ignore") as in_f:
            lines = in_f.readlines()
    except FileNotFoundError:
        print(f"Input file not found: {INPUT_FILE}")
        return

    captured_dns: list[str] = []

    for raw_line in lines:
        line = raw_line.strip()

        if not line.startswith(SLIPNET_PREFIX):
            continue

        payload = line[len(SLIPNET_PREFIX):].strip()
        decoded = decode_base64(payload)
        if decoded is None:
            continue

        dns_section = extract_dns_section(decoded)
        if dns_section is None:
            continue

        captured_dns.append(dns_section)

    Path(INTERMEDIATE_FILE).parent.mkdir(parents=True, exist_ok=True)
    Path(OUTPUT_FILE).parent.mkdir(parents=True, exist_ok=True)

    with open(INTERMEDIATE_FILE, "w", encoding="utf-8") as out_f:
        for dns_line in captured_dns:
            out_f.write(dns_line + "\n")

    seen: set[str] = set()
    unique_dns: list[str] = []

    with open(INTERMEDIATE_FILE, "r", encoding="utf-8", errors="ignore") as in_f:
        for raw_line in in_f:
            line = raw_line.strip()
            if not line:
                continue
            if line in seen:
                continue
            seen.add(line)
            unique_dns.append(line)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as out_f:
        for dns_line in unique_dns:
            out_f.write(f"🧬 {dns_line}\n")

    token = None
    chat_id = None

    import os
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")

    sent_chunks = 0
    if token and chat_id:
        try:
            sent_chunks = send_telegram_chunks(token, chat_id, unique_dns)
        except Exception as e:
            print(f"Telegram send failed: {e}")
    else:
        print("Telegram not sent: missing TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID")

    print(f"Parsed: {INPUT_FILE}")
    print(f"Captured DNS lines: {len(captured_dns)}")
    print(f"Unique DNS lines: {len(unique_dns)}")
    print(f"Sent Telegram chunks: {sent_chunks}")
    print(f"Saved intermediate: {INTERMEDIATE_FILE}")
    print(f"Saved final: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
