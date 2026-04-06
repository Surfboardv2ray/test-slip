#!/usr/bin/env python3
from __future__ import annotations

import base64
import binascii
import re


INPUT_FILE = "tg/config.txt"
INTERMEDIATE_FILE = "dns/dns_.txt"
OUTPUT_FILE = "dns/dns.txt"

SLIPNET_PREFIX = "slipnet://"

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

    print(f"Parsed: {INPUT_FILE}")
    print(f"Captured DNS lines: {len(captured_dns)}")
    print(f"Unique DNS lines: {len(unique_dns)}")
    print(f"Saved intermediate: {INTERMEDIATE_FILE}")
    print(f"Saved final: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
