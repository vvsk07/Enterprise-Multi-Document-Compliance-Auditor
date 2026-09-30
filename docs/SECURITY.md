# SECURITY SPECIFICATION

## API Authentication
API key authentication is supported via the `X-API-Key` HTTP header.
Authentication is enabled by setting `security.enabled: true` in `configs/settings.yaml` or passing `AUDITOR_API_KEY` in environment variables.
Keys are validated using constant-time comparison (`secrets.compare_digest`) to protect against timing side-channel attacks.

## File Upload Security & Path Traversal Prevention
1. **Filename Sanitization**: `sanitize_filename()` strips path components, null bytes (`\x00`), hidden leading dots, and unsafe characters.
2. **File Extension Whitelisting**: Restricted to `.pdf`, `.docx`, and `.txt`.
3. **File Size Hard Limit**: Rejects uploads exceeding 25 MB.

## Rate Limiting & Input Validation
- Sliding-window in-memory rate limiting enforces a maximum of 60 requests per minute per IP address.
- Query string lengths are validated and limited to 2000 characters.

## Secret Redaction in Audit Logs
The audit logging service automatically scrubs sensitive fields (`api_key`, `password`, `secret`, `authorization`, `token`) prior to persisting log entries to SQLite.
