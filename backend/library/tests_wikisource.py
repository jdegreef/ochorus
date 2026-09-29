"""`library.wikisource.blocks` — Wikisource page HTML to clean reading blocks."""

from django.test import SimpleTestCase

from library.wikisource import Block, blocks

PAGE = """
<div class="wst-header ws-noexport"><div class="header-notes">
<div class="prp-pages-output">
<span><span class="pagenum ws-pagenum">&#8203;</span></span>
<div class="wst-center"><p>LETTERS OF PASCAL</p><div class="wst-center"><p>I</p></div></div>
<div class="wst-right"><p>January 26, 1648.</p></div>
<p><span class="dropinitial"><span class="dropinitial-initial">W</span></span>E have
received <i>your</i> letters.<sup class="reference"><a href="#n1">[1]</a></sup></p>
<table><tr><td class="dotted"><span class="opaque">A paragraph set in a table.</span></td>
<td><span class="opaque">&#160;</span></td></tr></table>
</div></div></div>
<div class="prp-pages-output"><div class="reflist"><ol class="references"><li>A note.</li></ol></div></div>
"""


class WikisourceBlocksTests(SimpleTestCase):
    def test_a_page_reads_as_clean_ordered_blocks(self):
        self.assertEqual(
            blocks(PAGE),
            [
                Block("center", "LETTERS OF PASCAL"),
                Block("center", "I"),
                Block("right", "January 26, 1648."),
                Block("p", "We have received <em>your</em> letters."),
                Block("p", "A paragraph set in a table."),
            ],
        )

    def test_text_inside_a_noexport_header_survives(self):
        # The header template is left unclosed on some pages, so the letter sits
        # inside it; cleaning before lifting the text out used to delete it.
        self.assertIn("We have received", " ".join(b.text for b in blocks(PAGE)))
