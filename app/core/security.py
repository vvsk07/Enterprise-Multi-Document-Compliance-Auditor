"""
Security, API Authentication, File Validation, & Rate Limiting Module.
Provides API-key authentication, path traversal defense, file validation, and lightweight in-memory rate limiting.
"""

import os
import re
import time
import secrets
from pathlib import Path
from collections import defaultdict
from typing import Tuple, Optional
from fastapi import Request, Security, HTTPException, status
from fastapi.security.api_key import APIKeyHeader

from app.config import settings, get_document_processing_config, get_security_config, get_api_config
from app.core.logging import logger

API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)

class RateLimiter:
    """Lightweight sliding window in-memory rate limiter."""
    def __init__(self, requests_per_minute: int = 60):
        self.requests_per_minute = requests_per_minute
        self.requests = defaultdict(list)

    def is_allowed(self, client_ip: str) -> bool:
        now = time.time()
        window_start = now - 60.0

        # Filter out requests older than 1 minute
        valid_requests = [t for t in self.requests[client_ip] if t > window_start]
        self.requests[client_ip] = valid_requests

        if len(valid_requests) < self.requests_per_minute:
            self.requests[client_ip].append(now)
            return True
        return False

rate_limiter = RateLimiter(requests_per_minute=get_api_config().get("rate_limit", {}).get("requests_per_minute", 60))

def get_allowed_extensions() -> set:
    doc_cfg = get_document_processing_config()
    return set(doc_cfg.get("supported_extensions", [".pdf", ".docx", ".txt"]))

def get_max_file_size_bytes() -> int:
    doc_cfg = get_document_processing_config()
    return doc_cfg.get("max_file_size_mb", 25) * 1024 * 1024

def sanitize_filename(filename: str) -> str:
    """
    Sanitizes a filename to prevent path traversal and unsafe characters.
    Extracts basename and strips non-alphanumeric characters except dot, underscore, dash.
    """
    basename = os.path.basename(filename)
    basename = re.sub(r'[\x00-\x1f\x7f]', '', basename)
    basename = re.sub(r'^\.+(?=\.)', '', basename)

    name, ext = os.path.splitext(basename)
    name = re.sub(r'[^a-zA-Z0-9_\-]', '_', name)
    ext = ext.lower()

    if not name:
        name = "unnamed_document"
    return f"{name}{ext}"

def validate_file(filename: str, file_size: int) -> Tuple[bool, str]:
    """Validates file extension and size limits."""
    if file_size <= 0:
        return False, "Uploaded file is empty (0 bytes)."

    max_bytes = get_max_file_size_bytes()
    if file_size > max_bytes:
        max_mb = get_document_processing_config().get("max_file_size_mb", 25)
        return False, f"File size exceeds maximum allowed limit of {max_mb} MB."

    allowed_exts = get_allowed_extensions()
    ext = Path(filename).suffix.lower()
    if ext not in allowed_exts:
        allowed_str = ", ".join(allowed_exts)
        return False, f"Unsupported file extension '{ext}'. Allowed extensions: {allowed_str}."

    return True, ""

def verify_api_key(
    request: Request,
    api_key_header: Optional[str] = Security(API_KEY_HEADER)
):
    """
    Dependency that enforces API key authentication if security is enabled.
    """
    sec_config = get_security_config()
    security_enabled = sec_config.get("enabled", False)

    # Check environment variable AUDITOR_API_KEY
    expected_api_key = os.getenv("AUDITOR_API_KEY", sec_config.get("api_key", ""))

    if not security_enabled or not expected_api_key:
        return True

    if not api_key_header:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API Key missing in 'X-API-Key' header."
        )

    # Constant time comparison to prevent timing attacks
    if not secrets.compare_digest(api_key_header, expected_api_key):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API Key."
        )

    return True

def enforce_rate_limit(request: Request):
    """Dependency that enforces sliding window rate limiting."""
    api_cfg = get_api_config()
    if not api_cfg.get("rate_limit", {}).get("enabled", True):
        return True

    client_ip = request.client.host if request.client else "127.0.0.1"
    if not rate_limiter.is_allowed(client_ip):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded. Maximum 60 requests per minute allowed."
        )
    return True
