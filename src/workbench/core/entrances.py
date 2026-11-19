"""6 个入口的唯一来源：key / 名称 / 用途 / 归属域 / 状态。

状态由本配置驱动（planned / live），页面不得散落硬编码分支。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

EntranceStatus = Literal["planned", "live"]


@dataclass(frozen=True, slots=True)
class Entrance:
    key: str
    name: str
    description: str
    domain: str
    status: EntranceStatus


ENTRANCES: tuple[Entrance, ...] = (
    Entrance(
        key="case-library",
        name="用例库",
        description="浏览与检索测试用例，并在库内发起用例生成。",
        domain="test-case",
        status="planned",
    ),
    Entrance(
        key="bug-analysis",
        name="分析 bug",
        description="结合缺陷描述与项目上下文定位根因。",
        domain="diagnosis",
        status="planned",
    ),
    Entrance(
        key="log-triage",
        name="排查日志",
        description="从日志片段中归纳异常链路与排查线索。",
        domain="diagnosis",
        status="planned",
    ),
    Entrance(
        key="sql-analysis",
        name="分析 SQL",
        description="分析 SQL 语义、执行风险与优化方向。",
        domain="diagnosis",
        status="planned",
    ),
    Entrance(
        key="regression-list",
        name="生成回归清单",
        description="根据变更范围整理回归检查项。",
        domain="regression-list",
        status="planned",
    ),
    Entrance(
        key="test-report",
        name="生成测试报告",
        description="汇总执行结果并生成结构化测试报告。",
        domain="test-report",
        status="planned",
    ),
)

ENTRANCE_KEYS: tuple[str, ...] = tuple(item.key for item in ENTRANCES)
VALID_STATUSES: frozenset[str] = frozenset({"planned", "live"})


def iter_entrances() -> tuple[Entrance, ...]:
    for item in ENTRANCES:
        if item.status not in VALID_STATUSES:
            raise ValueError(f"illegal entrance status: {item.status}")
    return ENTRANCES


def get_entrance(key: str) -> Entrance | None:
    for item in iter_entrances():
        if item.key == key:
            return item
    return None


def entrance_to_dict(item: Entrance) -> dict[str, str]:
    return {
        "key": item.key,
        "name": item.name,
        "description": item.description,
        "domain": item.domain,
        "status": item.status,
    }
