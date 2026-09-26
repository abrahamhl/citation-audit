"""Claim-by-claim audit of an answer against the pages it cites."""
from __future__ import annotations

import re
import urllib.request
from dataclasses import dataclass, field

from .text import LINK_RE, QUOTE_RE, REF_USE_RE, best_window, content_words, fold, numbers, page_text, references, sentences

try:  # optional OS certificate store; TLS verification is never disabled
    import truststore
    truststore.inject_into_ssl()
except ImportError:
    pass

UA = {"User-Agent": "citation-audit/0.1 (+https://github.com/abrahamhl/citation-audit)", "Accept-Language": "en,es,nl"}


def fetch(url: str, timeout: float = 25.0) -> str:
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=timeout) as r:
        raw = r.read(8 * 1024 * 1024)
        charset = r.headers.get_content_charset() or "utf-8"
        return raw.decode(charset, errors="replace")


@dataclass
class Check:
    url: str
    verdict: str                 # SUPPORTED | PARTIAL | UNSUPPORTED | UNREACHABLE
    overlap: float = 0.0
    numbers_found: list[str] = field(default_factory=list)
    numbers_missing: list[str] = field(default_factory=list)
    quotes_missing: list[str] = field(default_factory=list)
    snippet: str = ""
    error: str = ""


@dataclass
class Claim:
    text: str
    urls: list[str]
    checks: list[Check] = field(default_factory=list)
    verdict: str = ""


def check_claim(claim: str, url: str, source_text: str) -> Check:
    src = fold(source_text)
    src_numbers = set(numbers(source_text))
    src_numbers |= {n.rstrip("%") for n in src_numbers}
    nums = [n for n in numbers(claim) if len(n.rstrip("%")) > 1 or n.endswith("%")]  # single digits are too noisy
    found = [n for n in nums if n in src_numbers or n.rstrip("%") in src_numbers]
    missing = [n for n in nums if n not in found]
    quotes = [q for q in QUOTE_RE.findall(claim)]
    q_missing = [q for q in quotes if fold(q) not in src]
    words = content_words(LINK_RE.sub(r"\1", claim))
    overlap, snippet = best_window(source_text, words)
    if missing or q_missing or overlap < 0.25:
        # A figure or a quote that is not on the page means the sentence, as written, is not supported.
        verdict = "UNSUPPORTED"
    elif overlap < 0.5:
        verdict = "PARTIAL"
    else:
        verdict = "SUPPORTED"
    return Check(url, verdict, round(overlap, 2), found, missing, q_missing, snippet)


RANK = {"SUPPORTED": 3, "PARTIAL": 2, "UNSUPPORTED": 1, "UNREACHABLE": 0}


def audit(answer: str, fetcher=fetch) -> list[Claim]:
    refs = references(answer)
    cache: dict[str, str | Exception] = {}
    claims: list[Claim] = []
    for s in sentences(answer):
        urls = [u for _, u in LINK_RE.findall(s)] + [refs[n] for n in REF_USE_RE.findall(s) if n in refs]
        urls = list(dict.fromkeys(urls))
        clean = re.sub(r"\s+([.,;:!?])", r"\1", REF_USE_RE.sub("", s)).strip()
        c = Claim(clean, urls)
        if not urls:
            c.verdict = "UNCITED" if numbers(clean) or QUOTE_RE.search(clean) else "NO CITATION NEEDED?"
            claims.append(c)
            continue
        for u in urls:
            if u not in cache:
                try:
                    cache[u] = page_text(fetcher(u))
                except Exception as e:  # recorded, never silently skipped
                    cache[u] = e
            got = cache[u]
            if isinstance(got, Exception):
                c.checks.append(Check(u, "UNREACHABLE", error=f"{type(got).__name__}: {got}"[:160]))
            else:
                c.checks.append(check_claim(clean, u, got))
        c.verdict = max(c.checks, key=lambda k: RANK[k.verdict]).verdict   # the best supporting source counts
        claims.append(c)
    return claims
