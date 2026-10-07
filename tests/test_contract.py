"""Phase 42: frontend-backend contract audit as a regression test.

Extracts every api("...") call from frontend JS/HTML, normalizes path params,
and asserts each (method, path) exists in the FastAPI route table.
Covers pages' GET/POST/PUT/PATCH/DELETE usage including template URLs.
"""
import re
from pathlib import Path

METHOD_RE = re.compile(r'api\(\s*[`\'"]([^`\'"]+)[`\'"]\s*,\s*\{\s*method\s*:\s*"(GET|POST|PUT|PATCH|DELETE)"')
PLAIN_RE = re.compile(r'api\(\s*[`\'"]([^`\'"]+)[`\'"]\s*\)')


def _norm(p: str) -> str:
    p = p.split("?")[0]
    p = re.sub(r"\$\{[^}]+\}", "{x}", p)
    p = re.sub(r"\{[^{}]+\}", "{x}", p)
    return p


def frontend_calls():
    fe = Path(__file__).resolve().parents[1] / "frontend"
    calls = set()
    for f in list(fe.glob("*.html")) + list(fe.glob("js/*.js")):
        src = f.read_text(encoding="utf-8")
        for m in METHOD_RE.finditer(src):
            calls.add((m.group(2), _norm(m.group(1))))
        for m in PLAIN_RE.finditer(src):
            calls.add(("GET", _norm(m.group(1))))
    return calls


def test_contract():
    import backend.app.main as M
    routes = set()
    for r in M.app.routes:
        methods = getattr(r, "methods", None) or set()
        path = getattr(r, "path", "")
        if path.startswith("/api/"):
            for m in methods:
                if m in ("GET", "POST", "PUT", "PATCH", "DELETE"):
                    routes.add((m, _norm(path)))
    missing = sorted(p for p in frontend_calls() if p not in routes)
    assert not missing, f"frontend calls with no backend route: {missing}"


def test_no_dead_research_links():
    """Every /api/* path referenced from research.html must exist."""
    import backend.app.main as M
    src = (Path(__file__).resolve().parents[1] / "frontend" / "research.html").read_text(encoding="utf-8")
    paths = {_norm(p) for p in re.findall(r"/api/[a-zA-Z0-9/_\-{}]+", src)}
    known = {_norm(getattr(r, "path", "")) for r in M.app.routes if getattr(r, "path", "").startswith("/api/")}
    assert paths <= known, f"stale research links: {paths - known}"
