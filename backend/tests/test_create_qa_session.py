from datetime import datetime, timezone
from pathlib import Path

import pytest

from scripts.create_qa_session import _read_cookie_file, _write_cookie_file


def test_cookie_file_is_0600_and_raw_token_is_readable_only_by_helper(tmp_path: Path):
    cookie_file = tmp_path / "qa.cookie"
    _write_cookie_file(cookie_file, "synthetic-token", datetime.now(timezone.utc))

    assert cookie_file.stat().st_mode & 0o777 == 0o600
    assert _read_cookie_file(cookie_file) == "synthetic-token"


def test_cookie_file_rejects_broader_permissions(tmp_path: Path):
    cookie_file = tmp_path / "qa.cookie"
    _write_cookie_file(cookie_file, "synthetic-token", datetime.now(timezone.utc))
    cookie_file.chmod(0o644)

    with pytest.raises(ValueError, match="0600"):
        _read_cookie_file(cookie_file)
