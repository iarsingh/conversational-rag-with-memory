from convrag.ops import router as ops_router
from fastapi import FastAPI, HTTPException
from convrag.memory import ask

app = FastAPI()
app.include_router(ops_router, prefix="/v1")


@app.get("/healthz")
def healthz():
    return {"status": "ok"}


@app.post("/ask")
def post_ask(body: dict):
    try:
        return ask(body.get("session_id"), body.get("question", ""))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
