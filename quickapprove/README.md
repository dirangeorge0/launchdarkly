# QuickApprove

Sample app for the LaunchDarkly EMEA Solutions Engineering panel. It shows how a regulated bank could release a payments change to a small group of branches first, watch the outcome, and roll back in seconds without a deploy.

## Scenario

A regulated EMEA bank wants certain branches to auto-approve low-value payments (up to £1,000) instead of sending every payment to manual review. Leadership wants this shipped quickly, but a bad rollout would expose the bank to customer harm and regulatory risk.

- LaunchDarkly decides **whether** instant approval is on for a given branch. This is a rollout decision.
- The app decides **whether** a payment qualifies, using a fixed £1,000 threshold in code. Compliance can find that number in the codebase.
- If LaunchDarkly is unreachable, every payment fails closed to manual review.

## Setup

Requires Python 3.10 or newer.

```bash
cd quickapprove
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Edit `.env`:

1. Set `LAUNCHDARKLY_SDK_KEY` to the **Test** environment's server-side SDK key (LaunchDarkly: project, Settings, SDK keys).
2. Keep `LD_FLAG_KEY=instant-approval`.

Run the app:

```bash
python app.py
```

Open `http://localhost:5050/dashboard` for the Observe view. See [OBSERVE.md](OBSERVE.md) for what Observe covers and how to check it in LaunchDarkly.

## LaunchDarkly configuration

The app expects the following in the **Test** environment:

| Item | Value | Notes |
|---|---|---|
| Flag | `instant-approval` (boolean) | Default off |
| Segment | `pilot-branches` | Branch keys for the pilot group |
| Flag rule | Serve `true` when context is in `pilot-branches` | Context kind: `branch` |
| Metric / event | `authorization-decision` | Custom event with outcome, amount, latency, error. Not yet turned into a LaunchDarkly metric. |
| Observability | Observability plugin | Optional. Sends data to LaunchDarkly Observability, which may need enabling on your plan. Set `LD_OBSERVABILITY=off` to run without it. |

Test it: send a request with a branch in `pilot-branches`, then confirm the flag shows as on for that branch.

```bash
curl -X POST http://localhost:5050/authorize \
  -H "Content-Type: application/json" \
  -d '{"branch_id": "branch-001", "region": "London", "amount": 250}'
```

## Demo flow

1. **Baseline:** flag off. Payments go to manual review.
2. **Pilot:** turn the flag on for `pilot-branches`. Pilot branches auto-approve payments up to £1,000. Other branches are unchanged.
3. **Observe:** the dashboard compares error rate, latency and approval rate by flag variation, and its Observe panel shows what is connected to LaunchDarkly.
4. **Rollback:** turn the flag off. Pilot branches return to manual review within seconds, with no code change.

## Design decisions

See [decision-log.md](decision-log.md).

## Known limits

This is a demo, not production code.

- No authentication on `/authorize` or `/dashboard`.
- The decision store is a local SQLite file. It isn't a tamper-evident audit trail.
- Payment errors are simulated (`SIMULATED_ERROR_RATE`).
- `debug=True` is set in `app.py`. Turn it off outside a demo.
