import asyncpg
from pgvector.asyncpg import register_vector
from app.config import settings
from app.schemas import PolicyMatch

_pool: asyncpg.Pool | None = None

SEED_POLICIES = [
    {
        "policy_id": "APEX-01",
        "brand": "ApexBank",
        "title": "Unauthorized Investment & Guaranteed Return Claims",
        "rule_text": (
            "Accounts using the ApexBank name, logo, or VIP advisory branding to promote "
            "guaranteed returns, crypto/stock signals, or off-platform Telegram/WhatsApp groups "
            "are fraudulent impersonations and must be classified as HIGH risk."
        ),
    },
    {
        "policy_id": "APEX-02",
        "brand": "ApexBank",
        "title": "Fake Customer Support & Credential Phishing",
        "rule_text": (
            "Accounts claiming to offer ApexBank helpdesk, account recovery, or KYC verification "
            "via direct messages or non-official domains must be classified as HIGH risk."
        ),
    },
    {
        "policy_id": "APEX-03",
        "brand": "ApexBank",
        "title": "Unverified Brand Mention / Fan Commentary",
        "rule_text": (
            "Personal accounts mentioning ApexBank in casual commentary, news sharing, or "
            "everyday lifestyle bios without impersonating official staff or soliciting money "
            "are LOW risk."
        ),
    },
]


async def _init_connection(conn: asyncpg.Connection) -> None:
    await register_vector(conn)


async def init_db() -> None:
    global _pool
    bootstrap_conn = await asyncpg.connect(settings.database_url)
    try:
        await bootstrap_conn.execute("CREATE EXTENSION IF NOT EXISTS vector;")
    finally:
        await bootstrap_conn.close()

    _pool = await asyncpg.create_pool(
        dsn=settings.database_url,
        min_size=1,
        max_size=5,
        init=_init_connection,
    )

    async with _pool.acquire() as conn:
        await conn.execute(
            """
            CREATE TABLE IF NOT EXISTS brand_policies (
                policy_id TEXT PRIMARY KEY,
                brand TEXT NOT NULL,
                title TEXT NOT NULL,
                rule_text TEXT NOT NULL,
                embedding vector(1536) NOT NULL
            );
            """
        )

        count = await conn.fetchval("SELECT COUNT(*) FROM brand_policies;")
        if count == 0:
            from app.graph import embed_text

            for policy in SEED_POLICIES:
                text_to_embed = f"{policy['brand']} - {policy['title']}: {policy['rule_text']}"
                embedding = await embed_text(text_to_embed)
                await conn.execute(
                    """
                    INSERT INTO brand_policies (policy_id, brand, title, rule_text, embedding)
                    VALUES ($1, $2, $3, $4, $5)
                    ON CONFLICT (policy_id) DO NOTHING;
                    """,
                    policy["policy_id"],
                    policy["brand"],
                    policy["title"],
                    policy["rule_text"],
                    embedding,
                )


async def close_db() -> None:
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None


async def search_policies(
    brand: str, query_embedding: list[float], top_k: int = 3
) -> list[PolicyMatch]:
    if _pool is None:
        raise RuntimeError("Database connection pool is not initialized.")

    async with _pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT
                policy_id,
                title,
                rule_text,
                1 - (embedding <=> $1::vector) AS similarity
            FROM brand_policies
            WHERE LOWER(brand) = LOWER($2)
            ORDER BY embedding <=> $1::vector
            LIMIT $3;
            """,
            query_embedding,
            brand,
            top_k,
        )

    return [
        PolicyMatch(
            policy_id=row["policy_id"],
            title=row["title"],
            rule_text=row["rule_text"],
            similarity=round(float(row["similarity"]), 4),
        )
        for row in rows
    ]