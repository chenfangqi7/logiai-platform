import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.core.config import get_settings
from app.core.security import hash_password
from app.db.base import Base
from app.db.session import get_session
from app.main import app
from app.models.tenant import Tenant
from app.models.user import User


@pytest.fixture(autouse=True)
def clean_llm_env(monkeypatch):
    monkeypatch.setenv("LLM_API_KEY", "")
    monkeypatch.setenv("LLM_MODEL", "")
    monkeypatch.setenv("FALLBACK_LLM_API_KEY", "")
    monkeypatch.setenv("FALLBACK_LLM_MODEL", "")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
async def client():
    engine = create_async_engine("sqlite+aiosqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        first = Tenant(name="First", code="first")
        second = Tenant(name="Second", code="second")
        session.add_all([first, second])
        await session.flush()
        first_user = User(tenant_id=first.id, username="admin", email="first@example.test", password_hash=hash_password("correct-password"), role="admin")
        second_user = User(tenant_id=second.id, username="admin", email="second@example.test", password_hash=hash_password("second-password"), role="admin")
        session.add_all([first_user, second_user])
        await session.commit()
        first_id, second_id = first.id, second.id
        first_user_id = first_user.id

    async def override_session():
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_session] = override_session
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as test_client:
            yield test_client, first_id, second_id, first_user_id
    finally:
        app.dependency_overrides.clear()
        await engine.dispose()
