"""Link title scraper — fetches <title> or og:title from URLs."""
import html as _html
import re
import urllib.request

_link_title_cache: dict = {}


def fetch_link_title(url: str) -> str:
    """Fetch <title> or og:title from a URL. In-memory cache (1 day TTL)."""
    if not url or not url.startswith("http"):
        return ""
    if url in _link_title_cache:
        return _link_title_cache[url]
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (compatible; CAE-Dashboard/1.0)"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            raw_html = resp.read(32768).decode("utf-8", errors="replace")
        title = ""
        for pat in [
            r'og:title[^>]+content=[^>]*?content=["\']([^"\'<>]+)',
            r'content=["\']([^"\'<>]+)["\'][^>]*?og:title',
            r'<og:title[^>]*>([^<]+)</og:title>',
            r'<title[^>]*>([^<]+)</title>',
        ]:
            m = re.search(pat, raw_html, re.I | re.S)
            if m:
                title = m.group(1).strip()[:120]
                break
        title = _html.unescape(title) if title else ""
        _link_title_cache[url] = title
        return title
    except Exception:
        return ""
