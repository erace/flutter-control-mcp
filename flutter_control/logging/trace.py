"""Trace context and logging for debugging."""

import json
import time
import secrets
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime

from ..config import LOG_DIR


def generate_trace_id() -> str:
    """Generate a short random trace ID."""
    return secrets.token_hex(3)  # 6 chars


@dataclass
class TraceEntry:
    """A single trace log entry."""
    elapsed_ms: int
    event: str
    detail: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "elapsed_ms": self.elapsed_ms,
            "event": self.event,
            "detail": self.detail,
        }


@dataclass
class TraceContext:
    """Context for tracing a single MCP tool call."""
    trace_id: str
    tool_name: str
    arguments: Dict[str, Any]
    start_time: float = field(default_factory=time.time)
    entries: List[TraceEntry] = field(default_factory=list)

    def log(self, event: str, detail: str = ""):
        """Add a trace entry."""
        elapsed_ms = int((time.time() - self.start_time) * 1000)
        entry = TraceEntry(elapsed_ms=elapsed_ms, event=event, detail=detail)
        self.entries.append(entry)
        print(f"[{self.trace_id}] {elapsed_ms:6d}ms {event:15s} {detail}", file=sys.stderr, flush=True)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "trace_id": self.trace_id,
            "tool_name": self.tool_name,
            "arguments": self.arguments,
            "start_time": datetime.fromtimestamp(self.start_time).isoformat(),
            "total_ms": int((time.time() - self.start_time) * 1000),
            "entries": [e.to_dict() for e in self.entries],
        }

    def save(self):
        """Append trace to the traces log file."""
        traces_file = LOG_DIR / "traces.jsonl"
        with open(traces_file, "a") as f:
            f.write(json.dumps(self.to_dict()) + "\n")


_recent_traces: List[TraceContext] = []
MAX_RECENT_TRACES = 100


def log_trace(trace: TraceContext):
    """Store trace in memory and save to disk."""
    global _recent_traces
    _recent_traces.append(trace)
    if len(_recent_traces) > MAX_RECENT_TRACES:
        _recent_traces = _recent_traces[-MAX_RECENT_TRACES:]
    trace.save()


def get_recent_traces(count: int = 10) -> List[Dict[str, Any]]:
    """Get recent traces for debugging."""
    return [t.to_dict() for t in _recent_traces[-count:]]


def get_trace(trace_id: str) -> Optional[Dict[str, Any]]:
    """Get a specific trace by ID."""
    for t in reversed(_recent_traces):
        if t.trace_id == trace_id:
            return t.to_dict()
    return None
