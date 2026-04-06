#!/usr/bin/env python3
from __future__ import annotations

import base64
import binascii
import re


INPUT_FILE = "tg/config.txt"
INTERMEDIATE_FILE = "dns/dns_.txt"
OUTPUT_FILE = "dns/dns.txt"

SLIPNET_PREFIX = "slipnet://"

# Strict IPv4:port validator.
IPV4_OCTET = r"(?:25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)"
PORT = r"(?:[1-9]\d{0,4})"

# One or more IPv4:port items separated by commas.
DNS_LIST_RE = re.compile(
    rf"^{IPV4_OCTET}(?:\.{IPV4_OCTET}){{3}}:{PORT}"
    rf"(?:,{IPV4_OCTET}(?:\.{IPV4_OCTET}){{3}}:{PORT})*$"
)


def is_valid_base64(value: str) -> bool:
    value = value.strip()
    if not value:
        return False

    # Base64 length should not be 1 mod 4.
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


def extract_dns_section(decoded_text: str) -> str | None:
    parts = decoded_text.split("|")
    if len(parts) < 5:
        return None

    dns_section = parts[4].strip()
    if not dns_section:
        return None

    if not DNS_LIST_RE.fullmatch(dns_section):
        return None

    return dns_section


def main() -> None:
    try:
        with open(INPUT_FILE, "r", encoding="utf-8", errors="ignore") as in_f:
            lines = in_f.readlines()
    except FileNotFoundError:
        print(f"Input file not found: {INPUT_FILE}")
        return

    # Collect valid DNS strings first.
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

    # Save all captured DNS lines to dns_.txt.
    with open(INTERMEDIATE_FILE, "w", encoding="utf-8") as out_f:
        for dns_line in captured_dns:
            out_f.write(dns_line + "\n")

    # Remove duplicates while preserving order, then save to dns.txt.
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
            out_f.write(dns_line + "\n")

    print(f"Parsed: {INPUT_FILE}")
    print(f"Captured DNS lines: {len(captured_dns)}")
    print(f"Unique DNS lines: {len(unique_dns)}")
    print(f"Saved intermediate: {INTERMEDIATE_FILE}")
    print(f"Saved final: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
