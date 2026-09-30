# RAG Assistant

A simple web app where you upload a document and ask questions about it.

The app is built with **FastAPI**. The RAG part (chunking, embeddings, vector search, LLM) runs in an **n8n** workflow.

## How it works

```
Browser  ->  FastAPI  ->  n8n workflow  ->  Supabase (pgvector) + LLM
```

1. You upload a file in the browser.
2. FastAPI gives the file a unique `doc_id` and sends it to n8n.
3. n8n splits the file into chunks, creates embeddings (Google Gemini), and stores them in Supabase.
4. You ask a question. FastAPI sends it to n8n with the same `doc_id`.
5. The n8n AI Agent searches only the chunks of that document and answers using the LLM (Groq).

## Tech stack

- Python 3.12, FastAPI, [uv](https://docs.astral.sh/uv/)
- n8n (workflow automation)
- Supabase with pgvector (vector database)
- Google Gemini (embeddings)
- Groq (LLM)
- Postgres (chat memory)
- Docker (optional)

## Requirements

- Python 3.12+
- `uv` installed
- A running n8n instance with the RAG workflow imported and **published**
- A Supabase project with a `documents` table and the `match_documents` function

## Setup

### 1. Set up n8n

Import the workflow from `n8n/workflow.json` (if included) and set your own credentials for Supabase, Google Gemini, Groq, and Postgres.

The workflow needs two Webhook nodes:

| Webhook path  | Method | Purpose                       |
|---------------|--------|-------------------------------|
| `upload-docs` | POST   | Receives the file and `doc_id` |
| `ask`         | POST   | Receives `doc_id` and `question` |

Important settings:

- Both Webhook nodes: **Respond** = "Using 'Respond to Webhook' Node".
- Upload flow: Default Data Loader must add the metadata `doc_id`, and use a Recursive Character Text Splitter.
- Ask flow: AI Agent prompt is `{{ $json.body.question }}`. The Supabase retrieval tool must use a metadata filter on `doc_id`. Postgres Chat Memory uses `doc_id` as the session ID.
- Click **Publish** after every change.

### 2. Configure the app

Copy the example environment file and edit it:

```bash
cp .env.example .env
```

| Variable          | Description                                   | Example                                       |
|-------------------|-----------------------------------------------|-----------------------------------------------|
| `N8N_UPLOAD_URL`  | n8n upload webhook (production URL)           | `http://localhost:5678/webhook/upload-docs`   |
| `N8N_ASK_URL`     | n8n ask webhook (production URL)              | `http://localhost:5678/webhook/ask`           |
| `MAX_UPLOAD_MB`   | Max upload size in MB (optional, default 20)  | `20`                                          |

### 3. Run the app

```bash
uv sync
uv run --env-file .env uvicorn main:app --reload
```

Open http://localhost:8000

### Run with Docker (optional)

```bash
docker build -t rag-app .
docker run -p 8000:8000 --env-file .env rag-app
```

If n8n runs on your host machine, use `host.docker.internal` instead of `localhost` in the URLs.

## API

### `POST /upload`

Upload a document (form-data, field name `file`).

Supported types: `.pdf`, `.txt`, `.md`, `.docx`, `.csv`, `.json`

Response:

```json
{ "doc_id": "a1b2c3...", "filename": "notes.pdf", "status": "indexed" }
```

### `POST /ask`

```json
{ "doc_id": "a1b2c3...", "question": "What is this document about?" }
```

Response:

```json
{ "answer": "..." }
```

### `GET /health`

Returns `{ "status": "ok" }`.

## Project structure

```
rag-app/
├── main.py            # FastAPI app
├── static/index.html  # Simple web UI
├── pyproject.toml     # Dependencies (uv)
├── Dockerfile
├── .env.example
└── README.md
```

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `404` from n8n | The workflow is not published, or the webhook path is wrong. Use the **Production URL** (`/webhook/...`, not `/webhook-test/...`). |
| `500 Unused Respond to Webhook node` | Set **Respond** to "Using 'Respond to Webhook' Node" on the Webhook node, then publish. |
| `500` on `/ask` | Open n8n **Executions**, find the red node, and read its error. Common causes: missing prompt in the AI Agent, empty memory session ID, or an LLM rate limit. |
| `Name or service not known` | The URL in your env vars is wrong or outdated. Restart the app after changing env vars. |
| `Address already in use` | Another process uses port 8000. Stop it or run with `--port 8001`. |

## Security notes

- Never commit `.env` or API keys.
- There is no login yet. Do not expose this app publicly without adding authentication.
- Do not use temporary tunnel URLs in production.

## Roadmap

- [ ] Source citations in answers
- [ ] Authentication
- [ ] Evaluation dataset
- [ ] Website URL ingestion
