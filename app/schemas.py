from typing import Literal, Optional
from pydantic import BaseModel, Field


class ProfileInput(BaseModel):
    brand: str = Field(..., examples=["ApexBank"])
    handle: str = Field(..., examples=["@apexbank_vip_invest"])
    display_name: str = Field(..., examples=["ApexBank Wealth Advisory"])
    bio: str = Field(..., examples=["Official VIP stock signals! DM for 300% guaranteed returns."])
    external_url: Optional[str] = Field(default=None, examples=["https://t.me/apexbank_vip"])
    recent_posts: list[str] = Field(default_factory=list)


class PolicyMatch(BaseModel):
    policy_id: str
    title: str
    rule_text: str
    similarity: float


class LLMJudgment(BaseModel):
    risk_level: Literal["LOW", "MEDIUM", "HIGH"]
    confidence: float = Field(..., ge=0.0, le=1.0)
    cited_policy_id: Optional[str] = None
    reasoning: str


class TriageVerdict(BaseModel):
    brand: str
    handle: str
    risk_level: Literal["LOW", "MEDIUM", "HIGH"]
    confidence: float = Field(..., ge=0.0, le=1.0)
    requires_human_review: bool
    cited_policy_id: Optional[str] = None
    retrieved_policies: list[PolicyMatch] = Field(default_factory=list)
    reasoning: str
    latency_ms: float