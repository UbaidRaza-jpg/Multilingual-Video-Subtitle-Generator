# Security Policy

## Overview

This project implements defense-in-depth security practices across its FastAPI backend, Streamlit client, and processing pipeline.

---

## Implemented Security Controls

### 1. Secret Protection & Environment Isolation
* API keys and credentials are never hardcoded in source files.
* Environment variables are loaded strictly from `.env` or container environment parameters.
* `.env` is permanently excluded via `.gitignore` and verified absent from Git commit history.
* A template `.env.example` provides non-sensitive parameter definitions.

### 2. Authentication & Admin Route Protection
* Administrative endpoints (`/admin/stats`, `/admin/tasks`, `/admin/cleanup`) are protected with token-based authentication.
* Admin authentication requires a valid API key passed either via the `X-Admin-API-Key` header or standard `Authorization: Bearer <key>` header.
* Key comparisons use cryptographically constant-time comparison (`secrets.compare_digest`) to prevent timing side-channel attacks.
* When `ADMIN_API_KEY` is not explicitly configured in `.env`, the server generates a cryptographically random 32-byte ephemeral key on startup.

### 3. Password Hashing Specification
* The `security.py` module provides PBKDF2-HMAC-SHA256 password hashing with 600,000 iterations and a 32-byte cryptographically secure random salt.
* Password verification uses constant-time byte comparisons to mitigate brute-force and timing vulnerabilities.

### 4. Input Validation & Form Sanitization
* **File Uploads**: Validated by extension whitelist (`.mp4`, `.avi`, `.mkv`, `.mov`) and MIME types. Strict 200MB size enforcement stops Denial-of-Service storage exhaustion.
* **Filename Sanitization**: Uploaded filenames are stripped of path traversal characters (`..`, `/`, `\`), null bytes, and non-printable control characters.
* **Styling Parameters**: Subtitle styling parameters (`font_name`, `font_color`, `font_size`, `alignment`, `border_style`) are validated against strict whitelists before injection into FFmpeg filter expressions.
* **UUID Validation**: All path parameters (`video_id`, `task_id`) are validated against RFC-4122 UUIDv4 syntax to prevent path traversal or parameter tampering.
* **Path Traversal Defense**: All file access and downloads verify that paths resolve strictly within designated directories (`uploads/`, `temp_outputs/`).

### 5. Cross-Site Scripting (XSS) Prevention
* **Backend Email Sanitization**: Dynamic user inputs (`filename`, `error_reason`) are HTML-escaped using `html.escape` before inclusion in email notification templates.
* **Frontend DOM Construction**: Segment blocks in `frontend/main.js` are constructed using native DOM nodes (`createElement`, `.textContent`, `.value`) rather than unescaped string interpolation into `innerHTML`.

### 6. Rate Limiting & Denial-of-Service Protection
* An in-memory sliding-window rate limiter protects CPU-intensive operations (Whisper transcription, FFmpeg encoding):
  * Video Uploads (`/upload`): 10 requests per minute per IP.
  * Video Processing (`/process`, `/transcribe`): 10 requests per minute per IP.
  * Previews (`/preview`): 25 requests per minute per IP.
  * General requests: 120 requests per minute per IP.
* When thresholds are exceeded, HTTP 429 Too Many Requests is returned with a `Retry-After` header.

### 7. HTTP Security Headers & CORS
* Standard security headers are injected on all HTTP responses:
  * `X-Content-Type-Options: nosniff`
  * `X-Frame-Options: DENY`
  * `X-XSS-Protection: 1; mode=block`
  * `Referrer-Policy: strict-origin-when-cross-origin`
  * `Content-Security-Policy: default-src 'self' https: data: 'unsafe-inline'; frame-ancestors 'none'; object-src 'none';`
  * `Permissions-Policy: camera=(), microphone=(), geolocation=()`
* CORS origins are restricted via `ALLOWED_ORIGINS` to trusted endpoints rather than unrestricted wildcards.

### 8. Production Server Configuration
* Debug mode and live-reloading are disabled in production runtime entrypoints (`reload=False`).
* Automated periodic background cleanup purges temporary files older than 15 minutes to prevent disk exhaustion.

---

## Reporting Vulnerabilities

If you discover a security vulnerability in this project, please open a private security advisory on GitHub or contact the maintainer directly.
