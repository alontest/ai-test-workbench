"""知识库注入留痕：ai_call_record 四列 + session_event 类型扩展。

``down_revision`` 指向 ``0005``；knowledge-base spec 的 ``0007`` 依赖本 revision。
本迁移不创建、不引用 ``knowledge_base`` 表。
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None

EVENT_TYPES_WITH_KNOWLEDGE = (
    "type IN ('input_text', 'artifact', 'call', 'status_change', 'knowledge_injection')"
)
EVENT_TYPES_BASELINE = "type IN ('input_text', 'artifact', 'call', 'status_change')"
TOTAL_CHARS_CHECK = "total_chars = prompt_chars + injected_chars"


def upgrade() -> None:
    with op.batch_alter_table("ai_call_record") as batch:
        batch.add_column(sa.Column("knowledge_injection", sa.JSON(), nullable=True))
        batch.add_column(
            sa.Column("injected_chars", sa.Integer(), nullable=False, server_default="0")
        )
        batch.add_column(
            sa.Column("prompt_chars", sa.Integer(), nullable=False, server_default="0")
        )
        batch.add_column(
            sa.Column("total_chars", sa.Integer(), nullable=False, server_default="0")
        )
        batch.create_check_constraint(
            "ck_ai_call_record_injected_chars", "injected_chars >= 0"
        )
        batch.create_check_constraint(
            "ck_ai_call_record_prompt_chars", "prompt_chars >= 0"
        )
        batch.create_check_constraint("ck_ai_call_record_total_chars", "total_chars >= 0")
        batch.create_check_constraint(
            "ck_ai_call_record_total_chars_sum", TOTAL_CHARS_CHECK
        )

    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        with op.batch_alter_table("session_event", recreate="always") as batch:
            batch.drop_constraint("ck_session_event_type", type_="check")
            batch.create_check_constraint("ck_session_event_type", EVENT_TYPES_WITH_KNOWLEDGE)
    else:
        op.drop_constraint("ck_session_event_type", "session_event", type_="check")
        op.create_check_constraint(
            "ck_session_event_type", "session_event", EVENT_TYPES_WITH_KNOWLEDGE
        )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        with op.batch_alter_table("session_event", recreate="always") as batch:
            batch.drop_constraint("ck_session_event_type", type_="check")
            batch.create_check_constraint("ck_session_event_type", EVENT_TYPES_BASELINE)
    else:
        op.drop_constraint("ck_session_event_type", "session_event", type_="check")
        op.create_check_constraint(
            "ck_session_event_type", "session_event", EVENT_TYPES_BASELINE
        )

    with op.batch_alter_table("ai_call_record") as batch:
        batch.drop_constraint("ck_ai_call_record_total_chars_sum", type_="check")
        batch.drop_constraint("ck_ai_call_record_total_chars", type_="check")
        batch.drop_constraint("ck_ai_call_record_prompt_chars", type_="check")
        batch.drop_constraint("ck_ai_call_record_injected_chars", type_="check")
        batch.drop_column("total_chars")
        batch.drop_column("prompt_chars")
        batch.drop_column("injected_chars")
        batch.drop_column("knowledge_injection")
