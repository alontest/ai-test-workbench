"""知识库删除生命周期：逻辑库全部版本、条目级联与文件移入 trash（ADR-117）。

先提交数据库再清理文件：列表立即不再出现，文件系统失败只记数量并返回成功。
历史会话、事件与调用记录不修改。
"""

from __future__ import annotations

import logging
import shutil

from vigil_workbench.db.engine import get_sessionmaker
from vigil_workbench.db.repositories import knowledge as knowledge_repo
from vigil_workbench.services.errors import DomainError

logger = logging.getLogger(__name__)


def _kb_not_found() -> DomainError:
    return DomainError(
        "kb_not_found",
        "知识库不存在。",
        status_code=404,
        details=[{"field": "kbId", "message": "知识库不存在"}],
    )


class KnowledgeLifecycleService:
    """删除逻辑知识库；文件清理为提交后的 best-effort。"""

    def __init__(
        self,
        *,
        sessionmaker=None,  # noqa: ANN001
        storage=None,  # noqa: ANN001
    ) -> None:
        self._sessionmaker = sessionmaker
        self._storage = storage

    @property
    def sessionmaker(self):  # noqa: ANN201
        return self._sessionmaker or get_sessionmaker()

    @property
    def storage(self):  # noqa: ANN201
        if self._storage is None:
            from vigil_workbench.adapters.fs.knowledge_storage import KbStorage

            self._storage = KbStorage()
        return self._storage

    async def delete_logical(self, kb_id: str) -> None:
        async with self.sessionmaker() as db:
            kb = await knowledge_repo.get(db, kb_id)
            if kb is None:
                raise _kb_not_found()
            versions = await knowledge_repo.list_versions(
                db, project_id=kb.project_id, name_key=kb.name_key
            )
            await knowledge_repo.delete_logical(
                db, project_id=kb.project_id, name_key=kb.name_key
            )
            await db.commit()

        self._cleanup_files([version.kb_id for version in versions])

    def _cleanup_files(self, kb_ids: list[str]) -> None:
        """rename 进 ``.trash/<kbId>-<ts>/`` 后尽力删除；失败只记数量。"""
        failed = 0
        for version_kb_id in kb_ids:
            try:
                target = self.storage.move_to_trash(version_kb_id)
                if target is not None:
                    shutil.rmtree(target)
            except OSError:
                failed += 1
        if failed:
            logger.warning("knowledge-base trash cleanup failed count=%s", failed)


__all__ = ["KnowledgeLifecycleService"]
