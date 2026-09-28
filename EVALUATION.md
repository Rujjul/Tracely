# Controlled testing and measurement

## Reproducible scenario design

Each run records `scenario_id`, revision, seed, healthy start/end, fault start/end, expected service, true fault, telemetry volume, observed incidents, and investigator output. Run a healthy control in addition to faults. Avoid counting repeated runs of the same trace as independent real-world incidents.

| Scenario | Injected cause | Expected observable evidence |
|---|---|---|
| Healthy control | None | Ordinary latency; no incident |
| DB timeout | Slow or unavailable demo database | Increased 5xx; database timeout exceptions |
| Unhandled exception | Code path throws consistently | One exception fingerprint; 5xx concentration |
| Slow dependency | Fake dependency delays responses | Latency growth; only error incident if requests fail |
| Brief error burst | A few isolated failures | Suppressed by minimum count and persistence rules |

The first detector only handles sustained request failures. A slow dependency with successful responses tests dashboard latency, not a latency incident; add a separate latency rule only after defining its threshold and evaluation.

## Metrics

Use time windows or injected fault episodes as labeled units. For each episode, match a detector incident only when project, service, type, and an agreed time tolerance match. Report precision = TP/(TP+FP), recall = TP/(TP+FN), false alarms per healthy hour, and detection delay = first detection time minus fault start. If no positives occur, report a metric as undefined instead of zero. Track ingestion p95 and dropped events separately.

For root cause, write a rubric before examining model answers: exact cause, plausible broader category, unsupported, or abstention. Have a human check cited event IDs and whether they actually support each observation. Report exact match and broader-category rates separately, along with model latency and resource use. Do not convert a model's self-reported certainty into a calibrated accuracy claim.

## Procedure

1. Reset database or create a new evaluation project; record git revision and detector thresholds.
2. Generate at least 5 minutes of healthy request traffic, then inject a named fault, then recover.
3. Capture server-side timestamps and ground truth outside the investigator's prompt.
4. Export machine-readable incident outcomes and human judgments to a results file.
5. Repeat across several seeds and rates; include healthy hours to reveal false alarms.
6. Publish denominators, hardware, traffic rate, thresholds, and observed numbers. Label synthetic benchmarks clearly.

## First benchmark target

Start with 3 faults × 3 runs plus 3 healthy controls. Expand only after finding and fixing concrete failure modes. A production pilot requires permission from the application's owner, data minimization, deletion/retention behavior, and separate reliability testing.
