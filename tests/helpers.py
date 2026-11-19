"""测试用种子数据构造。"""

from __future__ import annotations

from decimal import Decimal

from workbench.core.crypto import encrypt
from workbench.core.passwords import hash_password
from workbench.db.base import utcnow
from workbench.db.models import (
    AdminCredential,
    AnalysisSession,
    ModelBinding,
    ProjectContext,
    ProviderConfig,
)


async def seed_admin(sessionmaker, password: str) -> None:
    async with sessionmaker() as db:
        db.add(
            AdminCredential(
                credential_id=1,
                algorithm="argon2id",
                password_hash=hash_password(password),
                updated_at=utcnow(),
            )
        )
        await db.commit()


async def seed_project(sessionmaker, name: str = "支付中心") -> int:
    async with sessionmaker() as db:
        row = ProjectContext(name=name, name_key=name.casefold())
        db.add(row)
        await db.commit()
        return row.project_id


async def seed_provider(
    sessionmaker,
    *,
    name: str = "OpenAI",
    protocol: str = "openai_compatible",
    base_url: str = "https://api.example.com/v1",
    enabled: bool = True,
    ciphertext: str | None = None,
) -> int:
    async with sessionmaker() as db:
        row = ProviderConfig(
            name=name,
            protocol=protocol,
            base_url=base_url,
            api_key_ciphertext=ciphertext or encrypt("sk-test-key", key=bytes(range(32))),
            enabled=enabled,
        )
        db.add(row)
        await db.commit()
        return row.provider_id


async def seed_model(
    sessionmaker,
    provider_id: int,
    *,
    model_name: str = "gpt-4.1",
    display_name: str = "GPT-4.1",
    enabled: bool = True,
    temperature: str = "0.70",
    max_tokens: int = 4096,
) -> int:
    async with sessionmaker() as db:
        row = ModelBinding(
            provider_id=provider_id,
            model_name=model_name,
            model_name_key=model_name.casefold(),
            display_name=display_name,
            default_temperature=Decimal(temperature),
            default_max_tokens=max_tokens,
            enabled=enabled,
        )
        db.add(row)
        await db.commit()
        return row.model_id


async def seed_session(
    sessionmaker,
    *,
    project_id: int,
    model_id: int,
    title: str = "排查一次失败",
    status: str = "in_progress",
    entrance_key: str = "case-library",
) -> int:
    async with sessionmaker() as db:
        now = utcnow()
        row = AnalysisSession(
            project_id=project_id,
            entrance_key=entrance_key,
            title=title,
            status=status,
            model_id=model_id,
            created_at=now,
            updated_at=now,
        )
        if status != "in_progress":
            row.closed_at = now
        db.add(row)
        await db.commit()
        return row.session_id


def make_app(settings, database, **kwargs):  # noqa: ANN001, ANN003, ANN201
    from workbench.main import create_app

    return create_app(settings=settings, database=database, **kwargs)


def build_client(app, *, base_url: str = "http://testserver"):  # noqa: ANN001, ANN201
    import httpx

    transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
    return httpx.AsyncClient(transport=transport, base_url=base_url)


async def seed_session_graph(sessionmaker) -> tuple[int, int, int]:
    project_id = await seed_project(sessionmaker)
    provider_id = await seed_provider(sessionmaker)
    model_id = await seed_model(sessionmaker, provider_id)
    session_id = await seed_session(sessionmaker, project_id=project_id, model_id=model_id)
    return project_id, model_id, session_id
