"""
LaunchDarkly client wrapper for QuickApprove.

Why this file exists on its own (not just called inline from app.py):
the fail-closed decision below is the single most important piece of
judgement in this whole build, for a regulated-bank scenario, and it
deserves to live somewhere obvious and commented, not buried inside a
Flask route.

Context model: this app targets by BRANCH, not by individual customer.
The business question LaunchDarkly answers is "is instant approval
switched on for this branch yet" (a rollout decision) - not "should
this specific payment be approved" (that's the app's own business
rule, applied locally, after LD's answer comes back). Keeping those
two decisions separate is deliberate - see the decision log.
"""

import logging
import os

import ldclient
from ldclient import Context
from ldclient.config import Config

log = logging.getLogger("quickapprove.ld")

FLAG_KEY = os.environ.get("LD_FLAG_KEY", "instant-approval")

# Fail-closed default. If LaunchDarkly is unreachable, misconfigured,
# or the SDK key is wrong, every evaluation below returns False - which
# in this app always means "route to manual review". A regulated bank
# cannot afford an SDK outage to silently mean "auto-approve everyone".
# Fail SAFE, not fail FAST. This is a deliberate trade-off (see
# decision-log.md) - it costs speed/availability during an LD outage
# in exchange for never auto-approving a payment nobody actually
# evaluated.
FAIL_CLOSED_DEFAULT = False

_client = None


def init_client(sdk_key: str, wait_seconds: float = 5.0):
    """
    Initialise the LD client once at app startup. Blocks briefly so we
    know, at boot, whether LD is actually reachable - rather than
    discovering that on the first real transaction.
    """
    global _client
    config = Config(sdk_key)
    ldclient.set_config(config)
    client = ldclient.get()

    client.wait_for_initialization(timeout=wait_seconds)
    if not client.is_initialized():
        log.warning(
            "LaunchDarkly client did NOT initialise within %ss. "
            "Every flag evaluation will fail closed (manual review) "
            "until this is resolved.",
            wait_seconds,
        )
    _client = client
    return client


def build_branch_context(branch_id: str, region: str = "") -> Context:
    """
    One context per branch, of kind 'branch'. Targeting in the LD UI
    uses the 'pilot-branches' segment keyed on the branch key, so the
    rollout decision lives in LaunchDarkly, not in this code.
    'region' is accepted for logging and is not sent to LaunchDarkly.
    """
    return Context.create(branch_id, "branch")


def is_instant_approval_enabled(context: Context) -> bool:
    """
    The one call in this app that asks LaunchDarkly anything.
    Deliberately explicit about the fail-closed path rather than
    relying silently on the SDK's own default-value behaviour - an
    auditor reading this code should not have to know SDK internals
    to see why a decision defaulted to manual review.
    """
    if _client is None or not _client.is_initialized():
        log.warning("LD client not ready - forcing fail-closed (manual review).")
        return FAIL_CLOSED_DEFAULT

    return _client.variation(FLAG_KEY, context, FAIL_CLOSED_DEFAULT)


def track_decision(context: Context, outcome: str, amount: float, latency_ms: float, errored: bool):
    """
    Observe: every decision fires a custom event back to LaunchDarkly,
    tagged with the outcome and the variation that produced it. This
    is what lets a flag CHANGE be tied to a CONSEQUENCE later, instead
    of just a toggle in a UI with no evidence either way.
    """
    if _client is None:
        return
    _client.track(
        "authorization-decision",
        context,
        data={"outcome": outcome, "amount": amount, "latency_ms": latency_ms, "errored": errored},
    )


def flush():
    if _client is not None:
        _client.flush()


def close():
    if _client is not None:
        _client.close()
