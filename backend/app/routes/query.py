"""Question-answering route backed by Hugging Face inference."""

import os
from functools import lru_cache

from fastapi import APIRouter, HTTPException, Query
from dotenv import load_dotenv
from huggingface_hub import InferenceClient
from langchain_core.embeddings import Embeddings
from langchain_core.documents import Document
from langchain_qdrant import QdrantVectorStore
from qdrant_client import QdrantClient, models

load_dotenv()

# Legacy OpenAI implementation (intentionally disabled). Never put API keys in source.
# from langchain_openai import OpenAIEmbeddings
# from openai import OpenAI
# openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
# embedding_model = OpenAIEmbeddings(
#     model="text-embedding-3-large", api_key=os.getenv("OPENAI_API_KEY")
# )

EMBEDDING_MODEL = os.getenv("HF_EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
# This model is listed by the Hugging Face Inference Providers router. Override
# it through HF_CHAT_MODEL if your enabled provider offers a different model.
CHAT_MODEL = os.getenv("HF_CHAT_MODEL", "meta-llama/Llama-3.1-8B-Instruct")
HF_PROVIDER = os.getenv("HF_PROVIDER", "auto")
QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
COLLECTION_NAME = os.getenv("QDRANT_COLLECTION", "sample_collection")
router = APIRouter(prefix="/query", tags=["query"])


@lru_cache
def get_hf_client() -> InferenceClient:
    token = os.getenv("HF_TOKEN")
    if not token:
        raise RuntimeError("HF_TOKEN is not configured.")
    return InferenceClient(token=token, provider=HF_PROVIDER)


class HuggingFaceEmbeddings(Embeddings):
    """LangChain adapter for Hugging Face Inference Provider embeddings."""

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self.embed_query(text) for text in texts]

    def embed_query(self, text: str) -> list[float]:
        embedding = get_hf_client().feature_extraction(text, model=EMBEDDING_MODEL)
        return embedding.tolist() if hasattr(embedding, "tolist") else list(embedding)


@lru_cache
def get_vector_db() -> QdrantVectorStore:
    return QdrantVectorStore.from_existing_collection(
        embedding=HuggingFaceEmbeddings(),
        collection_name=COLLECTION_NAME,
        url=QDRANT_URL,
    )


@lru_cache
def get_qdrant_client() -> QdrantClient:
    return QdrantClient(url=QDRANT_URL)


def page_label(metadata: dict) -> str:
    """Prefer the page number printed in the PDF over its zero-based index."""
    return str(metadata.get("page_label", metadata.get("page", "unknown")))


def keyword_matches(question: str) -> list[Document]:
    """Find exact title/keyword mentions that semantic search may rank too low."""
    if "page" not in question.lower():
        return []

    # For questions such as "what page is <title>?", retain only the title.
    keywords = question.lower().replace("what page no. is", "").replace("what page is", "").strip()
    if len(keywords) < 4:
        return []
    points, _ = get_qdrant_client().scroll(
        collection_name=COLLECTION_NAME,
        scroll_filter=models.Filter(
            must=[
                models.FieldCondition(
                    key="page_content",
                    match=models.MatchText(text=keywords),
                )
            ]
        ),
        limit=3,
        with_payload=True,
        with_vectors=False,
    )
    return [
        Document(
            page_content=point.payload["page_content"],
            metadata=point.payload.get("metadata", {}),
        )
        for point in points
        if point.payload and "page_content" in point.payload
    ]


@router.post("/")
def query(question: str = Query(..., min_length=1)):
    """Answer a question from the indexed document, citing its source page."""
    try:
        exact_matches = keyword_matches(question)
        semantic_matches = get_vector_db().similarity_search(query=question, k=4)
        search_results = exact_matches + semantic_matches
        context = " ".join(
            f"[Page {page_label(result.metadata)}] {result.page_content}"
            for result in search_results
        )
        system_prompt = f"""You are a helpful assistant that answers questions based on the provided context.
If the context does not contain the answer, respond with "I don't know."

Also include the page number of the context in your answer if applicable.

Context:
{context}"""
        completion_options: dict = {
            "messages": [

                {"role": "system", "content": system_prompt},
                {"role": "user", "content": question},
            ],
            "max_tokens": 512,
        }
        completion_options["model"] = CHAT_MODEL
        response = get_hf_client().chat_completion(**completion_options)
        return {"question": question, "answer": response.choices[0].message.content}

        # Legacy completion call (intentionally disabled):
        # response = openai_client.chat.completions.create(
        #     model="gpt-5",
        #     messages=[
        #         {"role": "system", "content": system_prompt},
        #         {"role": "user", "content": question},
        #     ],
        # )
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Hugging Face request failed: {exc}") from exc
