"""Recipe URL import: fetch (SSRF-guarded) + recipe-scrapers parse (MIT).

Security: only http(s); hostname must resolve to a PUBLIC IP (blocks
169.254/10/172.16/192.168/loopback/link-local); 10s timeout; 2MB cap;
desktop UA. Users are responsible for source-site terms; attribution stored.
Never invents data: extraction failures return errors, not placeholders.
"""
import ipaddress
import socket
from urllib.parse import urlparse

ALLOWED_SCHEMES = {"http", "https"}
MAX_BYTES = 2_000_000
TIMEOUT = 10


def _public_host(host: str) -> bool:
    try:
        infos = socket.getaddrinfo(host, None)
    except socket.gaierror:
        return False
    addrs = []
    for fam, _, _, _, sockaddr in infos:
        try:
            addrs.append(ipaddress.ip_address(sockaddr[0]))
        except ValueError:
            return False
    if not addrs:
        return False
    return all(a.is_global for a in addrs)


def assert_safe_url(url: str) -> str:
    """Validate or raise ValueError. Returns normalized URL."""
    u = urlparse((url or "").strip())
    if u.scheme not in ALLOWED_SCHEMES or not u.hostname:
        raise ValueError("Only http(s) recipe URLs are supported")
    if not _public_host(u.hostname):
        raise ValueError("Refused: URL resolves to a private/internal address (SSRF guard)")
    return u.geturl()


def fetch_and_parse(url: str) -> dict:
    """Fetch + parse a recipe page. Returns attributed fields or raises ValueError."""
    import httpx
    from recipe_scrapers import scrape_html
    safe = assert_safe_url(url)
    try:
        r = httpx.get(safe, timeout=TIMEOUT, follow_redirects=True,
                      headers={"User-Agent": "Virelle/1.0 (recipe import; contact: admin@virelle.app)"})
    except Exception as e:
        raise ValueError(f"Could not fetch URL: {type(e).__name__}")
    if r.status_code != 200:
        raise ValueError(f"Page returned HTTP {r.status_code}")
    if len(r.content) > MAX_BYTES:
        raise ValueError("Page too large to import")
    final_host = urlparse(str(r.url)).hostname or ""
    if final_host and final_host != urlparse(safe).hostname and not _public_host(final_host):
        raise ValueError("Refused: redirect target is private (SSRF guard)")
    try:
        s = scrape_html(r.text[:MAX_BYTES], safe, wild_mode=True)
    except Exception as e:
        raise ValueError(f"Recipe extraction failed: {type(e).__name__}")
    def grab(fn, default=""):
        try:
            v = fn()
            return v if v not in (None, "") else default
        except Exception:
            return default
    title = grab(s.title)
    if not title:
        raise ValueError("No recipe found on this page")
    return {"title": str(title)[:200], "ingredients": [str(i)[:300] for i in grab(s.ingredients, []) or []],
            "instructions": [str(i)[:2000] for i in grab(s.instructions_list, []) or []],
            "servings": str(grab(s.yields, ""))[:40], "total_time": int(grab(s.total_time, 0) or 0),
            "image_url": str(grab(s.image, ""))[:500], "source_url": safe,
            "source_name": urlparse(safe).hostname or ""}
