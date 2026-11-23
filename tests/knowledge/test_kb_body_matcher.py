"""正文匹配。用例名带 TC 编号。"""

from __future__ import annotations

from vigil_workbench.knowledge.body_matcher import match_bodies


def test_tc109_matches_body_by_filename_then_heading() -> None:
    codes = ["ENT-1", "ENT-2", "ENT-3", "ENT-4"]
    files = [
        ("ENT-1.md", b"whole file body\n"),
        ("notes.md", b"### ENT-2\nbody2\n\n## Other\nignored\n"),
        ("a.md", b"### ENT-3\nfrom a\n"),
        ("b.md", b"### ENT-3\nfrom b\n### ENT-3\nfrom b again\n"),
        ("same.md", b"### ENT-4\nfirst\n### ENT-4\nsecond\n"),
        ("unrelated.md", b"# nothing here\n"),
    ]
    result = match_bodies(codes, files)

    assert result.content_for("ENT-1") == "whole file body"
    assert result.bodies["ent-1"].file_name == "ENT-1.md"
    assert result.content_for("ENT-2") == "body2"
    # 文件名升序优先于偏移：a.md 先于 b.md。
    assert result.content_for("ENT-3") == "from a"
    assert result.bodies["ent-3"].file_name == "a.md"
    # 同一文件多处命中取偏移最小。
    assert result.content_for("ENT-4") == "first"
    assert result.unmatched_files == ("unrelated.md",)

    duplicates = {(item.code, item.file_name) for item in result.duplicate_bodies}
    assert ("ENT-3", "b.md") in duplicates
    assert ("ENT-4", "same.md") in duplicates


def test_tc110_marks_missing_body_as_blank() -> None:
    codes = ["ENT-9", "ENT-8", "ENT-10"]
    files = [
        ("ENT-9.md", b"  \n\t"),
        ("blank.md", b"### ENT-10\n   \n"),
    ]
    result = match_bodies(codes, files)

    assert result.bodies["ent-9"].missing is True
    assert result.content_for("ENT-9") is None
    assert result.bodies["ent-10"].missing is True
    assert result.content_for("ENT-10") is None
    # 完全未匹配同样视为缺失，不用空串冒充。
    assert result.content_for("ENT-8") is None
    assert "ent-8" not in result.bodies
