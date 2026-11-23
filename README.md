\# Brand-Risk Intelligence \& RAG Agent



!\[CI](https://github.com/simon-ntust/brand-risk-rag-agent/actions/workflows/ci.yml/badge.svg)



An asynchronous, policy-grounded Trust \& Safety triage service built with \*\*FastAPI\*\*, \*\*LangGraph\*\*, \*\*PostgreSQL (`pgvector`)\*\*, and \*\*Pydantic\*\*. Designed to filter analyst alert fatigue by automatically separating benign brand mentions from high-risk impersonation and phishing accounts.



\## Architecture



```text

POST /api/v1/triage (ProfileInput)

&#x20;       │

&#x20;       ▼

┌───────────────────┐   Verified domain / benign   ┌──────────────────┐

│  Node 1: Triage   │ ───────────────────────────► │ Early Exit (LOW) │

│  \& Fast Router    │                              └──────────────────┘

└───────────────────┘

&#x20;       │ Suspicious brand mention

&#x20;       ▼

┌───────────────────┐   HNSW Cosine Similarity     ┌──────────────────┐

│  Node 2: Policy   │ ◄──────────────────────────► │   PostgreSQL +   │

│  RAG Assessment   │   (Filtered by Brand ID)     │     pgvector     │

└───────────────────┘                              └──────────────────┘

&#x20;       │

&#x20;       ▼

Structured JSON Verdict (Pydantic) + Human-in-the-Loop Escalation Flag

```



\### Key Engineering Decisions

\- \*\*Conditional Graph Routing (`LangGraph`):\*\* Short-circuits verified official domains and non-impersonating mentions before invoking vector search or LLM generation, reducing token cost and tail latency.

\- \*\*Multi-Tenant Policy Isolation (`pgvector`):\*\* Uses an HNSW index with brand-level SQL filtering (`WHERE LOWER(brand) = LOWER($2)`) so client policies never bleed across tenants.

\- \*\*Strict I/O Contracts (`Pydantic`):\*\* Enforces schema validation on incoming profile payloads and constrains LLM outputs to deterministic risk tiers (`LOW`, `MEDIUM`, `HIGH`), confidence scores, and cited policy IDs.

\- \*\*Data Privacy:\*\* Uses simulated FinTech (`ApexBank`) and E-Commerce (`SwiftMart`) policy rules for safe public benchmarking.



\## Evaluation Benchmark (`eval/run\_eval.py`)



Evaluated concurrently (`asyncio`) across simulated phishing, unauthorized investment, legitimate merchant, and benign commentary profiles:



| Metric | Result |

| :--- | :--- |

| \*\*Dataset Size\*\* | 10 profiles (2 simulated enterprise brands) |

| \*\*Overall Accuracy\*\* | `100.0%` |

| \*\*High-Risk Precision\*\* | `100.0%` |

| \*\*High-Risk Recall\*\* | `100.0%` |

| \*\*Median Latency\*\* | `1,978 ms` |



\## Quickstart



```bash

\# 1. Configure environment

cp .env.example .env  # Add your API key and model settings



\# 2. Launch FastAPI + PostgreSQL (pgvector)

docker compose up --build -d



\# 3. Run automated evaluation benchmark

docker compose exec api python -m eval.run\_eval



\# 4. Run unit test suite

pytest -v

```

