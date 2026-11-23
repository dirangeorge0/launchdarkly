> **DRAFT.** One answer is still to be written by Diran in his own words: the reason for choosing Observe (marked below). Everything else is his answers.

# Decision log

Written by: Diran George

## 1. Three design decisions and their trade-offs

1. **Fail-closed default.** This is a fail-safe framework. If LaunchDarkly can't switch instant approval on for a branch, the payment goes to manual review, where a person approves or rejects it. The cost: when fail-closed triggers, every payment slows down because it needs manual review. The gap: if an outage starts after the app has already connected, a rollback made in LaunchDarkly wouldn't take effect by default.
2. **Splitting the rollout from the money rule.** Different owners control each. Product and Engineering own the rollout in LaunchDarkly. The Compliance Officer owns the £1,000 limit, which is hard-coded, so nobody without access to the codebase can change it. That protects compliance, regulatory and financial risk. The cost: changing the limit means a Product or Engineering resource has to find it in the codebase, edit it, review it and push it. That is process driven and takes longer than a rollout change in LaunchDarkly, which takes seconds or minutes.
3. **Branch-level targeting.** The business owns branches operationally, which reduces complexity in monitoring and observability. The cost: I can't target individual customers or run experiments on them.

## 2. An AI suggestion I tried and then reverted

Candidly, there was no clean rejection. When I was testing the branch context, it didn't show up in LaunchDarkly immediately, so the AI suggested switching the context kind from `branch` to `user`. I made the change and tested it. A few minutes later the `branch` context appeared. I reverted to `branch`, because calling a branch a "user" would have muddied the demo. The lesson: verify the cause before changing the design.

## 3. What I would change for a 50-person startup

I would move the transaction limit into the LaunchDarkly flag. One owner could then manage both the rollout and the money rule, which speeds up decisions and deployment. The risk: someone could change the limit with no code review. I would mitigate that with role-based access, and with a short list of allowed limits on the flag, which prevents typos.

## 4. The biggest risk if a customer copied this into production

I couldn't roll back changes to rules, targeting, contexts or flags during a LaunchDarkly outage. The pilot would keep auto-approving payments and couldn't be switched off. The likelihood is low, but the impact is high. Two things help: the hard-coded limit, and targeting by branch, so the financial impact is capped per transaction. The first fix I would build is a local override environment variable in the app, which lets the bank force every payment to manual review without depending on LaunchDarkly.

## 5. What I would build next with four more hours

I would prioritise two updates within 4 hours and build a third for resilience.

1. **Local override.** An environment variable in the app that lets the bank force all payments to manual review, which acts as the rollback.
2. **Stream alert.** An alert if LaunchDarkly's streaming service becomes unavailable, so the bank can decide whether to flip the override.
3. **Relay Proxy.** A resilient Relay Proxy inside the bank's network for the app to connect to. It needs fewer outbound connections, and if the app restarts during a LaunchDarkly outage it can still get flag values from the proxy.

## Observe versus Iterate

Chosen: **Observe**. LaunchDarkly marks the `branch` context kind as not available for experiments and guarded rollouts, so Iterate would need a different context design, and a few days of pilot traffic is too little for a valid result. Evidence and status: see [OBSERVE.md](OBSERVE.md).

**My reason for choosing Observe, in my own words:** [Diran to write 2 to 3 sentences here]

## Appendix: all ten build decisions and my reasons

| # | Decision | My reason |
|---|---|---|
| 1 | Fail-closed default | A fail-safe framework. If a payment can't be auto-approved through LaunchDarkly, it goes to manual review. Cost: every payment slows down. Gap: a rollback made during an outage after connection doesn't take effect by default. |
| 2 | Two separate decisions (rollout in LaunchDarkly, payment rule in the app) | Different owners: Product/Engineering own the rollout, the Compliance Officer owns the money rule. Cost: a limit change is process driven, a rollout change takes seconds or minutes. |
| 3 | £1,000 limit hard-coded | It protects compliance, because nobody without access to the codebase can change the limit. Cost: a change needs a codebase change, which takes significantly longer than a rollout change. |
| 4 | Branch-level targeting | Easier because the business owns branches operationally. Cost: no per-customer targeting or experiments. |
| 5 | Observe, not Iterate | The dashboard shows authorisation and decisioning, and compares approval rates, errors and latency with the flag on versus off. That gives Product/Engineering insight into the risk of a deployment. |
| 6 | Server-side SDK | A server-side key keeps decisions and potential secrets off the client and on the server. |
| 7 | Default rule serves false, only the segment rule serves true | The default block rule stops a feature being exposed to contexts it shouldn't be. |
| 8 | Local SQLite store | Speed of prototyping. |
| 9 | Simulated payment errors | I want to prove the different scenarios the flag can permit or deny. |
| 10 | Test environment only | Simulated proof points for CI/CD without pushing straight to production. |
