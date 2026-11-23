"""
QuickApprove - sample app for the LaunchDarkly SE homework.

Scenario: a regulated EMEA bank wants to let certain branches
auto-approve low-value payments instantly instead of routing every
single one to manual review, without a code deploy every time they
want to change which branches, or what fraction of traffic, gets that
treatment.

Two things are deliberately kept separate:
  - LaunchDarkly decides WHETHER instant approval is switched on for
    this branch right now (a rollout/targeting decision).
  - This app's own business rule decides whether THIS transaction is
    small enough to qualify (a fixed threshold, not something you'd
    want hidden inside a flag rule in a regulated context - it's the
    kind of number compliance wants to find in code, not in a UI).
"""

import logging
import os
import random
import time

from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request

import ld
import store

load_dotenv()
logging.basicConfig(level=logging.INFO)

app = Flask(__name__)

AUTO_APPROVAL_THRESHOLD = 1000.00  # GBP. Fixed in code, not in a flag - see decision-log.md.

# Simulated downstream payment-processor flakiness, so the Observe
# dashboard has something real to show and something real to catch.
# Clearly fake, clearly labelled - not trying to pass this off as a
# real production error model.
SIMULATED_ERROR_RATE = float(os.environ.get("SIMULATED_ERROR_RATE", "0.04"))


@app.route("/health")
def health():
    return jsonify({"status": "ok"})


@app.route("/authorize", methods=["POST"])
def authorize():
    body = request.get_json(force=True, silent=True) or {}

    branch_id = body.get("branch_id", "unknown-branch")
    region = body.get("region", "")
    amount = float(body.get("amount", 0))

    start = time.monotonic()

    context = ld.build_branch_context(branch_id, region=region)  # kind=branch, keyed on branch_id
    instant_approval_on = ld.is_instant_approval_enabled(context)

    errored = random.random() < SIMULATED_ERROR_RATE

    if errored:
        outcome = "PROCESSOR_ERROR"
    elif instant_approval_on and amount <= AUTO_APPROVAL_THRESHOLD:
        outcome = "AUTO_APPROVED"
    else:
        outcome = "MANUAL_REVIEW"

    latency_ms = round((time.monotonic() - start) * 1000, 2)

    store.record_decision(
        branch_id=branch_id,
        amount=amount,
        flag_variation=instant_approval_on,
        outcome=outcome,
        latency_ms=latency_ms,
        errored=errored,
    )
    ld.track_decision(context, outcome, amount, latency_ms, errored)

    return jsonify(
        {
            "branch_id": branch_id,
            "amount": amount,
            "instant_approval_flag": instant_approval_on,
            "outcome": outcome,
            "latency_ms": latency_ms,
        }
    )


@app.route("/dashboard")
def dashboard():
    stats = store.variation_stats()
    recent = store.recent_decisions(limit=25)
    return render_template("dashboard.html", stats=stats, recent=recent, flag_key=ld.FLAG_KEY)


if __name__ == "__main__":
    sdk_key = os.environ.get("LAUNCHDARKLY_SDK_KEY")
    if not sdk_key:
        raise SystemExit(
            "LAUNCHDARKLY_SDK_KEY is not set. Copy .env.example to .env and fill it in."
        )

    ld.init_client(sdk_key)
    store.init_db()

    port = int(os.environ.get("PORT", 5050))
    try:
        app.run(host="0.0.0.0", port=port, debug=True, use_reloader=False)
    finally:
        ld.flush()
        ld.close()
