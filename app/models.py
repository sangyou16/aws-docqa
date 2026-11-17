from pydantic import BaseModel, Field


class SearchRequest(BaseModel):
    query: str = Field(min_length=2, max_length=500)
    top_k: int = Field(default=3, ge=1, le=10)


class AskRequest(SearchRequest):
    use_llm: bool = Field(default=False, description="Summarise with Amazon Bedrock (needs ENABLE_BEDROCK=true).")


class PassageOut(BaseModel):
    id: str
    title: str
    source: str
    score: float
    text: str


class SearchResponse(BaseModel):
    query: str
    results: list[PassageOut]


class AskResponse(BaseModel):
    query: str
    answer: str
    mode: str  # "extractive" or "bedrock"
    citations: list[PassageOut]
