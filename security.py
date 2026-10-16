import os
import re
import html
import uuid
import time
import secrets
import hashlib
from typing import Tuple, Dict, List, Optional
import asyncio

# Whitelist of allowed font families for FFmpeg subtitle rendering
ALLOWED_FONTS = [
    "Arial",
    "Arial Black",
    "Calibri",
    "Comic Sans MS",
    "Consolas",
    "Courier New",
    "Georgia",
    "Impact",
    "Tahoma",
    "Times New Roman",
    "Trebuchet MS",
    "Verdana"
]

ALLOWED_VIDEO_EXTENSIONS = {".mp4", ".avi", ".mkv", ".mov"}
ALLOWED_MIME_TYPES = {
    "video/mp4",
    "video/x-msvideo",
    "video/x-matroska",
    "video/quicktime",
    "application/octet-stream"
}

ALLOWED_BORDER_STYLES = {"outline", "box"}
ALLOWED_RESOLUTION_CAPS = {"original", "720p", "480p"}
ALLOWED_MODEL_SIZES = {"tiny", "base", "small", "medium", "large"}
ALLOWED_SEGMENTATION_MODES = {"line_by_line", "word_by_word"}

# Regex patterns
COLOR_HEX_REGEX = re.compile(r"^&H[0-9a-fA-F]{8}$|^#[0-9a-fA-F]{6}$")
LANGUAGE_CODE_REGEX = re.compile(r"^[a-zA-Z]{2,5}(-[a-zA-Z0-9]{2,5})?$")
EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")


# =====================================================================
# Password Hashing & Verification (PBKDF2-HMAC-SHA256, 600,000 rounds)
# =====================================================================

def hash_password(password: str) -> str:
    """
    Hash a password using PBKDF2-HMAC-SHA256 with 600,000 iterations
    and a cryptographically secure 32-byte salt.
    Returns: pbkdf2_sha256$<iterations>$<salt_hex>$<hash_hex>
    """
    if not isinstance(password, str) or not password:
        raise ValueError("Password must be a non-empty string.")
    
    salt = secrets.token_bytes(32)
    iterations = 600_000
    derived = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return f"pbkdf2_sha256${iterations}${salt.hex()}${derived.hex()}"


def verify_password(password: str, hashed_value: str) -> bool:
    """
    Verify a password against a stored PBKDF2-HMAC-SHA256 hash using
    constant-time comparison to prevent timing attacks.
    """
    if not password or not hashed_value or not isinstance(hashed_value, str):
        return False
    
    parts = hashed_value.split("$")
    if len(parts) != 4 or parts[0] != "pbkdf2_sha256":
        return False
    
    try:
        iterations = int(parts[1])
        salt = bytes.fromhex(parts[2])
        expected_hash = bytes.fromhex(parts[3])
    except (ValueError, TypeError):
        return False
    
    derived = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return secrets.compare_digest(derived, expected_hash)


def verify_admin_key(provided_key: Optional[str], expected_key: Optional[str]) -> bool:
    """
    Constant-time comparison for admin authentication tokens.
    """
    if not provided_key or not expected_key:
        return False
    return secrets.compare_digest(provided_key.strip(), expected_key.strip())


# =====================================================================
# Input Validation & Sanitization
# =====================================================================

def sanitize_filename(filename: str) -> str:
    """
    Sanitize an uploaded file name to eliminate directory traversal sequences,
    null bytes, and control characters.
    """
    if not filename:
        return "unnamed_video.mp4"
    
    # Strip any directory components
    clean_name = os.path.basename(filename)
    # Remove null bytes and non-printable characters
    clean_name = re.sub(r"[\x00-\x1f\x7f]", "", clean_name)
    # Remove dangerous characters and keep only alphanumeric, dashes, dots, underscores
    clean_name = re.sub(r"[^\w\.\-]", "_", clean_name)
    # Limit length to avoid filesystem truncation issues
    if len(clean_name) > 100:
        base, ext = os.path.splitext(clean_name)
        clean_name = base[:90] + ext
    return clean_name or "video.mp4"


def validate_uuid(value: str) -> bool:
    """
    Validate that an identifier matches standard UUID format.
    Prevents path traversal and parameter injection in resource lookups.
    """
    if not value or not isinstance(value, str):
        return False
    try:
        val = uuid.UUID(value, version=4)
        return str(val) == value.lower()
    except (ValueError, AttributeError, TypeError):
        return False


def is_safe_path(base_dir: str, target_path: str) -> bool:
    """
    Verify that target_path resolves strictly within base_dir.
    Prevents directory traversal attacks (e.g., ../../etc/passwd).
    """
    try:
        abs_base = os.path.abspath(base_dir)
        abs_target = os.path.abspath(target_path)
        common = os.path.commonpath([abs_base, abs_target])
        return common == abs_base
    except Exception:
        return False


def validate_font_name(font_name: str) -> str:
    """
    Strict whitelist check for font family names to prevent FFmpeg filter breakout.
    """
    if font_name in ALLOWED_FONTS:
        return font_name
    return "Arial"


def validate_font_color(font_color: str) -> str:
    """
    Validate color string against ASS format (&H00BBGGRR) or HTML Hex (#RRGGBB).
    """
    if font_color and COLOR_HEX_REGEX.match(font_color):
        return font_color
    return "&H00FFFFFF"


def validate_font_size(font_size: int) -> int:
    """
    Ensure font size is within safe bounds [8, 72].
    """
    try:
        size = int(font_size)
        return max(8, min(size, 72))
    except (ValueError, TypeError):
        return 20


def validate_alignment(alignment: int) -> int:
    """
    Validate ASS subtitle alignment key (1 through 9).
    """
    try:
        align = int(alignment)
        return align if 1 <= align <= 9 else 2
    except (ValueError, TypeError):
        return 2


def validate_language_code(lang: str) -> str:
    """
    Validate target language code (e.g., 'en', 'es', 'zh-cn', 'ur').
    """
    if lang and LANGUAGE_CODE_REGEX.match(lang):
        return lang.lower()
    return "en"


def validate_border_style(style: str) -> str:
    """
    Validate border style string.
    """
    if style in ALLOWED_BORDER_STYLES:
        return style
    return "outline"


def validate_resolution_cap(res: str) -> str:
    """
    Validate resolution cap parameter.
    """
    if res in ALLOWED_RESOLUTION_CAPS:
        return res
    return "original"


def validate_model_size(size: str) -> str:
    """
    Validate Whisper model size.
    """
    if size in ALLOWED_MODEL_SIZES:
        return size
    return "small"


def validate_segmentation_mode(mode: str) -> str:
    """
    Validate subtitle timing segmentation mode.
    """
    if mode in ALLOWED_SEGMENTATION_MODES:
        return mode
    return "line_by_line"


def validate_email_address(email: Optional[str]) -> Optional[str]:
    """
    Validate an optional email address.
    """
    if not email:
        return None
    cleaned = email.strip()
    if len(cleaned) <= 254 and EMAIL_REGEX.match(cleaned):
        return cleaned
    return None


def sanitize_email_content(text: Optional[str]) -> str:
    """
    HTML-escape strings placed into email notification templates.
    """
    if not text:
        return ""
    return html.escape(str(text))


# =====================================================================
# In-Memory Sliding-Window Rate Limiter
# =====================================================================

class SlidingWindowRateLimiter:
    """
    Lightweight, thread-safe in-memory rate limiter using sliding timestamp windows.
    Protects CPU-heavy endpoints (Whisper AI, FFmpeg transcoding) against DoS.
    """
    def __init__(self, cleanup_interval_seconds: int = 120):
        self._records: Dict[str, List[float]] = {}
        self._lock = asyncio.Lock()
        self._cleanup_interval = cleanup_interval_seconds
        self._last_cleanup = time.time()

    async def is_allowed(self, key: str, max_requests: int, window_seconds: int) -> Tuple[bool, int]:
        """
        Check if key has exceeded max_requests in the past window_seconds.
        Returns: (is_allowed: bool, retry_after_seconds: int)
        """
        now = time.time()
        async with self._lock:
            # Periodic cleanup of stale keys to prevent memory leak
            if now - self._last_cleanup > self._cleanup_interval:
                self._purge_stale_records(now)
                self._last_cleanup = now
            
            timestamps = self._records.get(key, [])
            cutoff = now - window_seconds
            valid_timestamps = [t for t in timestamps if t > cutoff]
            
            if len(valid_timestamps) >= max_requests:
                earliest = valid_timestamps[0]
                retry_after = max(1, int(window_seconds - (now - earliest)))
                self._records[key] = valid_timestamps
                return False, retry_after
            
            valid_timestamps.append(now)
            self._records[key] = valid_timestamps
            return True, 0

    def _purge_stale_records(self, now: float):
        max_retention = 300  # 5 minutes
        stale_keys = [
            k for k, timestamps in self._records.items()
            if not timestamps or (now - timestamps[-1]) > max_retention
        ]
        for k in stale_keys:
            del self._records[k]


# Global rate limiter instance
rate_limiter = SlidingWindowRateLimiter()
