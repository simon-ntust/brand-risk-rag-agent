import time
from fastapi import FastAPI
from app.schemas import ProfileInput, TriageVerdict

app = FastAPI(title="Brand-Risk Intelligence & RAG Agent", version="0.2.0")


@app.get("/health")
async def health_check():
    return {"status": "ok"}


@app.post("/api/v1/triage", response_model=TriageVerdict)
async def triage_profile(payload: ProfileInput) -> TriageVerdict:
    start = time.perf_counter()

    # Temporary stub logic until LangGraph + pgvector is wired in Milestone 3
    is_suspicious = payload.brand.lower() in f"{payload.handle} {payload.bio}".lower()
    risk_level = "MEDIUM" if is_suspicious else "LOW"
    confidence = 0.75 if is_suspicious else 0.95
    requires_human_review = risk_level == "MEDIUM"

    latency_ms = round((time.perf_counter() - start) * 1000, 2)

    return TriageVerdict(
        brand=payload.brand,
        handle=payload.handle,
        risk_level=risk_level,
        confidence=confidence,
        requires_human_review=requires_human_review,
        cited_policy_id=None,
        retrieved_policies=[],
        reasoning="Preliminary triage check completed.",
        latency_ms=latency_ms,
    )