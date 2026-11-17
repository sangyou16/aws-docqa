import json
import time
import uuid

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from mangum import Mangum

from app.answer import NO_ANSWER, bedrock_answer, bedrock_enabled, extractive_answer
from app.corpus import Passage, get_retriever
from app.models import AskRequest, AskResponse, PassageOut, SearchRequest, SearchResponse

app = FastAPI(title="AWS Doc Q&A", version="1.0.0")


@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.perf_counter()
    ctx = request.scope.get("aws.context")  # set by Mangum on Lambda
    request.state.request_id = getattr(ctx, "aws_request_id", None) or str(uuid.uuid4())
    request.state.result_count = None
    request.state.error = None
    try:
        response = await call_next(request)
    except Exception as exc:  # unhandled -> 500, still logged
        request.state.error = f"{type(exc).__name__}: {exc}"
        response = JSONResponse({"detail": "Internal server error"}, status_code=500)
    if response.status_code >= 400 and not request.state.error:
        request.state.error = f"http_{response.status_code}"
    # One JSON line per request; Lambda ships stdout to CloudWatch Logs as-is.
    print(json.dumps({
        "request_id": request.state.request_id,
        "endpoint": request.url.path,
        "method": request.method,
        "status": response.status_code,
        "latency_ms": round((time.perf_counter() - start) * 1000, 2),
        "result_count": request.state.result_count,
        "error": request.state.error,
    }), flush=True)
    response.headers["x-request-id"] = request.state.request_id
    return response


def _out(p: Passage, score: float) -> PassageOut:
    return PassageOut(id=p.id, title=p.title, source=p.source, score=round(score, 4), text=p.text)


@app.get("/health")
def health():
    return {"status": "ok", "passages": len(get_retriever().passages)}


@app.post("/search", response_model=SearchResponse)
def search(body: SearchRequest, request: Request):
    hits = get_retriever().search(body.query, body.top_k)
    request.state.result_count = len(hits)
    return SearchResponse(query=body.query, results=[_out(p, s) for p, s in hits])


@app.post("/ask", response_model=AskResponse)
def ask(body: AskRequest, request: Request):
    if body.use_llm and not bedrock_enabled():
        raise HTTPException(400, "use_llm requires the ENABLE_BEDROCK=true deployment flag")
    hits = get_retriever().search(body.query, body.top_k)
    answer, used = extractive_answer(body.query, hits)
    mode = "extractive"
    if body.use_llm and hits:
        try:
            answer, used, mode = bedrock_answer(body.query, [p for p, _ in hits]), [p for p, _ in hits], "bedrock"
        except Exception as exc:  # fall back rather than fail the request
            request.state.error = f"bedrock_failed: {type(exc).__name__}"
    scores = {p.id: s for p, s in hits}
    request.state.result_count = len(used)
    return AskResponse(query=body.query, answer=answer or NO_ANSWER, mode=mode,
                       citations=[_out(p, scores[p.id]) for p in used])


handler = Mangum(app, lifespan="off")  # Lambda entry point: app.main.handler
