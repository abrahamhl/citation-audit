# citation-audit

**Checks whether the sources cited in an AI-generated answer actually say what the answer claims.**
Python 3.10+, standard library only, MIT licence. 6 tests. No AI inside: every verdict comes from plain text matching you can reproduce.

Language models cite sources confidently, and some of those citations don't hold up: the page exists, but the figure or the quote is not on it. This tool takes an answer with citations, fetches every cited page once, and checks each sentence against the page it cites.

## What it checks per sentence

| Check | How |
|---|---|
| Figures | Every number in the sentence must appear on the cited page. `12,713`, `12.713` and `12 713` count as the same number, so English, Spanish and Dutch formats all work. |
| Quotes | Anything in quotation marks must appear verbatim (case and accents ignored). |
| Wording | Overlap between the sentence's content words and the best matching passage on the page. |
| Uncited figures | Sentences with numbers or quotes and no citation are flagged `UNCITED`. |
| Dead links | Pages that can't be fetched are `UNREACHABLE`, never skipped. |

Verdicts: `SUPPORTED`, `PARTIAL`, `UNSUPPORTED`, `UNCITED`, `UNREACHABLE`. For anything not supported, the report shows the closest passage on the page so a reviewer can see what the source really says.

## Quick start

```bash
python -m audit answer.md --out report.md          # [1]-style references or inline [text](url) links
python -m audit answer.md --lang es --out informe.md
```

Exit code 1 when anything is `UNSUPPORTED` or `UNCITED`, so it can gate a publishing pipeline.

## Real run (27 September 2026)

`examples/ai_answer_demo.md` is a six-sentence answer in the style of an AI assistant, citing two Wikipedia pages. It contains two planted errors. Result (`examples/audit_report_en.md`): **3 supported, 2 unsupported, 1 uncited.**

- "Europol … is headquartered in The Hague": supported (overlap 0.88).
- "Europol employs more than 12,000 staff": **unsupported**, `12000` is not on the cited page.
- "…'the gateway to the entire European market for more than 500 million consumers'": **unsupported**, the quote is not on the cited page, and neither is the figure.
- "The Port of Rotterdam handles 90% of all Dutch foreign trade": **uncited**, a figure without a source.

## Limits

- Supported means *the cited page says it*, not that it is true.
- Paraphrases with no shared words can be marked partial or unsupported: a human decides.
- Pages rendered with JavaScript are read as the server sends them.

---

### En español

Audita las citas de una respuesta generada por IA: descarga cada fuente citada y comprueba frase a frase si las cifras, las citas textuales y el contenido están de verdad en la página. Sin IA dentro: todo es comparación de texto reproducible.
