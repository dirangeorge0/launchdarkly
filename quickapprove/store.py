"""
Tiny local decision log for the Observe dashboard.

This is NOT the audit trail a real bank would need (see decision-log.md,
'biggest risk' - this store is in-memory/SQLite, unsigned, and anyone
with filesystem access could edit it). It exists purely so the Observe
story has real numbers behind it during the demo: approval rate and
error rate, split by which flag variation produced them.
"""

import sqlite3
import time
from contextlib import contextmanager

DB_PATH = "quickapprove.db"


def init_db():
    with _connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS decisions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ts REAL NOT NULL,
                branch_id TEXT NOT NULL,
                amount REAL NOT NULL,
                flag_variation INTEGER NOT NULL,
                outcome TEXT NOT NULL,
                latency_ms REAL NOT NULL,
                errored INTEGER NOT NULL
            )
            """
        )


@contextmanager
def _connect():
    conn = sqlite3.connect(DB_PATH)
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def record_decision(branch_id, amount, flag_variation, outcome, latency_ms, errored):
    with _connect() as conn:
        conn.execute(
            "INSERT INTO decisions (ts, branch_id, amount, flag_variation, outcome, latency_ms, errored) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (time.time(), branch_id, amount, int(flag_variation), outcome, latency_ms, int(errored)),
        )


def recent_decisions(limit=25):
    with _connect() as conn:
        rows = conn.execute(
            "SELECT ts, branch_id, amount, flag_variation, outcome, latency_ms, errored "
            "FROM decisions ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return [
        {
            "ts": r[0], "branch_id": r[1], "amount": r[2],
            "flag_variation": bool(r[3]), "outcome": r[4],
            "latency_ms": r[5], "errored": bool(r[6]),
        }
        for r in rows
    ]


def variation_stats():
    """
    The core Observe view: for each flag variation (ON = instant
    approval enabled for that branch, OFF = manual review), how many
    decisions, what fraction errored, average latency. This is the
    number you'd actually watch in production to decide whether to
    keep rolling out or roll back.
    """
    with _connect() as conn:
        rows = conn.execute(
            """
            SELECT flag_variation,
                   COUNT(*) as total,
                   SUM(errored) as errors,
                   AVG(latency_ms) as avg_latency,
                   SUM(CASE WHEN outcome = 'AUTO_APPROVED' THEN 1 ELSE 0 END) as auto_approved
            FROM decisions
            GROUP BY flag_variation
            """
        ).fetchall()
    stats = {}
    for variation, total, errors, avg_latency, auto_approved in rows:
        stats[bool(variation)] = {
            "total": total,
            "errors": errors or 0,
            "error_rate": round((errors or 0) / total * 100, 1) if total else 0.0,
            "avg_latency_ms": round(avg_latency or 0.0, 1),
            "auto_approved": auto_approved or 0,
            "auto_approval_rate": round((auto_approved or 0) / total * 100, 1) if total else 0.0,
        }
    return stats
