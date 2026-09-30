import os
import uuid

import httpx
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

N8N_UPLOAD_URL = os.getenv("N8N_UPLOAD_URL", "http://localhost:5678/webhook/upload-doc")
N8N_ASK_URL = os.getenv("N8N_ASK_URL", "http://localhost:5678/webhook/ask")
MAX_MB = int(os.getenv("MAX_UPLOAD_MB", "20"))
ALLOWED = {".pdf", ".txt", ".md", ".docx", ".csv", ".json"}

app = FastAPI(title="RAG Assistant")
app.mount("/static", StaticFiles(directory="static"), name="static")


class AskRequest(BaseModel):
    doc_id: str
    question: str


@app.get("/")
def home():
    return FileResponse("static/index.html")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/upload")
async def upload(file: UploadFile = File(...)):
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in ALLOWED:
        raise HTTPException(400, f"File type {ext or '?'} supported nahi hai. Allowed: {sorted(ALLOWED)}")

    content = await file.read()
    if len(content) > MAX_MB * 1024 * 1024:
        raise HTTPException(413, f"File {MAX_MB}MB se badi hai")

    doc_id = uuid.uuid4().hex  # har document ki unique ID
    try:
        async with httpx.AsyncClient(timeout=300) as client:
            r = await client.post(
                N8N_UPLOAD_URL,
                data={"doc_id": doc_id, "filename": file.filename},
                files={"data": (file.filename, content, file.content_type or "application/octet-stream")},
            )
        r.raise_for_status()
    except httpx.HTTPError as e:
        raise HTTPException(502, f"n8n upload workflow fail hua: {e}")

    return {"doc_id": doc_id, "filename": file.filename, "status": "indexed"}


@app.post("/ask")
async def ask(req: AskRequest):
    if not req.question.strip():
        raise HTTPException(400, "Sawal khali hai")
    try:
        async with httpx.AsyncClient(timeout=120) as client:
            r = await client.post(
                N8N_ASK_URL,
                json={"doc_id": req.doc_id, "question": req.question},
            )
        r.raise_for_status()
    except httpx.HTTPError as e:
        raise HTTPException(502, f"n8n chat workflow fail hua: {e}")

    try:
        data = r.json()
        if isinstance(data, list) and data:
            data = data[0]
        answer = data.get("answer") or data.get("output") or str(data)
    except ValueError:
        answer = r.text
    return {"answer": answer}
