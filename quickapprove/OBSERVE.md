# Observe evidence

I chose **Observe** over Iterate for this build. This file says what Observe means here, what the app does for it, how to check it in LaunchDarkly, and what is not proven.

## Why Observe, not Iterate

- Observe answers "what happened after I changed the flag?" Iterate answers "which version is better, with statistical confidence?"
- LaunchDarkly marks the `branch` context kind as not available for experiments and guarded rollouts, so Iterate would need a different context design.
- A few days of pilot traffic is too little for a valid experiment.
- A regulated bank needs a change that can be tied to an outcome and a name. That is audit evidence.

## What the app does for Observe

| Piece | Where | What it gives you |
|---|---|---|
| Custom event `authorization-decision` | `ld.track_decision()` | One event per payment, with outcome, amount, latency and error flag. `latency_ms` is also sent as the event's numeric value. |
| Observability plugin | `ld.enable_observability()` | Errors, logs, traces and metrics sent to LaunchDarkly. Flask requests are traced automatically. |
| OpenTelemetry metrics | `ld.track_decision()` | `quickapprove.decisions` (count) and `quickapprove.decision.latency_ms` (histogram), both tagged with `outcome` and `instant_approval` (the flag value). This is what lets you compare flag on and flag off inside LaunchDarkly. |
| Flag change history | LaunchDarkly, on the flag | Who changed the flag, when, and what changed. |
| Dashboard Observe panel | `/dashboard` | Whether the SDK is connected, whether the plugin is on, and how many events the app has queued. |
| Local comparison cards | `/dashboard` | Approval rate, error rate and latency by flag value, from a local SQLite file. |

The plugin is optional. If `launchdarkly-observability` is missing, or `LD_OBSERVABILITY=off`, the app still runs and still fails closed.

## Setup

```bash
cd quickapprove
source .venv/bin/activate
pip install -r requirements.txt
```

`.env` options (see `.env.example`):

- `LD_OBSERVABILITY=on` (default) or `off`
- `APP_VERSION=demo` is shown as the service version. A git SHA is best.

## How to check it in LaunchDarkly

Run the app, send some payments (see the README), then check each item. Tick them off as you confirm them.

- [ ] **Change history.** Open the `instant-approval` flag and its Change history. Switch the flag off and on. Each change should appear with your name and a time.
- [ ] **Contexts.** Open Contexts. The `branch` kind and the branch keys you sent should be listed.
- [ ] **Observability.** Open Observability, then Explore. Look for the `quickapprove` service. Check Traces for `POST /authorize` and Logs for the app's log lines.
- [ ] **Metrics.** Look for `quickapprove.decisions` in Observability. Group or filter by `instant_approval` to compare flag on and flag off.
- [ ] **Custom event.** Open Measurement, then Metrics, and create a custom metric on the event key `authorization-decision`. Use the numeric value option for average latency. Confirm the event is received.
- [ ] **Rollback story.** With traffic running, switch the flag off. The dashboard's flag-on count should stop growing and the flag-off count should start growing.

## Status of the evidence

| Item | Status |
|---|---|
| App starts with the plugin, fails closed, and the dashboard panel renders | Tested in a sandbox that could not reach LaunchDarkly |
| Flask requests are instrumented | Tested: the app object is built from the instrumented Flask class when the plugin is created first |
| Events and observability data arrive in LaunchDarkly | **Not confirmed.** Tick the checklist above on a machine that can reach LaunchDarkly |
| A LaunchDarkly metric built on `authorization-decision` | **Not built yet** |
| Observability available on this LaunchDarkly plan | **Not confirmed** |

## Things to know before using this in a bank

- **Data leaves the network.** The plugin exports over gRPC to `otel.observability.app.launchdarkly.com:4317`, in addition to the usual LaunchDarkly connections. A bank would need to allow that, and decide what logs and attributes may be sent. Branch keys and amounts are sent today.
- **Order matters.** The plugin patches Flask when it is created, so `ld.enable_observability()` must run before `from flask import Flask`. `app.py` does this and has a comment explaining why.
- **Package weight.** `launchdarkly-observability` pulls in many OpenTelemetry packages. The plugin needs SDK 9.12 or later and Python 3.10 or later.
- **Queued is not received.** The dashboard's event count is the number of calls to the SDK. It does not prove delivery.
- **The local numbers are demo data.** Processor errors are simulated and the store is a local SQLite file, not an audit trail.
