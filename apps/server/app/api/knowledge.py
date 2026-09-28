from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_session
from app.services.auth import AuthenticatedUser
from app.services.knowledge import KnowledgeService, MAX_KNOWLEDGE_BYTES, extract_document

router = APIRouter(prefix="/api/v1/knowledge", tags=["knowledge"])


class TextInput(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    content: str = Field(min_length=1, max_length=200000)


def knowledge(session: AsyncSession, current: AuthenticatedUser) -> KnowledgeService:
    return KnowledgeService(session, current.user.tenant_id)


@router.get("")
async def list_documents(session: Annotated[AsyncSession, Depends(get_session)], current: Annotated[AuthenticatedUser, Depends(get_current_user)]):
    return await knowledge(session, current).list()


@router.post("/text", status_code=201)
async def add_text(payload: TextInput, session: Annotated[AsyncSession, Depends(get_session)], current: Annotated[AuthenticatedUser, Depends(get_current_user)]):
    try:
        return await knowledge(session, current).create(payload.title, "TEXT", payload.content)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc


@router.post("/upload", status_code=201)
async def upload_document(session: Annotated[AsyncSession, Depends(get_session)], current: Annotated[AuthenticatedUser, Depends(get_current_user)],
    file: UploadFile = File(...), title: str = Form("")):
    data = await file.read(MAX_KNOWLEDGE_BYTES + 1)
    try:
        source_type, content = extract_document(file.filename or "", data)
        return await knowledge(session, current).create((title or file.filename or "文档")[:200], source_type, content)
    except (ValueError, UnicodeError) as exc:
        raise HTTPException(422, str(exc)) from exc
    except Exception as exc:
        raise HTTPException(422, "Document could not be parsed") from exc


@router.get("/search")
async def search_documents(q: str = Query(min_length=1, max_length=500), session: AsyncSession = Depends(get_session), current: AuthenticatedUser = Depends(get_current_user)):
    return await knowledge(session, current).search(q)


@router.get("/{document_id}")
async def get_document(document_id: str, session: Annotated[AsyncSession, Depends(get_session)], current: Annotated[AuthenticatedUser, Depends(get_current_user)]):
    result = await knowledge(session, current).get(document_id)
    if result is None:
        raise HTTPException(404, "Document not found")
    return result


@router.delete("/{document_id}", status_code=204)
async def delete_document(document_id: str, session: Annotated[AsyncSession, Depends(get_session)], current: Annotated[AuthenticatedUser, Depends(get_current_user)]):
    if not await knowledge(session, current).delete(document_id):
        raise HTTPException(404, "Document not found")
