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

Run the app, send some payments (see the README), then check each item. Ticked items were confirmed in the Test environment on 23 Nov 2026.

- [x] **Change history.** Open the `instant-approval` flag and its Change history. Each switch of the flag appears with the name of the person who made it and a time.
- [x] **Contexts.** Open Contexts. The `branch` kind and the branch keys sent by the app are listed. (The kind can take a few minutes to appear the first time.)
- [x] **Logs.** Open Observability, then Explore, then Logs. The app's log lines arrive, including each `POST /authorize` call and "Started LaunchDarkly Client: OK".
- [x] **Metrics, flag on versus off.** Open Observability, then Explore, then Observability metrics. Filter on `metric_name` `quickapprove.decisions` and group by `instant_approval`. The chart splits into `true` and `false`. `quickapprove.decision.latency_ms` and `http.server.duration` are listed too. Note that the counts are metric export batches, not payment counts.
- [x] **Rollback story.** With the flag on, a pilot branch's payments of 250 GBP return `AUTO_APPROVED` and a 5,000 GBP payment returns `MANUAL_REVIEW`. After switching the flag off, all of them return `MANUAL_REVIEW`.
- [ ] **Traces.** Open Observability, then Explore, then Traces, and look for `POST /authorize` spans. The chart showed no spans when last checked, although a count of 20 appeared in the table beneath it. Not confirmed.
- [ ] **Custom event metric.** Open Measurement, then Metrics, create a custom metric on the event key `authorization-decision` (use the numeric value option for average latency), and confirm LaunchDarkly receives the event. Not done yet.

## Status of the evidence

| Item | Status |
|---|---|
| App starts with the plugin, fails closed, and the dashboard panel renders | Tested in a sandbox that could not reach LaunchDarkly, and on a Mac with a live key |
| Logs from the app arrive in LaunchDarkly | **Confirmed** |
| `quickapprove.decisions` arrives and splits by `instant_approval` | **Confirmed** |
| Flask requests are instrumented | Partly confirmed: `http.server.duration` metrics arrive. Traces are not confirmed |
| Observability works in this LaunchDarkly account | **Confirmed** for the Test environment. The plan tier is not known |
| A LaunchDarkly metric built on the `authorization-decision` event | **Not built yet** |
| Local override that forces manual review without LaunchDarkly | **Not built yet** (the first thing I would build next) |

So Observe is **partly** evidenced: flag changes can be tied to system behaviour in LaunchDarkly, but the custom event metric and traces are still open.

## Things to know before using this in a bank

- **Data leaves the network.** The plugin exports over gRPC to `otel.observability.app.launchdarkly.com:4317`, in addition to the usual LaunchDarkly connections. A bank would need to allow that, and decide what logs and attributes may be sent. Branch keys and amounts are sent today.
- **Order matters.** The plugin patches Flask when it is created, so `ld.enable_observability()` must run before `from flask import Flask`. `app.py` does this and has a comment explaining why.
- **Package weight.** `launchdarkly-observability` pulls in many OpenTelemetry packages. The plugin needs SDK 9.12 or later and Python 3.10 or later.
- **Queued is not received.** The dashboard's event count is the number of calls to the SDK. It does not prove delivery.
- **The local numbers are demo data.** Processor errors are simulated and the store is a local SQLite file, not an audit trail.
