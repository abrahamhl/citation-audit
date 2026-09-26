import unittest

from audit.cli import report
from audit.core import audit, check_claim
from audit.text import numbers, page_text, references, sentences

PAGE = """<html><head><script>var x = 999999;</script></head><body><nav>Menu 12345</nav>
<p>The Port of Rotterdam is the largest seaport in Europe.</p>
<p>In 2023 the port handled 439 million tonnes of cargo.</p>
<p>The port area covers 12,713 hectares, according to the Port Authority.</p>
<p>It employs “about 385,000 people directly and indirectly” across the Netherlands.</p></body></html>"""

ANSWER = """The Port of Rotterdam is the largest seaport in Europe [1].
In 2023 the port handled 470 million tonnes of cargo [1].
The port area covers 12.713 hectares [1].
Rotterdam port employs "about 385,000 people directly and indirectly" [1].
The port was founded by the Romans in 1270 and has 80% market share.
It is also said the harbour is linked to [a missing page](https://missing.example/x).

Sources:
[1] Port facts - https://port.example/facts
"""


def fetcher(url, timeout=25.0):
    if url == "https://port.example/facts":
        return PAGE
    raise OSError("404 not found")


class TestAudit(unittest.TestCase):
    def test_numbers_across_locales(self):
        self.assertEqual(numbers("6,241 and 6.241 and 6 241"), ["6241", "6241", "6241"])
        self.assertEqual(numbers("4.5% or 4,5 %"), ["4.5%", "4.5%"])
        self.assertEqual(numbers("1.234.567,8"), ["1234567.8"])

    def test_page_text_skips_scripts_and_nav(self):
        t = page_text(PAGE)
        self.assertNotIn("999999", t)
        self.assertNotIn("12345", t)
        self.assertIn("439 million", t)

    def test_references_and_sentences(self):
        self.assertEqual(references(ANSWER), {"1": "https://port.example/facts"})
        self.assertEqual(len(sentences(ANSWER)), 6)

    def test_verdicts(self):
        claims = audit(ANSWER, fetcher=fetcher)
        v = [c.verdict for c in claims]
        self.assertEqual(v[0], "SUPPORTED")
        self.assertEqual(v[1], "UNSUPPORTED")                     # 470 is not on the page, 439 is
        self.assertEqual(claims[1].checks[0].numbers_missing, ["470"])
        self.assertEqual(v[2], "SUPPORTED")                       # 12.713 (ES/NL format) == 12,713
        self.assertEqual(v[3], "SUPPORTED")                       # verbatim quote present
        self.assertEqual(v[4], "UNCITED")                         # figures with no source
        self.assertEqual(v[5], "UNREACHABLE")

    def test_altered_quote_is_caught(self):
        c = check_claim('It employs "about 400,000 people directly and indirectly"', "u", page_text(PAGE))
        self.assertEqual(c.verdict, "UNSUPPORTED")
        self.assertTrue(c.quotes_missing)

    def test_report_is_explicit(self):
        md = report(audit(ANSWER, fetcher=fetcher), "answer.md", "es")
        self.assertIn("cifras que no aparecen en la fuente: 470", md)
        self.assertIn("pasaje más cercano", md)


if __name__ == "__main__":
    unittest.main()
