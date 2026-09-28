from __future__ import annotations

import hashlib
import io
import math
import re
import zipfile

from docx import Document
from openpyxl import load_workbook
from pypdf import PdfReader
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.domain import KnowledgeChunk, KnowledgeDocument
from app.repositories.knowledge import KnowledgeRepository

MAX_KNOWLEDGE_BYTES = 5 * 1024 * 1024
MAX_TEXT_CHARS = 200_000
VECTOR_DIMENSIONS = 1536


def text_embedding(text: str) -> list[float]:
    """Deterministic local character n-gram embedding for offline MVP retrieval."""
    normalized = text.lower()
    units = re.findall(r"[a-z0-9]+|[\u4e00-\u9fff]", normalized)
    grams = units + ["".join(units[index:index + 2]) for index in range(len(units) - 1)]
    vector = [0.0] * VECTOR_DIMENSIONS
    for gram in grams:
        digest = hashlib.blake2b(gram.encode("utf-8"), digest_size=8).digest()
        vector[int.from_bytes(digest, "big") % VECTOR_DIMENSIONS] += 1.0
    norm = math.sqrt(sum(item * item for item in vector))
    return [item / norm for item in vector] if norm else vector


def chunk_text(text: str, size: int = 500, overlap: int = 100) -> list[str]:
    cleaned = text.strip()
    return [cleaned[start:start + size] for start in range(0, len(cleaned), size - overlap) if cleaned[start:start + size]]


def extract_document(filename: str, data: bytes) -> tuple[str, str]:
    if len(data) > MAX_KNOWLEDGE_BYTES:
        raise ValueError("Document exceeds 5 MB")
    extension = filename.lower().rsplit(".", 1)[-1]
    if extension == "txt":
        content = data.decode("utf-8-sig")
        source_type = "TEXT"
    elif extension == "pdf":
        if not data.startswith(b"%PDF"):
            raise ValueError("Invalid PDF file")
        reader = PdfReader(io.BytesIO(data))
        if len(reader.pages) > 100:
            raise ValueError("PDF exceeds 100 pages")
        parts = []
        for page in reader.pages:
            parts.append(page.extract_text() or "")
            if sum(len(part) for part in parts) > MAX_TEXT_CHARS:
                raise ValueError("Document exceeds 200000 text characters")
        content = "\n".join(parts)
        source_type = "PDF"
    elif extension == "docx":
        if not data.startswith(b"PK"):
            raise ValueError("Invalid DOCX file")
        validate_office_archive(data)
        content = "\n".join(paragraph.text for paragraph in Document(io.BytesIO(data)).paragraphs)
        source_type = "DOCX"
    elif extension == "xlsx":
        if not data.startswith(b"PK"):
            raise ValueError("Invalid XLSX file")
        validate_office_archive(data)
        workbook = load_workbook(io.BytesIO(data), read_only=True, data_only=True)
        try:
            lines = []
            for sheet in workbook.worksheets:
                for row in sheet.iter_rows(values_only=True):
                    lines.append(" | ".join(str(value or "") for value in row))
                    if len(lines) > 5000 or sum(len(line) for line in lines) > MAX_TEXT_CHARS:
                        raise ValueError("Spreadsheet is too large")
            content = "\n".join(lines)
        finally:
            workbook.close()
        source_type = "XLSX"
    else:
        raise ValueError("Only TXT, PDF, DOCX and XLSX are supported")
    content = content.strip()
    if not content or len(content) > MAX_TEXT_CHARS:
        raise ValueError("Document must contain 1 to 200000 text characters")
    return source_type, content


def validate_office_archive(data: bytes) -> None:
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            files = archive.infolist()
            if len(files) > 2000 or sum(item.file_size for item in files) > 20 * 1024 * 1024:
                raise ValueError("Office archive is too large")
    except zipfile.BadZipFile as exc:
        raise ValueError("Invalid Office archive") from exc


class KnowledgeService:
    def __init__(self, session: AsyncSession, tenant_id: str) -> None:
        self.session = session
        self.tenant_id = tenant_id
        self.repo = KnowledgeRepository(session, tenant_id)

    async def create(self, title: str, source_type: str, content: str) -> dict:
        if not content.strip() or len(content) > MAX_TEXT_CHARS:
            raise ValueError("Content must contain 1 to 200000 characters")
        chunks = chunk_text(content)
        document = KnowledgeDocument(tenant_id=self.tenant_id, title=title, source_type=source_type,
            content=content, embedding=text_embedding(chunks[0]), extra_metadata={"chunk_count": len(chunks), "embedding_provider": "local-hash-v1"})
        self.session.add(document)
        await self.session.flush()
        self.session.add_all([KnowledgeChunk(tenant_id=self.tenant_id, document_id=document.id, chunk_index=index,
            content=chunk, embedding=text_embedding(chunk)) for index, chunk in enumerate(chunks)])
        await self.session.commit()
        return self.summary(document)

    def summary(self, document: KnowledgeDocument) -> dict:
        return {"id": document.id, "tenant_id": document.tenant_id, "title": document.title,
            "source_type": document.source_type, "metadata": document.extra_metadata,
            "created_at": document.created_at, "updated_at": document.updated_at}

    async def list(self) -> list[dict]:
        return [self.summary(item) for item in await self.repo.list()]

    async def get(self, document_id: str) -> dict | None:
        item = await self.repo.get(document_id)
        return {**self.summary(item), "content": item.content} if item else None

    async def delete(self, document_id: str) -> bool:
        item = await self.repo.get(document_id)
        if item is None:
            return False
        for chunk in await self.repo.chunks(document_id):
            await self.session.delete(chunk)
        await self.session.delete(item)
        await self.session.commit()
        return True

    async def search(self, query: str, limit: int = 3) -> list[dict]:
        vector = text_embedding(query)
        if not any(vector):
            return []
        rows = await self.repo.search(vector, limit)
        return [{"document_id": item.document_id, "content": item.content, "score": round(score, 3)} for item, score in rows]
