from fastapi import FastAPI

app = FastAPI(title="Brand-Risk Intelligence & RAG Agent", version="0.1.0")


@app.get("/health")
async def health_check():
    return {"status": "ok"}