"""python -m audit answer.md [--out report.md] [--lang en|es]"""
from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path

from . import __version__
from .core import audit

ICON = {"SUPPORTED": "✅", "PARTIAL": "🟡", "UNSUPPORTED": "❌", "UNREACHABLE": "⛔", "UNCITED": "❓", "NO CITATION NEEDED?": "·"}
TXT = {
    "en": {"title": "Citation audit", "summary": "Summary", "claim": "Claim", "evidence": "closest passage in the source",
           "missing": "figures not found in the source", "qmissing": "quotes not found verbatim", "found": "figures found",
           "note": "Deterministic text matching, no AI involved. SUPPORTED means the words and figures are on the cited page, not that the page is right. UNSUPPORTED means a human must check before the sentence is used."},
    "es": {"title": "Auditoría de citas", "summary": "Resumen", "claim": "Afirmación", "evidence": "pasaje más cercano en la fuente",
           "missing": "cifras que no aparecen en la fuente", "qmissing": "citas textuales no encontradas", "found": "cifras encontradas",
           "note": "Comparación de texto determinista, sin IA. SUPPORTED significa que las palabras y cifras están en la página citada, no que la página tenga razón. UNSUPPORTED significa que una persona debe revisarlo antes de usar la frase."},
}


def report(claims, name: str, lang: str = "en") -> str:
    t = TXT.get(lang, TXT["en"])
    counts = Counter(c.verdict for c in claims)
    out = [f"# {t['title']} · {name}", "", f"## {t['summary']}", ""]
    out += [f"- {ICON[k]} {k}: {v}" for k, v in counts.most_common()]
    for i, c in enumerate(claims, 1):
        out += ["", f"### {ICON[c.verdict]} {i}. {c.verdict}", f"> {c.text}"]
        for k in c.checks:
            out.append(f"- {ICON[k.verdict]} {k.url} · overlap {k.overlap:.2f}" + (f" · {k.error}" if k.error else ""))
            if k.numbers_found:
                out.append(f"  - {t['found']}: {', '.join(k.numbers_found)}")
            if k.numbers_missing:
                out.append(f"  - **{t['missing']}: {', '.join(k.numbers_missing)}**")
            if k.quotes_missing:
                out.append(f"  - **{t['qmissing']}: {' | '.join(k.quotes_missing)}**")
            if k.snippet and k.verdict != "SUPPORTED":
                out.append(f"  - {t['evidence']}: “{k.snippet}”")
    out += ["", "---", f"_{t['note']}_", ""]
    return "\n".join(out)


def main(argv=None) -> int:
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass
    p = argparse.ArgumentParser(prog="audit", description="Check whether cited sources support each sentence of an answer.")
    p.add_argument("--version", action="version", version=__version__)
    p.add_argument("answer", help="Markdown/text file with [n] references or inline [text](url) links")
    p.add_argument("--out")
    p.add_argument("--lang", default="en", choices=["en", "es"])
    a = p.parse_args(argv)
    claims = audit(Path(a.answer).read_text(encoding="utf-8"))
    md = report(claims, Path(a.answer).name, a.lang)
    if a.out:
        Path(a.out).write_text(md, encoding="utf-8")
        c = Counter(x.verdict for x in claims)
        print(f"written {a.out}: " + ", ".join(f"{k}={v}" for k, v in c.most_common()))
    else:
        print(md)
    return 1 if any(c.verdict in ("UNSUPPORTED", "UNCITED") for c in claims) else 0
