from typing import TypedDict
from langgraph.graph import END, START, StateGraph
from openai import AsyncAzureOpenAI, AsyncOpenAI
from app.config import settings
from app.db import search_policies
from app.schemas import LLMJudgment, PolicyMatch, ProfileInput


def get_llm_client() -> AsyncOpenAI:
    if settings.azure_openai_endpoint:
        return AsyncAzureOpenAI(
            api_key=settings.openai_api_key,
            azure_endpoint=settings.azure_openai_endpoint,
            api_version=settings.azure_openai_api_version,
        )
    return AsyncOpenAI(
        api_key=settings.openai_api_key,
        base_url=settings.openai_base_url or None,
    )


async def embed_text(text: str) -> list[float]:
    client = get_llm_client()
    response = await client.embeddings.create(
        model=settings.embedding_model,
        input=text,
        dimensions=1536,
    )
    return response.data[0].embedding


class TriageState(TypedDict):
    profile: ProfileInput
    retrieved_policies: list[PolicyMatch]
    judgment: LLMJudgment | None
    requires_human_review: bool


async def retrieve_policies_node(state: TriageState) -> dict:
    profile = state["profile"]
    posts_text = " | ".join(profile.recent_posts) if profile.recent_posts else "None"
    query_text = (
        f"Brand: {profile.brand}\n"
        f"Handle: {profile.handle}\n"
        f"Display Name: {profile.display_name}\n"
        f"Bio: {profile.bio}\n"
        f"External URL: {profile.external_url or 'None'}\n"
        f"Recent Posts: {posts_text}"
    )
    query_embedding = await embed_text(query_text)
    matches = await search_policies(brand=profile.brand, query_embedding=query_embedding, top_k=3)
    return {"retrieved_policies": matches}


async def evaluate_risk_node(state: TriageState) -> dict:
    profile = state["profile"]
    policies = state["retrieved_policies"]

    policy_context = "\n\n".join(
        f"[{p.policy_id}] {p.title} (similarity={p.similarity}): {p.rule_text}"
        for p in policies
    ) or "No brand policies found."

    system_prompt = (
        "You are a senior Brand Risk & Trust-and-Safety analyst. "
        "Evaluate the social media profile strictly against the retrieved brand policies. "
        "Respond ONLY with valid JSON matching this schema:\n"
        '{"risk_level": "LOW" | "MEDIUM" | "HIGH", "confidence": float (0.0 to 1.0), '
        '"cited_policy_id": string or null, "reasoning": string}'
    )

    user_prompt = (
        f"### Retrieved Brand Policies\n{policy_context}\n\n"
        f"### Profile Under Review\n"
        f"- Brand: {profile.brand}\n"
        f"- Handle: {profile.handle}\n"
        f"- Display Name: {profile.display_name}\n"
        f"- Bio: {profile.bio}\n"
        f"- External URL: {profile.external_url or 'None'}\n"
        f"- Recent Posts: {profile.recent_posts}\n"
    )

    client = get_llm_client()
    completion = await client.chat.completions.create(
        model=settings.chat_model,
        temperature=0.0,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    )

    raw_json = completion.choices[0].message.content or "{}"
    judgment = LLMJudgment.model_validate_json(raw_json)
    return {"judgment": judgment}


async def apply_guardrails_node(state: TriageState) -> dict:
    judgment = state["judgment"]
    valid_ids = {p.policy_id for p in state["retrieved_policies"]}

    if judgment is None:
        fallback = LLMJudgment(
            risk_level="MEDIUM",
            confidence=0.0,
            cited_policy_id=None,
            reasoning="Model failed to produce a judgment; routed to human review.",
        )
        return {"judgment": fallback, "requires_human_review": True}

    if judgment.cited_policy_id and judgment.cited_policy_id not in valid_ids:
        judgment.cited_policy_id = None

    requires_human_review = (
        judgment.risk_level in ("MEDIUM", "HIGH") or judgment.confidence < 0.80
    )
    return {"judgment": judgment, "requires_human_review": requires_human_review}


def build_triage_graph():
    workflow = StateGraph(TriageState)
    workflow.add_node("retrieve_policies", retrieve_policies_node)
    workflow.add_node("evaluate_risk", evaluate_risk_node)
    workflow.add_node("apply_guardrails", apply_guardrails_node)

    workflow.add_edge(START, "retrieve_policies")
    workflow.add_edge("retrieve_policies", "evaluate_risk")
    workflow.add_edge("evaluate_risk", "apply_guardrails")
    workflow.add_edge("apply_guardrails", END)

    return workflow.compile()


triage_graph = build_triage_graph()