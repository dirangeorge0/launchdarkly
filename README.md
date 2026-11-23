# QuickApprove: LaunchDarkly release and observe demo

A small Python app that shows how a regulated EMEA bank could release instant approval of low-value payments to a pilot group of branches, watch what happens, and roll back in seconds without a deploy. Built for the LaunchDarkly EMEA Solutions Engineering homework by Diran George.

## The scenario

A bank wants some branches to auto-approve payments of up to 1,000 GBP instead of sending every payment to manual review. Leadership wants to ship faster. Risk appetite is low.

Two decisions are kept apart on purpose:

- **LaunchDarkly decides whether instant approval is on for a branch.** This is the rollout decision. Product and Engineering own it.
- **The app decides whether the payment is small enough.** The 1,000 GBP limit is hard-coded, so compliance can find it in the codebase and nobody can change it from a dashboard.

If LaunchDarkly can't be reached when the app starts, every payment fails closed to manual review.

## What is in this repo

| Path | What it is |
|---|---|
| `quickapprove/app.py` | Flask app: `/authorize`, `/dashboard`, `/health` |
| `quickapprove/ld.py` | The only file that talks to LaunchDarkly: client start-up, branch context, flag check, event and metrics |
| `quickapprove/store.py` | Local SQLite record of decisions, for the dashboard |
| `quickapprove/OBSERVE.md` | What Observe means here, how to check it in LaunchDarkly, and what is not proven yet |
| `quickapprove/decision-log.md` | The decision log: design trade-offs, an AI suggestion I reverted, risks and next steps |
| `quickapprove/README.md` | Shorter app-level notes |

## What it proves

| Brief item | Evidence |
|---|---|
| **Release** | A boolean flag, `instant-approval`, targeted at a `pilot-branches` segment. Default rule off. Instant rollback by switching the flag off. |
| **Observe** (chosen over Iterate) | Custom event `authorization-decision`, an optional observability plugin, metrics tagged with the flag value, a dashboard Observe panel, and the flag's change history. Status is **partial**, see [OBSERVE.md](quickapprove/OBSERVE.md). |

I chose Observe because LaunchDarkly marks the `branch` context kind as unavailable for experiments, and a few days of pilot traffic is too little for a valid experiment.

## Environment assumptions

- Python 3.10 or newer (tested on 3.12). The LaunchDarkly Python SDK 9.19.0 needs 3.10 or newer.
- A LaunchDarkly account with a project and a **Test** environment. Observability must be available on the account if you want logs and metrics. The app runs without it.
- Outbound HTTPS to LaunchDarkly. With the observability plugin on, also outbound gRPC to `otel.observability.app.launchdarkly.com:4317`.
- Nothing from my LaunchDarkly account is in this repo. The SDK key lives in a local `.env` file that git ignores. **You must create your own flag, segment and key** (below).

## Setup

### 1. Run the app

```bash
git clone https://github.com/dirangeorge0/launchdarkly.git
cd launchdarkly/quickapprove
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

### 2. Re-create the LaunchDarkly configuration

In your own LaunchDarkly project, Test environment:

1. **SDK key.** Go to Project settings, then Environments, then Test, and copy the **server-side SDK key**. Paste it into `.env` as `LAUNCHDARKLY_SDK_KEY`. Never commit it.
2. **Context kind.** Create a context kind with the key `branch`. It also appears automatically after the app sends its first request, which can take a few minutes.
3. **Flag.** Create a boolean flag with the key `instant-approval`. The variations are `true` and `false`. The off variation is `false`.
4. **Segment.** Create a segment `pilot-branches` with context kind `branch`. Add the branch keys that should be in the pilot. The demo uses `branch-001`.
5. **Targeting.** On the flag, add a rule: if the context is in the segment `pilot-branches`, serve `true`. Set the default rule to serve `false`. Turn targeting on.

### 3. Start the app

```bash
python app.py
```

It listens on port 5050. Open `http://localhost:5050/dashboard`.

## Try it

Send a payment from a pilot branch:

```bash
curl -X POST http://localhost:5050/authorize \
  -H "Content-Type: application/json" \
  -d '{"branch_id": "branch-001", "region": "London", "amount": 250}'
```

| Step | What to do | What you should see |
|---|---|---|
| Baseline | Flag targeting off | `MANUAL_REVIEW` for every payment |
| Pilot | Targeting on, `branch-001` in the segment | `AUTO_APPROVED` for amounts up to 1,000. `MANUAL_REVIEW` above that |
| Other branch | Use a branch key that is not in the segment | `MANUAL_REVIEW` |
| Observe | Open `/dashboard` and the LaunchDarkly Observability pages | Outcomes compared by flag value, plus the connection status panel |
| Rollback | Switch the flag off | The pilot branch returns to `MANUAL_REVIEW` within seconds, with no code change |

Set `LD_OBSERVABILITY=off` in `.env` to run without the observability plugin.

## Known limits

This is a demo, not production code.

- No authentication on `/authorize` or `/dashboard`.
- The decision store is a local SQLite file. It is not a tamper-evident audit trail.
- Payment errors are simulated (`SIMULATED_ERROR_RATE`), so the dashboard numbers are demo data.
- `debug=True` and `host="0.0.0.0"` are set for the demo. Turn both off outside it.
- **Biggest risk:** once the app has connected, a rollback made in LaunchDarkly can't reach it during a LaunchDarkly outage. A local override that forces manual review is the first thing I would build next.
- The custom `authorization-decision` event is sent but not yet turned into a LaunchDarkly metric, and traces are not yet confirmed. See [OBSERVE.md](quickapprove/OBSERVE.md).

## How AI was used

I built this with AI assistance (Claude). Two AI-written SDK calls were wrong and were caught: a method that doesn't exist in SDK 9.x, and an unverified context builder. The decision log is written in my own words, and records where I pushed back on the AI.
