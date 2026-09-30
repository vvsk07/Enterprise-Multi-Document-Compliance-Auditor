"""
Tests for Workstream 6 & 7: API Security, File Validation, and Path Traversal.
"""

import pytest
from app.core.security import sanitize_filename, validate_file, RateLimiter

def test_sanitize_filename_traversal():
    assert sanitize_filename("../../../etc/passwd") == "passwd"
    assert sanitize_filename("..\\..\\Windows\\cmd.exe") == "cmd.exe"
    assert sanitize_filename("normal_contract.pdf") == "normal_contract.pdf"


def test_validate_file_extensions():
    ok, _ = validate_file("agreement.pdf", 1024)
    assert ok is True

    bad_ext, err = validate_file("script.py", 1024)
    assert bad_ext is False
    assert "Unsupported file extension" in err

    empty_file, err_empty = validate_file("empty.txt", 0)
    assert empty_file is False
    assert "empty" in err_empty

def test_rate_limiter():
    limiter = RateLimiter(requests_per_minute=2)
    client_ip = "192.168.1.100"

    assert limiter.is_allowed(client_ip) is True
    assert limiter.is_allowed(client_ip) is True
    assert limiter.is_allowed(client_ip) is False  # 3rd request blocked
