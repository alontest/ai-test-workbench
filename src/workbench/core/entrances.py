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
        description="基于知识库规则与代码路径两阶段设计用例，支持溯源锚点、失效标红与多格式导出。",
        domain="test-case",
        status="live",
    ),
    Entrance(
        key="regression-list",
        name="生成回归清单",
        description="基于 Git 变更路径、本体一跳邻居与诊断结论三路召回，输出风险分级与漏测盲区。",
        domain="regression-list",
        status="planned",
    ),
    Entrance(
        key="test-report",
        name="生成测试报告",
        description="聚合用例执行率、回归覆盖度与诊断风险结论，产出带完整追溯编号的质量报告。",
        domain="test-report",
        status="planned",
    ),
    Entrance(
        key="bug-analysis",
        name="分析 Bug",
        description="联动报错信息、仓库源码与业务规则，按「假设 → 证据 → 结论」定位缺陷根因。",
        domain="diagnosis",
        status="planned",
    ),
    Entrance(
        key="log-triage",
        name="排查日志",
        description="从日志堆栈提取异常信号，自动关联对应版本源码与知识库条目收敛排查结论。",
        domain="diagnosis",
        status="planned",
    ),
    Entrance(
        key="sql-analysis",
        name="分析 SQL",
        description="结合 SQL、EXPLAIN 执行计划与知识库表结构（ENT-），诊断索引失效与锁竞争风险。",
        domain="diagnosis",
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
