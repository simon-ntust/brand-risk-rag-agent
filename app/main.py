import time
from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.db import close_db, init_db
from app.graph import triage_graph
from app.schemas import ProfileInput, TriageVerdict
from fastapi.responses import FileResponse



@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield
    await close_db()


app = FastAPI(
    title="Brand-Risk Intelligence & RAG Agent",
    version="0.3.0",
    lifespan=lifespan,
)


@app.get("/health")
async def health_check():
    return {"status": "ok"}

@app.get("/", include_in_schema=False)
async def serve_demo():
    return FileResponse("static/index.html")


@app.post("/api/v1/triage", response_model=TriageVerdict)
async def triage_profile(payload: ProfileInput) -> TriageVerdict:
    start = time.perf_counter()

    final_state = await triage_graph.ainvoke(
        {
            "profile": payload,
            "retrieved_policies": [],
            "judgment": None,
            "requires_human_review": False,
        }
    )

    judgment = final_state["judgment"]
    latency_ms = round((time.perf_counter() - start) * 1000, 2)

    return TriageVerdict(
        brand=payload.brand,
        handle=payload.handle,
        risk_level=judgment.risk_level,
        confidence=judgment.confidence,
        requires_human_review=final_state["requires_human_review"],
        cited_policy_id=judgment.cited_policy_id,
        retrieved_policies=final_state["retrieved_policies"],
        reasoning=judgment.reasoning,
        latency_ms=latency_ms,
    )