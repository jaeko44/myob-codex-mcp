from __future__ import annotations

import pytest

from myob_codex_mcp.safety.validators import ValidationError, validate_guid, validate_relative_path


def test_validate_relative_path_blocks_absolute_urls() -> None:
    with pytest.raises(ValidationError):
        validate_relative_path("https://evil.example/path")


def test_validate_relative_path_requires_query_params_separately() -> None:
    with pytest.raises(ValidationError):
        validate_relative_path("/Sale/Invoice?$top=10")


def test_validate_guid() -> None:
    assert validate_guid("00000000-0000-0000-0000-000000000000") == "00000000-0000-0000-0000-000000000000"
    with pytest.raises(ValidationError):
        validate_guid("not-a-guid")
