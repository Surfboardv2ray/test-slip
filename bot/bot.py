import os
import sys
import json
import pathlib
import html
import urllib.request
import urllib.error

TELEGRAM_API_BASE = "https://api.telegram.org"
MAX_TELEGRAM_MESSAGE = 3900  # safety margin under Telegram message limits


def split_text(text: str, limit: int = MAX_TELEGRAM_MESSAGE):
    chunks = []
    current = []
    current_len = 0

    for line in text.splitlines(keepends=True):
        if current_len + len(line) > limit and current:
            chunks.append("".join(current))
            current = [line]
            current_len = len(line)
        else:
            current.append(line)
            current_len += len(line)

    if current:
        chunks.append("".join(current))

    return chunks


def send_telegram_message(token: str, chat_id: str, text: str):
    url = f"{TELEGRAM_API_BASE}/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": f"<blockquote expandable>{html.escape(text)}</blockquote>",
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

    if not content.strip():
        content = "(dns/dns.txt is empty)"

    chunks = split_text(content)

    for index, chunk in enumerate(chunks, start=1):
        if len(chunks) == 1:
            message = chunk
        else:
            message = f"Part {index}/{len(chunks)}\n\n{chunk}"
        send_telegram_message(token, chat_id, message)

    print(f"Sent {len(chunks)} message(s) from {file_path}")


if __name__ == "__main__":
    main()
    
