"""把知识库注入服务注册进 core 的进程内端口（ADR-110 / ADR-112）。"""

from __future__ import annotations

from vigil_workbench.core.ports import register_injection_preparer
from vigil_workbench.services.knowledge.injection_service import KnowledgeInjectionService


def install_injection_preparer(app) -> KnowledgeInjectionService:  # noqa: ANN001
    """用当前应用会话工厂与设置构造服务并注册；返回实例便于测试断言。"""
    database = app.state.database
    service = KnowledgeInjectionService(
        sessionmaker=database.sessionmaker,
        settings=app.state.settings,
    )
    register_injection_preparer(service)
    return service


def uninstall_injection_preparer() -> None:
    register_injection_preparer(None)


__all__ = ["install_injection_preparer", "uninstall_injection_preparer"]
