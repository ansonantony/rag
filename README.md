# Hugging Face RAG API

A FastAPI retrieval-augmented generation (RAG) service. It indexes `app/data/sample.pdf` into Qdrant, retrieves the most relevant passages for a question, and asks a Hugging Face chat model to answer only from those passages.

## Flow

```text
PDF -> PyPDFLoader -> text chunks -> Hugging Face embeddings -> Qdrant
                                                           |
POST /query/?question=... -> query embedding -> similarity search -> context
                                                                  -> Hugging Face chat model -> answer + page reference
```

The embedding model defaults to `sentence-transformers/all-MiniLM-L6-v2` and the chat model defaults to `meta-llama/Llama-3.1-8B-Instruct`. Use the same embedding model while indexing and querying, otherwise Qdrant vector search will not work correctly.

## Requirements

- Python 3.10 or later
- Docker (for Qdrant)
- A Hugging Face access token with permission to use Inference Providers

Install the existing project dependencies plus the Hugging Face migration dependencies:

```bash
pip install -r requirements.txt -r requirements-huggingface.txt
```

## Configuration

Create a `.env` file in the project root:

```env
HF_TOKEN=hf_your_token_here
# Optional: select another model offered by your enabled provider.
HF_CHAT_MODEL=meta-llama/Llama-3.1-8B-Instruct
HF_PROVIDER=auto
HF_EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
QDRANT_URL=http://localhost:6333
QDRANT_COLLECTION=sample_collection
```

`HF_CHAT_MODEL`, `HF_PROVIDER`, `HF_EMBEDDING_MODEL`, `QDRANT_URL`, and `QDRANT_COLLECTION` are optional. With `HF_PROVIDER=auto`, Hugging Face selects an available provider according to your Inference Provider preferences. Do not commit `.env` or API tokens.

### Enable a Hugging Face inference provider

The Hugging Face router requires a provider that supports your selected model. In Hugging Face **Settings → Inference Providers**, enable a provider and add credits or connect that provider's API key if prompted. Then restart the API. A `model_not_supported` response means the model is unavailable through your enabled providers; set `HF_CHAT_MODEL` to an available model in the same settings page. The provider catalog for this token currently reports no free chat models, so this account-side setup is required before a chat request can succeed.

## Run

Start Qdrant:

```bash
docker compose up -d
```

Index the PDF. Run this whenever the PDF, chunking settings, collection name, or embedding model changes:

```bash
python -m app.index
```

Start the API from the repository root:

```bash
uvicorn app.main:app --reload
```

Open the interactive API documentation at `http://127.0.0.1:8000/docs`.

## Query the API

```bash
curl -X POST "http://127.0.0.1:8000/query/?question=What%20does%20the%20document%20say%3F"
```

Example response:

```json
{
  "question": "What does the document say?",
  "answer": "The answer from the retrieved context (Page 1)."
}
```

The route returns `503` if `HF_TOKEN` is missing and `502` when Qdrant or Hugging Face inference cannot complete the request.

## OpenAI migration note

The previous OpenAI imports and call patterns remain commented in `app/routes/query.py` and `app/index.py` as a reference only. The active implementation uses Hugging Face for both embeddings and chat completion. Credentials are read from environment variables; no secret is stored in source code.
