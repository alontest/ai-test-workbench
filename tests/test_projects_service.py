"""项目上下文服务。用例名带 TC 编号。"""

from __future__ import annotations

import pytest
from sqlalchemy import func, select

from workbench.db.models import ProjectContext
from workbench.services import projects
from workbench.services.errors import DomainError


async def _count(sessionmaker) -> int:  # noqa: ANN001
    async with sessionmaker() as db:
        return await db.scalar(select(func.count()).select_from(ProjectContext))


@pytest.mark.asyncio
async def test_tc013_create_project_and_duplicate(database) -> None:
    sm = database.sessionmaker
    view = await projects.create(name="支付中心")
    assert set(view) == {
        "projectId",
        "name",
        "repoUrl",
        "techStack",
        "requirementSource",
        "notes",
        "createdAt",
        "updatedAt",
    }
    assert view["projectId"] > 0
    assert view["name"] == "支付中心"

    async with sm() as db:
        row = await db.get(ProjectContext, view["projectId"])
        assert row.name_key == "支付中心".casefold()

    for duplicate in ("  支付中心  ", "支付中心"):
        with pytest.raises(DomainError) as err:
            await projects.create(name=duplicate)
        assert err.value.code == "project_name_duplicate"
        assert err.value.status_code == 409
        assert err.value.details[0]["field"] == "name"

    assert await _count(sm) == 1

    upper = await projects.create(name="PAYMENT")
    with pytest.raises(DomainError) as err:
        await projects.create(name="Payment")
    assert err.value.code == "project_name_duplicate"
    assert upper["name"] == "PAYMENT"


@pytest.mark.asyncio
async def test_tc014_update_reflects_and_touches(database) -> None:
    sm = database.sessionmaker
    created = await projects.create(name="支付中心", notes="旧备注")

    updated = await projects.update(created["projectId"], tech_stack="Python 3.12")
    assert updated["techStack"] == "Python 3.12"
    assert updated["notes"] == "旧备注"
    assert updated["updatedAt"] > created["updatedAt"]

    fetched = await projects.get(created["projectId"])
    assert fetched["techStack"] == "Python 3.12"

    cleared = await projects.update(created["projectId"], notes=None)
    assert cleared["notes"] is None
    assert cleared["updatedAt"] > updated["updatedAt"]

    same = await projects.update(created["projectId"])
    assert same["name"] == "支付中心"

    with pytest.raises(DomainError) as err:
        await projects.get(999999)
    assert err.value.code == "project_not_found"
    assert err.value.status_code == 404


@pytest.mark.asyncio
async def test_tc016_name_validation(database) -> None:
    sm = database.sessionmaker
    for bad_name in ("", "   ", "x" * 101):
        with pytest.raises(DomainError) as err:
            await projects.create(name=bad_name)
        assert err.value.status_code == 400
        assert err.value.details[0]["field"] == "name"

    for bad_url in (
        "ftp://example.com/repo",
        "http://user:secret@example.com/repo",
        "javascript:alert(1)",
        "https://example.com/" + "x" * 500,
    ):
        with pytest.raises(DomainError) as err:
            await projects.create(name="合法项目", repo_url=bad_url)
        assert err.value.details[0]["field"] == "repoUrl"

    assert await _count(sm) == 0

    ok = await projects.create(
        name="x" * 100, repo_url="https://example.com/org/repo?tab=1"
    )
    assert len(ok["name"]) == 100
    assert ok["repoUrl"].startswith("https://")
