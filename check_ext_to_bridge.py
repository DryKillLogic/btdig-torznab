#!/usr/bin/env python3
"""Measure an ext.to Torznab bridge against the live service.

Answers the two questions that decide whether a deep walk is workable:
how long one page costs, and whether a request ever answers at all.

    ./check_ext_to_bridge.py https://ext.myserver.stream/torznab/api
    ./check_ext_to_bridge.py <url> --query "The Rookie S07E04" --pages 20
"""

import argparse
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

DEFAULT_QUERY = "The Rookie S07E04"


def fetch(url, params, timeout):
    query = urllib.parse.urlencode(params)
    started = time.monotonic()
    try:
        with urllib.request.urlopen(f"{url}?{query}", timeout=timeout) as response:
            body = response.read()
            elapsed = time.monotonic() - started
            return body, elapsed, None
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        return b"", time.monotonic() - started, exc


def items(body):
    try:
        root = ET.fromstring(body)
    except ET.ParseError:
        return []
    return root.findall(".//item")


def report(label, body, elapsed, error, timeout):
    if error is not None:
        print(f"  {label:<28} FAILED after {elapsed:6.1f}s: {error}")
        return False
    found = items(body)
    print(f"  {label:<28} {elapsed:6.1f}s  {len(body):>8d} bytes  {len(found):>4d} item(s)")
    if elapsed > timeout * 0.9:
        print(f"    (at the {timeout:.0f}s client timeout — treat as a timeout)")
    return True


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("url")
    parser.add_argument("--query", default=DEFAULT_QUERY)
    parser.add_argument("--pages", type=int, default=20)
    parser.add_argument("--timeout", type=float, default=180.0)
    args = parser.parse_args()

    print(f"bridge: {args.url}   client timeout: {args.timeout:.0f}s\n")

    checks = [
        ("caps", {"t": "caps"}, True),
        ("one page (limit=50)", {"t": "search", "q": args.query, "cat": 5000,
                                 "limit": 50, "sort": "age", "order": "desc"}, True),
        ("deep walk (pages, no enrich)", {"t": "search", "q": args.query, "cat": 5000,
                                          "limit": 50, "sort": "age", "order": "desc",
                                          "pages": args.pages, "enrich": 0}, True),
    ]

    ok = True
    for label, params, required in checks:
        body, elapsed, error = fetch(args.url, params, args.timeout)
        passed = report(label, body, elapsed, error, args.timeout)
        if required:
            ok = ok and passed

    print("\nRESULT:", "bridge answers" if ok else "bridge did NOT answer — nothing downstream can work")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
