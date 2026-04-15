"""Lightweight timestamped logs for ingestion debugging (stdout / uvicorn)."""

from __future__ import annotations

from datetime import datetime, timezone


def plog(stage: str, message: str) -> None:
    ts = datetime.now(timezone.utc).strftime("%H:%M:%S")
    print(f"[glp {ts} UTC] [{stage}] {message}", flush=True)
