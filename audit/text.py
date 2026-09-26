"""Parsing the answer, extracting page text, and the matching primitives."""
from __future__ import annotations

import re
import unicodedata
from html.parser import HTMLParser

STOP = set("""
a an and are as at be been but by can could did do does for from had has have how if in into is it its may might more
most not of on or our over such than that the their them then there these they this those through to under was were
what when where which while who will with would also about after before between both each other only same some very
el la los las un una unos unas y o de del en con por para que se su sus al es son fue ser como más pero sin sobre entre
este esta estos estas ese esa lo le les ya ha han hay muy también cuando donde
de het een en of in op met voor van te is zijn was werd worden door naar bij als dat die dit deze om ook niet maar nog
""".split())

NUM_RE = re.compile(r"(?<![\w.,])(\d{1,3}(?:[.,  ]\d{3})+(?:[.,]\d+)?|\d+(?:[.,]\d+)?)(\s?%)?")
QUOTE_RE = re.compile(r"[\"“”«»„]([^\"“”«»„]{8,200})[\"“”«»„]")
LINK_RE = re.compile(r"\[([^\]]+)\]\((https?://[^)\s]+)\)")
REF_USE_RE = re.compile(r"\[(\d{1,3})\](?!\()")
REF_DEF_RE = re.compile(r"^\s*\[?(\d{1,3})[\].:)]\s+.*?(https?://\S+)", re.M)


def fold(s: str) -> str:
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c)).lower()
    return re.sub(r"\s+", " ", s)


def numbers(s: str) -> list[str]:
    """Canonical digit strings: '6,241' '6.241' '6 241' -> '6241'; '4.5' '4,5' -> '4.5'."""
    out = []
    for m in NUM_RE.finditer(s):
        raw = m.group(1).replace(" ", " ")
        if re.fullmatch(r"\d{1,3}(?:[., ]\d{3})+", raw):          # thousands grouping only
            val = re.sub(r"[., ]", "", raw)
        elif re.fullmatch(r"\d{1,3}(?:[., ]\d{3})+[.,]\d+", raw):  # grouping + decimals
            val = re.sub(r"[., ](?=\d{3}(?:[.,]|$))", "", raw).replace(",", ".")
        else:
            val = raw.replace(",", ".")
        if val.endswith(".0"):
            val = val[:-2]
        out.append(val + ("%" if m.group(2) else ""))
    return out


def content_words(s: str) -> set[str]:
    return {w for w in re.findall(r"[a-z][a-z\-]{3,}", fold(s)) if w not in STOP}


class _Text(HTMLParser):
    SKIP = {"script", "style", "noscript", "svg", "nav", "footer", "header", "form"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self._skip = 0

    def handle_starttag(self, tag, attrs):
        if tag in self.SKIP:
            self._skip += 1
        elif tag in ("p", "br", "li", "h1", "h2", "h3", "h4", "tr", "div", "td"):
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag in self.SKIP and self._skip:
            self._skip -= 1

    def handle_data(self, data):
        if not self._skip:
            self.parts.append(data)


def page_text(html: str) -> str:
    p = _Text()
    try:
        p.feed(html)
    except Exception:
        pass
    return re.sub(r"[ \t]+", " ", "".join(p.parts))


def sentences(text: str) -> list[str]:
    body = re.split(r"\n\s*(?:#+\s*)?(?:sources|references|fuentes|referencias|bronnen)\s*:?\s*\n", text, flags=re.I)[0]
    chunks = re.split(r"(?<=[.!?])\s+(?=[A-ZÁÉÍÓÚÑ\"“(\[])|\n{2,}|\n\s*[-*]\s+", body)
    return [c.strip(" -*\n") for c in chunks if len(c.strip()) > 15]


def references(text: str) -> dict[str, str]:
    return {m.group(1): m.group(2).rstrip(").,>") for m in REF_DEF_RE.finditer(text)}


def best_window(source_text: str, words: set[str], size: int = 3) -> tuple[float, str]:
    """Best overlap between the claim's content words and any run of `size` source sentences."""
    sents = [s.strip() for s in re.split(r"(?<=[.!?])\s+|\n+", source_text) if len(s.strip()) > 20]
    if not sents or not words:
        return 0.0, ""
    best, snippet = 0.0, ""
    for i in range(len(sents)):
        window = " ".join(sents[i:i + size])
        overlap = len(words & content_words(window)) / len(words)
        if overlap > best:
            best, snippet = overlap, window
    return best, snippet[:400]
