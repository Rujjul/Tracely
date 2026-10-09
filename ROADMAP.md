# Scope and next steps

## Plan A release boundary

Required: accounts, projects, hashed ingestion keys, validated event collection, log explorer, basic incident detector, exception grouping, evidence-based incident view, deterministic investigation, fault demo, controlled evaluation, Docker Compose, and documentation. The local LLM is optional for completion; it should improve explanations without changing detector truth.

## Added milestone: Phase 9.5

Before Phase 10, add a guided synthetic demo and an owner-scoped **Copy debugging brief** action using existing incident evidence. Include preview, redaction, citations, copy fallback, and instructions for focused debugging and fix verification. See `BUILD.md` for acceptance checks. This milestone is implemented locally; it does not add automated repairs or AI investigations.

## After the MVP

| Priority | Addition | Entry condition |
|---|---|---|
| 1 | Better onboarding and tiny Python helper/SDK | A separate developer struggles to send a first event |
| 2 | pgvector semantic error search | Keyword search demonstrably misses relevant cases |
| 3 | Deployment event ingestion and Git correlation | Real deployment metadata is available and correctly timestamped |
| 4 | Queue, batching, and worker scaling | Load test exposes ingestion or detector bottleneck |
| 5 | Multi-user teams, alert delivery, hosted service | Pilot users need access and operational support |
| 6 | ML anomaly models | Labeled baseline shows a measurable improvement opportunity |

Kafka, Kubernetes, billing, three language SDKs, and autonomous code fixes are outside the first release. A later README may claim external usage or benchmark results only after they happen and can be reproduced.

## Budget notes

Local open-source development can have ₹0 direct service charges, assuming existing laptop, power, storage, and internet. Local models use memory and compute; an RTX 3050 laptop may need a small model or CPU fallback. Hosted infrastructure, managed databases, paid LLM APIs, domains, and increased usage can incur costs. Check current provider terms before deployment; no free hosting tier is assumed by this plan.
