#!/usr/bin/env python3
"""
Groq RPM Stress Test (Safe, configurable)

Sends small chat/completions requests at a target requests-per-minute (RPM)
and reports achieved throughput, 2xx, 429, and other errors. Use for quick
validation of org-tier limits (e.g., ~300 RPM for Developer tier).

IMPORTANT: This incurs usage. Start with a short duration (e.g., 20–60s).
"""

import argparse
import os
import queue
import threading
import time
from typing import Optional

import requests


def make_request(session: requests.Session, api_key: str, service_tier: Optional[str], model: str) -> tuple[int, dict]:
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    body = {
        "model": model,
        "messages": [{"role": "user", "content": "ping"}],
        "max_tokens": 4,
    }
    if service_tier:
        body["service_tier"] = service_tier

    resp = session.post(url, headers=headers, json=body, timeout=10)
    # Collect relevant headers for diagnostics
    headers_out = {
        k: v for k, v in resp.headers.items() if "ratelimit" in k.lower()
    }
    return resp.status_code, headers_out


def worker(request_q: "queue.Queue[None]", result_q: "queue.Queue[tuple[int, dict]]", api_key: str, service_tier: Optional[str], model: str, stop_event: threading.Event) -> None:
    session = requests.Session()
    while not stop_event.is_set():
        try:
            request_q.get(timeout=0.25)
        except queue.Empty:
            continue
        try:
            status, hdrs = make_request(session, api_key, service_tier, model)
            result_q.put((status, hdrs))
        except Exception:
            result_q.put((0, {}))
        finally:
            request_q.task_done()


def main():
    parser = argparse.ArgumentParser(description="Groq RPM stress test")
    parser.add_argument("--rpm", type=int, default=60, help="Target requests per minute (default: 60)")
    parser.add_argument("--duration", type=int, default=30, help="Test duration in seconds (default: 30)")
    parser.add_argument("--concurrency", type=int, default=8, help="Number of worker threads (default: 8)")
    parser.add_argument("--service-tier", choices=["flex", "auto", "on_demand"], default=None, help="Optional service tier for chat requests")
    parser.add_argument("--model", default="llama3-8b-8192", help="Model name for chat/completions (default: llama3-8b-8192)")
    args = parser.parse_args()

    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        print("❌ GROQ_API_KEY environment variable is not set.")
        return

    interval = 60.0 / max(args.rpm, 1)
    total_requests_planned = int(args.rpm * (args.duration / 60.0))

    print("🚀 Groq RPM Stress Test")
    print("=" * 50)
    print(f"Target RPM: {args.rpm}")
    print(f"Duration: {args.duration}s")
    print(f"Planned requests: ~{total_requests_planned}")
    print(f"Concurrency: {args.concurrency}")
    if args.service_tier:
        print(f"Service tier: {args.service_tier}")
    print("Note: This generates billable requests. Keep duration short.")

    request_q: "queue.Queue[None]" = queue.Queue()
    result_q: "queue.Queue[tuple[int, dict]]" = queue.Queue()
    stop_event = threading.Event()

    # Start workers
    workers: list[threading.Thread] = []
    for _ in range(args.concurrency):
        t = threading.Thread(target=worker, args=(request_q, result_q, api_key, args.service_tier, args.model, stop_event), daemon=True)
        t.start()
        workers.append(t)

    # Schedule requests uniformly
    start = time.time()
    next_time = start
    end_time = start + args.duration
    scheduled = 0
    while time.time() < end_time:
        now = time.time()
        if now >= next_time:
            request_q.put(None)
            scheduled += 1
            next_time += interval
        else:
            time.sleep(min(0.002, next_time - now))

    # Wait for all scheduled tasks to be processed or until a small grace period
    request_q.join()
    stop_event.set()

    # Drain results
    successes = 0
    rate_limits = 0
    errors = 0
    last_headers = {}

    while not result_q.empty():
        status, hdrs = result_q.get()
        last_headers = hdrs or last_headers
        if status == 200:
            successes += 1
        elif status == 429:
            rate_limits += 1
        elif status == 0:
            errors += 1
        else:
            errors += 1

    elapsed = max(time.time() - start, 0.0001)
    achieved_rps = successes / elapsed
    achieved_rpm = achieved_rps * 60.0

    print("\n" + "=" * 50)
    print("📊 Results")
    print("=" * 50)
    print(f"Scheduled: {scheduled}")
    print(f"Success (200): {successes}")
    print(f"Rate limited (429): {rate_limits}")
    print(f"Other/Errors: {errors}")
    print(f"Elapsed: {elapsed:.2f}s")
    print(f"Achieved RPM (2xx only): {achieved_rpm:.1f}")

    if last_headers:
        print("\nRate limit headers (last response):")
        for k, v in last_headers.items():
            print(f"  {k}: {v}")


if __name__ == "__main__":
    main()




