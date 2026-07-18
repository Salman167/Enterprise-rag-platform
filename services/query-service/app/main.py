"""Query Service — LangGraph RAG orchestration with multi-language prompts."""

from contextlib import asynccontextmanager
from typing import TypedDict
from uuid import UUID, uuid4

import httpx
from fastapi import FastAPI, HTTPException
from langgraph.graph import END, StateGraph
from openai import OpenAI

from enterprise_rag_common.config import settings
from enterprise_rag_common.enums import AuditAction, SupportedLocale
from enterprise_rag_common.llm import has_valid_openai_key
from enterprise_rag_common.models import HealthResponse, QueryResponse

SERVICE_NAME = "query-service"

SYSTEM_PROMPTS = {
    "en": (
        "You are an enterprise knowledge assistant for EU/MENA organizations. "
        "Answer ONLY from the provided context. Cite sources. "
        "If unsure, say you don't know. Never fabricate information."
    ),
    "ar": (
        "أنت مساعد معرفة مؤسسي للمنظمات في أوروبا والشرق الأوسط. "
        "أجب فقط من السياق المقدم. اذكر المصادر. "
        "إذا لم تكن متأكداً، قل أنك لا تعرف. لا تختلق معلومات."
    ),
    "fr": (
        "Vous êtes un assistant de connaissances d'entreprise. "
        "Répondez UNIQUEMENT à partir du contexte fourni. Citez les sources."
    ),
    "de": (
        "Sie sind ein Unternehmens-Wissensassistent. "
        "Antworten Sie NUR basierend auf dem bereitgestellten Kontext. Zitieren Sie Quellen."
    ),
}


class RAGState(TypedDict):
    question: str
    locale: str
    context: str
    retrieval_results: list
    answer: str


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.http = httpx.AsyncClient(timeout=120.0)
    app.state.openai = OpenAI(api_key=settings.openai_api_key, base_url=settings.openai_base_url)
    app.state.graph = _build_graph(app)
    yield
    await app.state.http.aclose()


def _build_graph(app: FastAPI):
    async def retrieve(state: RAGState) -> RAGState:
        resp = await app.state.http.post(
            f"{settings.retrieval_service_url}/search",
            json={
                "question": state["question"],
                "top_k": 5,
                "hybrid": True,
                "locale": state["locale"],
            },
        )
        resp.raise_for_status()
        results = resp.json()["results"]
        context = "\n\n---\n\n".join(
            f"[Source: {r['filename']} | chunk {r['chunk_index']}]\n{r['text']}" for r in results
        )
        return {**state, "retrieval_results": results, "context": context}

    def generate(state: RAGState) -> RAGState:
        locale = state["locale"]
        system = SYSTEM_PROMPTS.get(locale, SYSTEM_PROMPTS["en"])

        if not has_valid_openai_key():
            answer = (
                f"[Dev mode — no valid LLM key] Based on {len(state['retrieval_results'])} retrieved chunks:\n"
                f"{state['context'][:800]}"
            )
            return {**state, "answer": answer}

        try:
            response = app.state.openai.chat.completions.create(
                model=settings.llm_model,
                messages=[
                    {"role": "system", "content": system},
                    {
                        "role": "user",
                        "content": f"Context:\n{state['context']}\n\nQuestion: {state['question']}",
                    },
                ],
                temperature=0.1,
            )
            answer = response.choices[0].message.content or ""
        except Exception:
            answer = (
                f"[Dev mode — LLM unavailable] Based on {len(state['retrieval_results'])} retrieved chunks:\n"
                f"{state['context'][:800]}"
            )
        return {**state, "answer": answer}

    graph = StateGraph(RAGState)
    graph.add_node("retrieve", retrieve)
    graph.add_node("generate", generate)
    graph.set_entry_point("retrieve")
    graph.add_edge("retrieve", "generate")
    graph.add_edge("generate", END)
    return graph.compile()


app = FastAPI(title="Query Service", version="0.1.0", lifespan=lifespan)


@app.get("/health", response_model=HealthResponse)
def health():
    return HealthResponse(service=SERVICE_NAME, data_region=settings.data_region)


@app.post("/query", response_model=QueryResponse)
async def query(payload: dict):
    question = payload.get("question", "")
    locale = payload.get("locale") or settings.default_locale
    include_citations = payload.get("include_citations", True)

    if not question:
        raise HTTPException(status_code=400, detail="question required")

    state: RAGState = {
        "question": question,
        "locale": locale,
        "context": "",
        "retrieval_results": [],
        "answer": "",
    }

    result = await app.state.graph.ainvoke(state)
    query_id = uuid4()

    citations = []
    if include_citations and result["retrieval_results"]:
        cite_resp = await app.state.http.post(
            f"{settings.citation_service_url}/build",
            json={"results": result["retrieval_results"]},
        )
        if cite_resp.status_code == 200:
            citations = cite_resp.json().get("citations", [])

    return QueryResponse(
        answer=result["answer"],
        citations=citations,
        locale=SupportedLocale(locale) if locale in SupportedLocale._value2member_map_ else SupportedLocale.EN,
        query_id=query_id,
        model=settings.llm_model,
    )
