"""Frontend syntax regression: every inline page script + app.js must parse.

Catches the class of bug where a stray bracket kills a page's entire script
block (nav + data loading dead). Skipped where node is unavailable.
"""
import re
import shutil
import subprocess
from pathlib import Path

import pytest

FE = Path(__file__).resolve().parents[1] / "frontend"
NODE = shutil.which("node")
INLINE_RE = re.compile(r"<script(?![^>]*src=)[^>]*>(.*?)</script>", re.S)


@pytest.mark.skipif(not NODE, reason="node not available")
@pytest.mark.parametrize("page", sorted(p.name for p in FE.glob("*.html")))
def test_inline_scripts_parse(page):
    src = (FE / page).read_text(encoding="utf-8")
    blocks = [b for b in INLINE_RE.findall(src) if b.strip()]
    assert blocks, f"{page} has no inline script (unexpected)"
    for i, code in enumerate(blocks):
        tmp = FE / f".syntax_check_{page.replace('.html', '')}_{i}.js"
        try:
            tmp.write_text(code, encoding="utf-8")
            r = subprocess.run([NODE, "--check", str(tmp)], capture_output=True, text=True)
            assert r.returncode == 0, f"{page} block {i}: {r.stderr[:300]}"
        finally:
            tmp.unlink(missing_ok=True)


@pytest.mark.skipif(not NODE, reason="node not available")
def test_app_js_parses():
    r = subprocess.run([NODE, "--check", str(FE / "js" / "app.js")], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr[:300]


def test_every_page_calls_nav_or_is_entry():
    """All content pages must render navigation; only auth/onboarding/landing differ."""
    exempt = {"auth.html", "onboarding.html", "index.html"}
    for page in FE.glob("*.html"):
        src = page.read_text(encoding="utf-8")
        if page.name in exempt:
            continue
        assert "nav(" in src, f"{page.name} never calls nav()"
        assert "requireUser()" in src, f"{page.name} missing auth guard"
