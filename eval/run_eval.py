import asyncio
import json
import statistics
import time
from pathlib import Path
from app.db import close_db, init_db
from app.graph import triage_graph
from app.schemas import ProfileInput


async def evaluate() -> None:
    await init_db()
    dataset = json.loads(Path("eval/dataset.json").read_text(encoding="utf-8"))
    semaphore = asyncio.Semaphore(3)

    async def eval_item(item: dict) -> dict:
        async with semaphore:
            profile_obj = ProfileInput(**item["profile"])
            start = time.perf_counter()
            res = await triage_graph.ainvoke(
                {
                    "profile": profile_obj,
                    "retrieved_policies": [],
                    "judgment": None,
                    "requires_human_review": False,
                }
            )
            elapsed_ms = (time.perf_counter() - start) * 1000
            judgment = res["judgment"]
            pred = judgment.risk_level if judgment is not None else "UNKNOWN"
            cited_policy = judgment.cited_policy_id if judgment is not None else None
            return {
                "handle": item["profile"]["handle"],
                "expected": item["expected_risk"],
                "predicted": pred,
                "cited_policy": cited_policy,
                "latency_ms": elapsed_ms,
            }

    results = await asyncio.gather(*(eval_item(row) for row in dataset))

    tp = sum(1 for r in results if r["expected"] == "HIGH" and r["predicted"] == "HIGH")
    fp = sum(1 for r in results if r["expected"] != "HIGH" and r["predicted"] == "HIGH")
    fn = sum(1 for r in results if r["expected"] == "HIGH" and r["predicted"] != "HIGH")
    exact_matches = sum(1 for r in results if r["expected"] == r["predicted"])

    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    accuracy = exact_matches / len(results) if results else 0.0
    latencies = [r["latency_ms"] for r in results]

    print("\n=== Brand-Risk RAG Agent Evaluation ===")
    print(f"Total Samples     : {len(results)}")
    print(f"Overall Accuracy  : {accuracy:.1%}")
    print(f"High-Risk Prec.   : {precision:.1%}")
    print(f"High-Risk Recall  : {recall:.1%}")
    print(f"Median Latency    : {statistics.median(latencies):.1f} ms")
    print("=======================================\n")

    for r in results:
        status = "PASS" if r["expected"] == r["predicted"] else "MISS"
        print(
            f"[{status}] {r['handle']:<28} | Expected: {r['expected']:<4} | "
            f"Pred: {r['predicted']:<4} | Policy: {str(r['cited_policy']):<8} | {r['latency_ms']:.0f}ms"
        )


async def main() -> None:
    try:
        await evaluate()
    finally:
        await close_db()


if __name__ == "__main__":
    asyncio.run(main())