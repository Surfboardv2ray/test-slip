import os
import sys
import json
import pathlib
import html
import urllib.request
import urllib.error

TELEGRAM_API_BASE = "https://api.telegram.org"
MAX_TELEGRAM_MESSAGE = 3900  # safety margin under Telegram message limits


def split_text(lines, limit: int = MAX_TELEGRAM_MESSAGE, header: str = "Parsed DNS for Slipnet:\n\n"):
    chunks = []
    current = []
    current_len = len(header)

    for line in lines:
        line_len = len(line) + 1  # +1 for newline

        if current and current_len + line_len > limit:
            chunks.append(current)
            current = [line]
            current_len = len(header) + len(line) + 1
        else:
            current.append(line)
            current_len += line_len

    if current:
        chunks.append(current)

    return chunks


def send_telegram_message(token: str, chat_id: str, text: str):
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


def format_chunk(lines):
    body = "\n".join(f"<code>{html.escape(line)}</code>" for line in lines if line.strip())
    return f"Parsed DNS for Slipnet:\n\n{body}"


def main():
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")

    if not token:
        print("Missing environment variable: TELEGRAM_BOT_TOKEN", file=sys.stderr)
        sys.exit(1)

    if not chat_id:
        print("Missing environment variable: TELEGRAM_CHAT_ID", file=sys.stderr)
        sys.exit(1)

    file_path = pathlib.Path("dns/dns.txt")

    if not file_path.exists():
        print(f"File not found: {file_path}", file=sys.stderr)
        sys.exit(1)

    content = file_path.read_text(encoding="utf-8", errors="replace")
    lines = [line.strip() for line in content.splitlines() if line.strip()]

    if not lines:
        lines = ["(dns/dns.txt is empty)"]

    chunks = split_text(lines)

    for chunk in chunks:
        message = format_chunk(chunk)
        send_telegram_message(token, chat_id, message)

    print(f"Sent {len(chunks)} message(s) from {file_path}")


if __name__ == "__main__":
    main()
