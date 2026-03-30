import os
from urllib.parse import urlsplit


DEFAULT_LOCAL_HOSTS = ("127.0.0.1", "localhost")


def _split_csv(raw_value: str | None) -> list[str]:
    if not raw_value:
        return []
    return [item.strip() for item in raw_value.split(",") if item.strip()]


def normalize_origin(origin: str | None) -> str | None:
    if not origin:
        return None

    parsed = urlsplit(origin.strip())
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        return None

    hostname = parsed.hostname.lower()
    port = parsed.port
    default_port = 443 if parsed.scheme == "https" else 80
    netloc = hostname if port in {None, default_port} else f"{hostname}:{port}"
    return f"{parsed.scheme}://{netloc}"


def normalize_host(host: str | None) -> str | None:
    if not host:
        return None

    parsed = urlsplit(f"//{host.strip().lower()}")
    if not parsed.hostname:
        return None

    if parsed.port is not None:
        return f"{parsed.hostname.lower()}:{parsed.port}"
    return parsed.hostname.lower()


def get_allowed_hosts() -> list[str]:
    hosts = {host.lower() for host in DEFAULT_LOCAL_HOSTS}
    hosts.update(item.lower() for item in _split_csv(os.getenv("APP_ALLOWED_HOSTS")))
    return sorted(hosts)


def get_allowed_origins() -> list[str]:
    port = (os.getenv("PORT") or "8000").strip() or "8000"
    origins: set[str] = set()

    for host in get_allowed_hosts():
        if "*" in host:
            continue
        origins.add(f"http://{host}:{port}")
        origins.add(f"https://{host}:{port}")

    for candidate in _split_csv(os.getenv("ALLOWED_ORIGINS")):
        normalized = normalize_origin(candidate)
        if normalized is not None:
            origins.add(normalized)

    return sorted(origins)


def is_allowed_websocket_origin(
    origin: str | None,
    host: str | None,
    allowed_origins: list[str] | set[str] | None = None,
) -> bool:
    normalized_origin = normalize_origin(origin)
    normalized_host = normalize_host(host)
    if normalized_origin is None or normalized_host is None:
        return False

    if urlsplit(normalized_origin).netloc.lower() == normalized_host:
        return True

    origin_allowlist = allowed_origins if allowed_origins is not None else get_allowed_origins()
    normalized_allowlist = {
        candidate
        for candidate in (normalize_origin(item) for item in origin_allowlist)
        if candidate is not None
    }
    return normalized_origin in normalized_allowlist


SECURE_RESPONSE_HEADERS = {
    "Content-Security-Policy": "; ".join(
        [
            "default-src 'self'",
            "script-src 'self'",
            "style-src 'self'",
            "img-src 'self' data: blob:",
            "connect-src 'self'",
            "font-src 'self'",
            "object-src 'none'",
            "base-uri 'self'",
            "form-action 'self'",
            "frame-ancestors 'none'",
        ]
    ),
    "Permissions-Policy": "camera=(self), microphone=(), geolocation=()",
    "Referrer-Policy": "same-origin",
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
}
