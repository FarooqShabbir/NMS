"""Utility helper functions."""
import hashlib
import json
import re
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Union
from ipaddress import IPv4Address, IPv6Address


def calculate_hash(content: str) -> str:
    """Calculate SHA256 hash of content."""
    return hashlib.sha256(content.encode()).hexdigest()


def parse_timedelta(seconds: int) -> str:
    """Parse seconds into human-readable timedelta string."""
    if seconds < 0:
        return "0s"

    days = seconds // 86400
    hours = (seconds % 86400) // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60

    parts = []
    if days > 0:
        parts.append(f"{days}d")
    if hours > 0:
        parts.append(f"{hours}h")
    if minutes > 0:
        parts.append(f"{minutes}m")
    if secs > 0 or not parts:
        parts.append(f"{secs}s")

    return " ".join(parts)


def format_bytes(bytes_value: int) -> str:
    """Format bytes into human-readable string."""
    if bytes_value < 0:
        return "0 B"

    units = ["B", "KB", "MB", "GB", "TB", "PB"]
    unit_index = 0
    value = float(bytes_value)

    while value >= 1024 and unit_index < len(units) - 1:
        value /= 1024
        unit_index += 1

    if unit_index == 0:
        return f"{int(value)} {units[unit_index]}"
    return f"{value:.2f} {units[unit_index]}"


def format_bandwidth(bps: float) -> str:
    """Format bits per second into human-readable string."""
    return format_bytes(int(bps)) + "/s"


def calculate_utilization(counter1: int, counter2: int, interval: int, speed: int) -> float:
    """
    Calculate interface utilization percentage.

    Args:
        counter1: First counter value (octets)
        counter2: Second counter value (octets)
        interval: Time interval in seconds
        speed: Interface speed in bits per second

    Returns:
        Utilization percentage (0-100)
    """
    if speed <= 0 or interval <= 0:
        return 0.0

    delta = counter2 - counter1
    if delta < 0:
        # Counter wrapped
        delta = (2**64 - counter1) + counter2

    # Convert octets to bits
    bits = delta * 8
    bps = bits / interval

    utilization = (bps / speed) * 100
    return min(utilization, 100.0)


def diff_configs(old_config: str, new_config: str) -> Dict[str, Any]:
    """
    Generate a simple diff between two configurations.

    Returns a dict with added, removed, and modified lines.
    """
    old_lines = set(old_config.strip().splitlines())
    new_lines = set(new_config.strip().splitlines())

    added = new_lines - old_lines
    removed = old_lines - new_lines

    return {
        "added": list(added),
        "removed": list(removed),
        "has_changes": bool(added or removed),
        "added_count": len(added),
        "removed_count": len(removed),
    }


def is_valid_ip(ip: str) -> bool:
    """Check if string is a valid IPv4 or IPv6 address."""
    try:
        IPv4Address(ip) or IPv6Address(ip)
        return True
    except Exception:
        return False


def mask_sensitive_data(config: str, patterns: Optional[List[str]] = None) -> str:
    """
    Mask sensitive data in configuration.

    Args:
        config: Configuration text
        patterns: List of regex patterns to mask (default: passwords, secrets)
    """
    if patterns is None:
        patterns = [
            (r"(password|secret|key|credential)\s+(?:in-ascii\s+)?(\S+)", r"\1 *****"),
            (r"(snmp-server community)\s+(\S+)", r"\1 *****"),
            (r"(username \S+ password)\s+(\S+)", r"\1 *****"),
            (r"(enable (?:password|secret))\s+(\S+)", r"\1 *****"),
            (r"(wpa-psk ascii)\s+(\S+)", r"\1 *****"),
        ]

    masked_config = config
    for pattern, replacement in patterns:
        masked_config = re.sub(pattern, replacement, masked_config, flags=re.IGNORECASE)

    return masked_config


def parse_cron_expression(cron_expr: str) -> Optional[datetime]:
    """
    Parse a cron expression and return the next run time.

    Supports: minute hour day-of-month month day-of-week
    """
    # This is a simplified parser - for production, use 'croniter' package
    parts = cron_expr.split()
    if len(parts) != 5:
        return None

    now = datetime.now()
    # Simplified: just return next occurrence based on hour/minute
    try:
        minute = int(parts[0]) if parts[0] != "*" else now.minute
        hour = int(parts[1]) if parts[1] != "*" else now.hour

        next_run = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if next_run <= now:
            next_run += timedelta(days=1)

        return next_run
    except (ValueError, IndexError):
        return None


def safe_json_loads(s: str) -> Any:
    """Safely parse JSON string, returning None on failure."""
    if not s:
        return None
    try:
        return json.loads(s)
    except (json.JSONDecodeError, TypeError):
        return None


def safe_json_dumps(obj: Any) -> Optional[str]:
    """Safely dump object to JSON string, returning None on failure."""
    try:
        return json.dumps(obj, default=str)
    except (TypeError, ValueError):
        return None


def merge_dicts(base: Dict, override: Dict) -> Dict:
    """Deep merge two dictionaries."""
    result = base.copy()
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = merge_dicts(result[key], value)
        else:
            result[key] = value
    return result


def truncate_string(s: str, max_length: int = 100, suffix: str = "...") -> str:
    """Truncate string to max_length, adding suffix if truncated."""
    if len(s) <= max_length:
        return s
    return s[: max_length - len(suffix)] + suffix
