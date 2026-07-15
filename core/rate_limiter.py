from __future__ import annotations

import threading
import time
from collections import deque
from dataclasses import dataclass, field

import streamlit as st

from config import settings


class RateLimitError(RuntimeError):
    """Raised when a session or global rate/budget limit is exceeded."""


@dataclass
class _GlobalUsageTracker:
    _lock: threading.Lock = field(default_factory=threading.Lock)
    _query_times: deque = field(default_factory=deque)
    _byte_events: deque = field(default_factory=deque)

    _WINDOW_SECONDS = 24 * 3600

    def _prune(self, now: float) -> None:
        cutoff = now - self._WINDOW_SECONDS
        while self._query_times and self._query_times[0] < cutoff:
            self._query_times.popleft()
        while self._byte_events and self._byte_events[0][0] < cutoff:
            self._byte_events.popleft()

    def check_query_budget(self) -> None:
        now = time.time()
        with self._lock:
            self._prune(now)
            if len(self._query_times) >= settings.GLOBAL_MAX_QUERIES_PER_DAY:
                raise RateLimitError(
                    f"This app has hit its shared daily limit of "
                    f"{settings.GLOBAL_MAX_QUERIES_PER_DAY} queries across all users. "
                    "Please try again later."
                )

    def check_byte_budget(self, additional_bytes: int) -> None:
        now = time.time()
        with self._lock:
            self._prune(now)
            total = sum(b for _, b in self._byte_events)
            if total + additional_bytes > settings.GLOBAL_MAX_BYTES_PER_DAY:
                raise RateLimitError(
                    "This app has hit its shared daily data-scan budget across all "
                    "users. Please try again later."
                )

    def record(self, bytes_processed: int) -> None:
        now = time.time()
        with self._lock:
            self._query_times.append(now)
            self._byte_events.append((now, bytes_processed))

    def snapshot(self) -> dict:
        now = time.time()
        with self._lock:
            self._prune(now)
            return {
                "queries_today": len(self._query_times),
                "queries_limit": settings.GLOBAL_MAX_QUERIES_PER_DAY,
                "bytes_today": sum(b for _, b in self._byte_events),
                "bytes_limit": settings.GLOBAL_MAX_BYTES_PER_DAY,
            }


@st.cache_resource
def _get_global_tracker() -> _GlobalUsageTracker:
    return _GlobalUsageTracker()


def check_session_limit() -> None:
    """Raise RateLimitError if this browser session has run too many
    queries within the configured rolling window."""
    now = time.time()
    timestamps: deque = st.session_state.setdefault("_rl_session_times", deque())
    cutoff = now - settings.SESSION_WINDOW_MINUTES * 60
    while timestamps and timestamps[0] < cutoff:
        timestamps.popleft()
    if len(timestamps) >= settings.SESSION_MAX_QUERIES:
        raise RateLimitError(
            f"You've hit the limit of {settings.SESSION_MAX_QUERIES} queries per "
            f"{settings.SESSION_WINDOW_MINUTES} minutes. Please wait a bit and try again."
        )


def record_session_query() -> None:
    timestamps: deque = st.session_state.setdefault("_rl_session_times", deque())
    timestamps.append(time.time())


def check_global_query_limit() -> None:
    _get_global_tracker().check_query_budget()


def check_global_byte_budget(additional_bytes: int) -> None:
    _get_global_tracker().check_byte_budget(additional_bytes)


def record_global_usage(bytes_processed: int) -> None:
    _get_global_tracker().record(bytes_processed)


def global_usage_snapshot() -> dict:
    return _get_global_tracker().snapshot()
