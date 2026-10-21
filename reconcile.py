#!/usr/bin/env python3
"""Payment reconciliation.

Reads payments.jsonl and works out how much money we actually collected.
Run:  python3 reconcile.py
"""

import json
from datetime import datetime


def parse_ts(ts_val):
    """Safely parse ISO/UTC timestamps (or numeric timestamps) for comparison."""
    if isinstance(ts_val, (int, float)):
        return float(ts_val)
    if isinstance(ts_val, str):
        ts_str = ts_val.strip()
        if ts_str.endswith("Z"):
            ts_str = ts_str[:-1] + "+00:00"
        try:
            return datetime.fromisoformat(ts_str).timestamp()
        except ValueError:
            return ts_str
    return ""


def parse_amount(amt_val):
    """Safely convert amount (even if formatted as a string with commas/symbols)."""
    if isinstance(amt_val, (int, float)):
        return float(amt_val)
    if isinstance(amt_val, str):
        cleaned = amt_val.replace(",", "").replace("₦", "").replace("NGN", "").strip()
        return float(cleaned)
    return 0.0


latest_events = {}

with open("payments.jsonl", "r", encoding="utf-8") as f:
    for line in f:
        line = line.strip()
        if not line:
            continue
        try:
            event = json.loads(line)
        except (json.JSONDecodeError, ValueError):
            continue

        if not isinstance(event, dict):
            continue

        # Ignore events without a valid txn_id
        txn_id = event.get("txn_id")
        if not txn_id or not isinstance(txn_id, str) or not txn_id.strip():
            continue
        txn_id = txn_id.strip()

        # Ensure timestamp exists
        ts_raw = event.get("ts")
        if ts_raw is None:
            continue
        ts_parsed = parse_ts(ts_raw)

        # Keep only the latest attempt (by ts) for each txn_id
        if txn_id not in latest_events or ts_parsed >= latest_events[txn_id][0]:
            latest_events[txn_id] = (ts_parsed, event)

total = 0.0
count = 0

for txn_id, (_, event) in latest_events.items():
    if str(event.get("status", "")).strip().lower() == "success":
        try:
            total += parse_amount(event["amount"])
            count += 1
        except (KeyError, ValueError, TypeError):
            continue

with open("expected.txt", "r", encoding="utf-8") as f:
    expected = int(f.read().strip())

if count != expected:
    print(f"Check failed: counted {count} successful payments, expected {expected}.")
    print("Something in the data isn't being handled the way the README describes.")
else:
    print(f"Check passed: {count} successful payments.")
    print(f"Your code: KOYA-{round(total)}")
