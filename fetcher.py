"""Download a news page and extract its headline and paragraphs.
Uses only the Python standard library, so it adds no dependencies."""

import ipaddress
import socket
from html.parser import HTMLParser
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import HTTPRedirectHandler, Request, build_opener

MAX_BYTES = 1500000
TIMEOUT = 10
MAX_CHARS = 30000
MIN_WORDS = 30
USER_AGENT = "Mozilla/5.0 (compatible; FakeNewsAnalyzer/1.0)"


class FetchError(ValueError):
    """Friendly error that can be shown directly to the user."""


def _check_url(url):
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        raise FetchError("Please enter a full web address starting with http:// or https://")
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    try:
        infos = socket.getaddrinfo(parsed.hostname, port, proto=socket.IPPROTO_TCP)
    except (socket.gaierror, UnicodeError):
        raise FetchError("Could not find that website. Please check the address.")
    for info in infos:
        ip = ipaddress.ip_address(info[4][0].split("%")[0])
        if not ip.is_global:
            raise FetchError("Addresses on private or local networks are not allowed.")


class _SafeRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        _check_url(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


class _Extractor(HTMLParser):
    SKIP = {"script", "style", "noscript", "svg", "nav", "footer", "header", "aside", "form", "iframe", "template"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.skip_depth = 0
        self.in_p = False
        self.in_title = False
        self.in_h1 = False
        self.title = ""
        self.h1 = ""
        self.og_title = ""
        self.cur = []
        self.paragraphs = []

    def handle_starttag(self, tag, attrs):
        if tag in self.SKIP:
            self.skip_depth += 1
            return
        if tag == "meta":
            d = dict(attrs)
            if d.get("property") == "og:title" and d.get("content"):
                self.og_title = d["content"].strip()
            return
        if self.skip_depth:
            return
        if tag == "title":
            self.in_title = True
        elif tag == "h1":
            self.in_h1 = True
        elif tag == "p":
            self.in_p = True
            self.cur = []

    def handle_endtag(self, tag):
        if tag in self.SKIP:
            self.skip_depth = max(0, self.skip_depth - 1)
            return
        if tag == "title":
            self.in_title = False
        elif tag == "h1":
            self.in_h1 = False
        elif tag == "p" and self.in_p:
            self.in_p = False
            para = " ".join("".join(self.cur).split())
            if len(para.split()) >= 6:
                self.paragraphs.append(para)

    def handle_data(self, data):
        if self.skip_depth:
            return
        if self.in_title:
            self.title += data
        if self.in_h1:
            self.h1 += " " + data
        if self.in_p:
            self.cur.append(data)


def extract_article(html_text):
    """Return (headline, article_text) from HTML source."""
    parser = _Extractor()
    try:
        parser.feed(html_text)
        parser.close()
    except Exception:
        pass
    headline = ""
    for candidate in (parser.og_title, parser.h1, parser.title):
        candidate = " ".join(candidate.split())
        if candidate:
            headline = candidate
            break
    text = "\n\n".join(parser.paragraphs)[:MAX_CHARS]
    return headline, text


def fetch_article(url):
    url = (url or "").strip()
    if not url:
        raise FetchError("Please paste a link first.")
    if "://" not in url:
        url = "https://" + url
    _check_url(url)
    request = Request(url, headers={"User-Agent": USER_AGENT, "Accept": "text/html,text/plain;q=0.9"})
    try:
        with build_opener(_SafeRedirect).open(request, timeout=TIMEOUT) as resp:
            ctype = (resp.headers.get("Content-Type") or "").lower()
            if "html" not in ctype and "text/plain" not in ctype:
                raise FetchError("That link is not a normal web page.")
            raw = resp.read(MAX_BYTES + 1)[:MAX_BYTES]
            charset = resp.headers.get_content_charset() or "utf-8"
    except FetchError:
        raise
    except HTTPError as err:
        if err.code in (401, 403, 429):
            raise FetchError("This website blocks automated access. Please open the article and paste its text instead.")
        if err.code == 404:
            raise FetchError("That page was not found (error 404). Please check the link.")
        raise FetchError("The website returned an error (" + str(err.code) + "). Please paste the text instead.")
    except URLError:
        raise FetchError("Could not connect to that website. Please check the link or paste the text instead.")
    except OSError:
        raise FetchError("The website took too long to respond. Please try again or paste the text instead.")
    except Exception:
        raise FetchError("Could not download that page. Please paste the text instead.")

    try:
        decoded = raw.decode(charset, errors="replace")
    except LookupError:
        decoded = raw.decode("utf-8", errors="replace")

    if "text/plain" in ctype:
        headline, text = "", decoded[:MAX_CHARS]
    else:
        headline, text = extract_article(decoded)
    if len(text.split()) < MIN_WORDS:
        raise FetchError(
            "Could not find enough article text on that page (it may need JavaScript or a login). "
            "Please paste the text instead."
        )
    return headline, text
