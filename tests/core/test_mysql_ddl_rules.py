"""MySQL 8 的 DDL 规则，本地离线检查。

CI 的 ``mysql-tests`` 首次真跑时，0001 迁移因为 CHECK 约束引用自增列
（MySQL 3818）执行失败。SQLite 允许这种写法，本地 pytest 发现不了，
所以这类问题只能在 CI 里暴露。

这里把迁移链渲染成 MySQL 方言 SQL（离线，不连数据库），再按 MySQL 8
会拒绝的写法检查。渲染本身也会失败在无法翻译的 DDL 上。
"""

from __future__ import annotations

import contextlib
import io
import re

from alembic import command
from alembic.config import Config

MYSQL_URL = "mysql+asyncmy://verify:verify@127.0.0.1:3306/verify"
CREATE_TABLE_RE = re.compile(r"CREATE TABLE (\w+) \((.*?)\n\)", re.S)
AUTO_INCREMENT_RE = re.compile(r"^\s*(\w+)\s+[^,]*AUTO_INCREMENT", re.I | re.M)
CHECK_RE = re.compile(r"\bCHECK\s*\(", re.I)


def render_mysql_ddl(monkeypatch) -> str:  # noqa: ANN001
    """把 alembic 迁移链渲染成 MySQL 方言 SQL；不建立连接。"""
    # migrations/env.py 优先读 VIGIL_DATABASE_URL，测试进程里可能已被别的用例设置。
    monkeypatch.setenv("VIGIL_DATABASE_URL", MYSQL_URL)
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", MYSQL_URL)
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        command.upgrade(config, "head", sql=True)
    return out.getvalue()


def auto_increment_columns(block: str) -> set[str]:
    return {m.group(1) for m in AUTO_INCREMENT_RE.finditer(block)}


def check_expressions(block: str) -> list[str]:
    """取出每个 CHECK(...) 的表达式，按括号配平截断。"""
    expressions: list[str] = []
    for match in CHECK_RE.finditer(block):
        start = match.end() - 1
        depth = 0
        for pos in range(start, len(block)):
            if block[pos] == "(":
                depth += 1
            elif block[pos] == ")":
                depth -= 1
                if depth == 0:
                    expressions.append(block[start + 1 : pos].strip())
                    break
    return expressions


def check_mysql_ddl(ddl: str) -> list[str]:
    """返回 MySQL 8 会拒绝的写法；空列表表示通过。"""
    problems: list[str] = []
    for table, block in CREATE_TABLE_RE.findall(ddl):
        auto_columns = auto_increment_columns(block)
        if not auto_columns:
            continue
        for expression in check_expressions(block):
            for column in auto_columns:
                if re.search(
                    rf"(?<![A-Za-z0-9_]){re.escape(column)}(?![A-Za-z0-9_])",
                    expression,
                    re.I,
                ):
                    problems.append(
                        f"{table}: CHECK ({expression}) 引用了自增列 {column}"
                        "（MySQL 3818）"
                    )
    return problems


def test_guard_migration_chain_renders_for_mysql(monkeypatch) -> None:  # noqa: ANN001
    ddl = render_mysql_ddl(monkeypatch)
    assert "CREATE TABLE admin_credential" in ddl


def test_guard_no_check_constraint_on_auto_increment(monkeypatch) -> None:  # noqa: ANN001
    problems = check_mysql_ddl(render_mysql_ddl(monkeypatch))
    assert problems == [], "MySQL 会拒绝这些 DDL：\n" + "\n".join(problems)


def test_guard_checker_catches_0001_regression() -> None:
    """检查器必须能抓到 eef4da4^ 上真实渲染出来的那段 DDL。"""
    historical_ddl = """
CREATE TABLE admin_credential (
    credential_id SMALLINT NOT NULL AUTO_INCREMENT,
    algorithm VARCHAR(32) NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    updated_at DATETIME NOT NULL,
    CONSTRAINT pk_admin_credential PRIMARY KEY (credential_id),
    CONSTRAINT ck_admin_credential_credential_id CHECK (credential_id = 1)
)ENGINE=InnoDB CHARSET=utf8mb4 COLLATE utf8mb4_0900_ai_ci;
"""
    problems = check_mysql_ddl(historical_ddl)
    assert problems, "检查器漏掉了 CHECK 引用自增列"
    assert "credential_id" in problems[0]


def test_guard_checker_allows_check_on_plain_column() -> None:
    ddl = """
CREATE TABLE login_attempt (
    source_ip_hash CHAR(64) NOT NULL,
    failed_count INTEGER NOT NULL DEFAULT '0',
    CONSTRAINT ck_login_attempt_failed_count CHECK (failed_count >= 0)
)ENGINE=InnoDB;
"""
    assert check_mysql_ddl(ddl) == []
