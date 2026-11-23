"""日志与响应脱敏。用例名带 TC 编号。"""

from __future__ import annotations

import json
import logging

from vigil_workbench.core.redaction import RedactionFilter, redact


def test_tc063_logs_and_responses_never_contain_secrets(caplog) -> None:
    text = (
        'Authorization: Bearer sk-live-abcdef123456\n'
        "Cookie: vigil_session=abcdef\n"
        '{"apiKey": "sk-json-9999", "password": "hunter2"}\n'
        "provider key sk-abcdef1234"
    )
    cleaned = redact(text)
    assert "sk-live-abcdef123456" not in cleaned
    assert "vigil_session=abcdef" not in cleaned
    assert "sk-json-9999" not in cleaned
    assert "hunter2" not in cleaned
    assert "sk-abcdef1234" not in cleaned
    assert "[REDACTED]" in cleaned

    long_text = "x" * 5000
    assert len(redact(long_text, max_length=100)) == 100

    logger = logging.getLogger("vigil_workbench.test.redaction")
    logger.addFilter(RedactionFilter())
    caplog.set_level(logging.INFO, logger=logger.name)
    logger.info("upstream error Authorization: Bearer sk-live-abcdef123456 boom")
    record = caplog.records[-1]
    assert "sk-live-abcdef123456" not in record.getMessage()
    assert "[REDACTED]" in record.getMessage()

    payload = json.dumps({"message": redact(text)})
    assert "sk-" not in payload
