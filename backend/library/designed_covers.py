"""The hand-made covers — the ones nothing may redraw — and what we derive from
them for the translations.

THE RULE
A designed cover is a raster under ``/covers/<slug>.<ext>`` with its words baked
into the pixels: a photograph, a layout, a title set by a person. It is not
output. Every other cover in the library is drawn by a machine and can be drawn
again — a plate ground from ``covers.build_ground``, a webp variant from
``build_cover_assets``, an og twin from ``ensure_og_twin`` — and each of those
tools decides what a book should look like from its data. A designed cover
carries a judgement no data records, so **it is frozen**: the file that is
committed is the file that ships, and a tool that would rewrite it has a bug.

``DESIGNED`` below is that promise written down — one entry per cover, keyed by
the URL a fixture row wears, valued by the SHA-256 of the committed bytes. Two
gates in ``tests_fixture`` hold it up:

* ``test_designed_covers_are_never_changed`` recomputes every digest, so an
  overwrite, a re-compression or a well-meaning "optimisation pass" fails the
  build naming the file it touched.
* ``test_every_designed_cover_is_registered`` fails a row wearing a designed
  raster that has no entry here, so a NEW hand-made cover has to be written
  down — which is the moment its immutability starts.

Registering a cover is therefore how you protect it, and the digest is not
busywork: it is the difference between "this file exists" (which the older gates
already checked, and which stayed green for months over a stale generation of
share cards) and "this file is the one we drew".

CHANGING ONE ON PURPOSE is a two-line diff — replace the file, update its digest
— and the gate exists to make that deliberate rather than incidental. Nothing
here forbids a redesign; it forbids a redesign nobody noticed.

THE HAZARD THIS WAS WRITTEN FOR IS REAL, not hypothetical.
``localize_covers.ensure_og_twin`` writes ``/covers/<slug>.png``, and two
designed covers — ``baptism-with-the-holy-spirit`` and
``prayer-the-pulse-of-life`` — ARE ``.png`` files at exactly that path. Only an
``if dest.exists()`` stands between the twin writer and a hand-made cover, so
deleting either file and re-running a curation script would have replaced a
designed cover with a machine crop of itself, silently. ``ensure_og_twin`` now
asks this module first.

THAT GUARD IS A LOCAL BACKSTOP, NOT THE PROTECTION. ``/covers/<slug>.png`` has
a SECOND writer — ``frontend/scripts/generate-cover-og.mjs`` — which cannot
import a Python registry and still decides by extension. The digest gate is
what covers both, and every writer after them: it is content-addressed, so it
does not care which tool moved the bytes or what language that tool was written
in. A guard at a call site can only defend the call sites you thought of.

WHY THE TRANSLATIONS NEEDED SOMETHING ELSE
The words are IN these files, so a designed cover cannot serve a Swahili
edition: a scrim is not an eraser, and the prototypes that tried came out with
the English title legible above the translated one (see
``scripts/localize_covers.py``). For sixteen of these works the English edition
therefore wore a photograph while every other language wore a flat coloured
plate — the shelf said, in the one place a reader looks first, that the
translations were the lesser edition.

``DERIVED_GROUND`` is the answer, and it changes nothing about the file it reads
from. For each of those works ``scripts/build_derived_grounds.py`` crops the
band of the designed cover that carries PHOTOGRAPHY AND NO WORDS — below the
title, above the ministry mark, inside the hairline frame — and composes it into
a wordless ground under ``covers/art/``. That is the tier ``BookCover`` already
draws a per-language title over, so every translated edition gets the work's own
artwork with its own title on it, and the English row keeps pointing at the
untouched designed cover.

So a work in ``DERIVED_GROUND`` deliberately wears TWO covers: the hand-made one
in English, and its wordless sibling everywhere else. That is not the drift
``test_translated_editions_wear_their_own_cover`` guards against — the point of
that rule is that no edition wears another edition's WORDS, and a ground with no
words in it cannot.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import NamedTuple

#: Every hand-made cover, by the ``cover_url`` its row wears → SHA-256 of the
#: committed file. Add an entry when you add a cover; change one only when you
#: mean to replace the artwork.
DESIGNED: dict[str, str] = {
    "/covers/baptism-with-the-holy-spirit.png":
        "d7a50b3b4aef331a353c928d60f5a0a4db8328429a9e024e80dab6f11a8d9667",
    "/covers/clothed-with-strength-and-dignity.jpg":
        "818722e5ec6ae8ad955eb88481552b54c8822084238e62af8957274f18a54fe4",
    "/covers/feasting-at-the-table.jpg":
        "75428579274b21090f44604464e1608fa54321307892f01791ac7b1f46a28713",
    "/covers/godliness.jpg":
        "50b72ef83e3f24780d1274148d034ea55317bb5c2d36c1b339d2213c80593dd1",
    "/covers/he-holds-my-tomorrows.jpg":
        "ecc94170eec003af3df0a6cd7de73321f752a18120abba82b96f6e77c8eaf433",
    "/covers/humility-2.jpg":
        "d1a0e7653d874c4df65e1a37e4963724028584faa66ce51d69892acdfa6cc997",
    "/covers/jesus-himself-2.jpg":
        "e40e84e7b60120827a09351a7dc152c7d78a7bab62246cb50382f825ebd29c13",
    "/covers/lord-teach-us-to-pray-2.jpg":
        "d1a60e268eb163232e075407d5b3ca24ee2caf70b056dce1f02ad048117c6da0",
    "/covers/men-and-women-who-gave-everything-2.jpg":
        "40ae45aab2c1e92e509dc5b655d7ca07c53f42988a3a0907581f2e4591807bca",
    "/covers/men-of-prayer-2.jpg":
        "3be5d85a8b6ab71b7b8d0d7d88a43e10d1d39dddbe52382c57eea5fa25db4ac1",
    "/covers/men-who-moved-heaven.jpg":
        "46b871cd0fe570bf38f6f6fe628064d7643d5d5baee2f77777331c347fd4ab99",
    "/covers/men-who-tended-the-flock-2.jpg":
        "e051d1a0e83eb33f8254ef9a68fbe79c2cc6f0ba3b271a0a10de15a77a5eb1b5",
    "/covers/prayer-the-pulse-of-life.png":
        "29030df615f17c8cf480f36a1bf738c14a7407cf9cc51c0e178cc480386cc3e1",
    "/covers/purity-of-heart.jpg":
        "f3659ad885cb95c3bf8f0d954d45c078c709674407fd560fcc4cf96d1bd60554",
    "/covers/rise-up-men-of-god-2.jpg":
        "183c80450cd76f8c3522bdae6a8ca1490896ba71656cefbd645b741387237d31",
    "/covers/soar-like-the-eagle-3.jpg":
        "2db8925dd6782464cd895d241508324b7955d9678acf8f6afd33d4c4a5d2c107",
    "/covers/stepping-stones-2.jpg":
        "f3564c524858961bbe55d4a7b900f70b88589a349ca8ad56f9b94ef92bce15da",
    "/covers/talks-to-the-farmer.jpg":
        "120ca61d19bce6c692bc1bc8c9eecc38543224945496fbb427f0c1ecdbf6ed48",
    "/covers/the-christians-secret-of-a-happy-life-4.jpg":
        "d9b9836cb2eaa1cd8d669cb3f2fc880ed884c0ab020e13afb7fde2e6ea2685e5",
    "/covers/the-god-of-all-comfort.jpg":
        "d2917c2f827ac26b0570ef7995dfe2c7bc0560ad81e4ccf1937dbc265b1a9dcd",
    "/covers/the-inner-chamber.jpg":
        "524abc40f0fb242aaba695875851382a6d98481799a6178304d47c8befbde671",
    "/covers/the-key-in-my-hand.jpg":
        "3e1a5e8c26072334f96a3a1039808ab24d0e749aad148613c23948c987fb1b62",
    "/covers/the-masters-indwelling.jpg":
        "389d6f2248dd21120d79be7def954bebe8ed895a93b0517eefa45e6ee8715949",
    "/covers/the-person-and-work-of-the-holy-spirit.jpg":
        "854342772afb4da0ac470fdc3b92b253794051942e82bde23a3681388c7bab60",
    "/covers/the-secret-of-guidance.jpg":
        "a990801a9928f654ed2da0760f6d7c0a64d974e24d72d3ff9485fc05ac4ddfc6",
    "/covers/the-unselfishness-of-god.jpg":
        "da76ca7d2a047bac2463d0ab58af54f40d987ce0bf5127001d102d553f8f4078",
    "/covers/women-who-moved-heaven-2.jpg":
        "471f2e18290bd563bab4220c6664aea4adebbcc06e1c07749f9843ef805cad0f",
}


class Ground(NamedTuple):
    """How one designed cover is cropped into a wordless ground.

    The recipe lives here rather than in the script that draws it, for the
    reason ``curated_art.CURATED`` does: what a work's artwork should be is
    catalogue knowledge, and a script is a thing you run. Keeping it here also
    means there is ONE table keyed by these sixteen slugs instead of two that a
    hand-written consistency check has to hold together.

    No rule finds these numbers, which is why they are written down one work at
    a time: the ministry mark sits at 78% on one cover and over the subject on
    the next, and ``jesus-himself-2`` has a hairline rule at 0.594 that a crop
    from 0.56 quietly included.
    """

    #: The words-free band, as fractions of the designed cover's height. Every
    #: one of these excludes the byline, the title, any rule, and the Ochorus or
    #: garethevansministries.org mark at the foot.
    top: float
    bottom: float
    #: How far in from each side, clearing the designed cover's own hairline
    #: frame — `BookCover` draws a frame of its own, and two of them a few
    #: pixels apart is worse than either. A full-bleed photograph takes the 0.02
    #: that only trims the edge.
    inset: float
    #: Gamma on the band, against the art scrim's 36-64% black. 1.0 leaves it
    #: alone. The curated tier needs none because a museum landscape is
    #: daylight; these are ministry photographs chosen to be moody.
    lift: float
    #: How much of the band's top the out-of-focus extension is built from. The
    #: default suits a photograph whose top is already background; a silhouette
    #: against a sunset wants less, or its subject blurs upward into the sky it
    #: was cut out of.
    sky: float = 0.35
    #: The ``DESIGNED`` digest of the cover this ground was actually cut from.
    #:
    #: WHY A GROUND RECORDS ITS SOURCE. Replacing a hand-made cover is meant to
    #: be a two-line diff — new file, new digest — and for the eleven
    #: English-only works it is. For these sixteen it cannot be: the ground and
    #: the og twin were cut from the OLD artwork, and every gate stays green
    #: over them. ``test_designed_covers_are_never_changed`` re-reads whatever
    #: digest you just wrote, the twin-staleness gate deliberately skips
    #: designed rasters, and both writers bail on ``dest.exists()``. Every
    #: translated edition would keep the retired photograph, silently.
    #:
    #: So this pins what the committed ground was MADE FROM, the way
    #: ``og-manifest.json`` pins what a share card was made from — and for the
    #: same reason, which that file learned the hard way: existence was never
    #: what went wrong, staleness was.
    source: str = ""


#: The works whose translations wear a ground cropped from the designed English
#: cover of the same name, and the crop that makes it. Only the sixteen that HAVE
#: translations are here — a work read in one language needs no language-neutral
#: ground, and drawing one nobody points at is how a file with no reader gets
#: committed.
#:
#: The designed cover each is cut from is NOT restated here: it is
#: ``designed_url(slug)``, derived from ``DESIGNED`` above, so replacing one of
#: those files with a different extension stays the two-line diff this module
#: advertises rather than quietly needing a third edit here.
DERIVED_GROUND: dict[str, Ground] = {
    "baptism-with-the-holy-spirit": Ground(0.42, 0.83, 0.11, 1.15,
        source="d7a50b3b4aef331a353c928d60f5a0a4db8328429a9e024e80dab6f11a8d9667",
    ),
    "clothed-with-strength-and-dignity": Ground(0.40, 0.78, 0.10, 1.45,
        source="818722e5ec6ae8ad955eb88481552b54c8822084238e62af8957274f18a54fe4",
    ),
    "godliness": Ground(0.44, 0.75, 0.09, 1.85,
        source="50b72ef83e3f24780d1274148d034ea55317bb5c2d36c1b339d2213c80593dd1",
    ),
    "he-holds-my-tomorrows": Ground(0.46, 0.88, 0.02, 1.10, sky=0.20,
        source="ecc94170eec003af3df0a6cd7de73321f752a18120abba82b96f6e77c8eaf433",
    ),
    "humility-2": Ground(0.38, 0.80, 0.11, 1.20,
        source="d1a0e7653d874c4df65e1a37e4963724028584faa66ce51d69892acdfa6cc997",
    ),
    # Below the rule at 0.594 there is only 18% of the cover left, which at the
    # usual inset came out five parts blur to one part picture; the wide inset
    # crops IN to the cross's stem. At 0.22 that landed the sharp band at a
    # third of the plate — the note this replaces — and the rest stayed blur.
    # 0.38 is the same lever taken to where it ENDS: a band this narrow is
    # taller than 4:3 once widened, so it fills the plate and there is no blurred
    # extension at all. What it costs is width, and what it buys is that a
    # translated reader sees the wall's real texture rather than a teal wash.
    # The cross does not survive either crop; it is behind the title.
    "jesus-himself-2": Ground(0.60, 0.82, 0.38, 1.80,
        source="e40e84e7b60120827a09351a7dc152c7d78a7bab62246cb50382f825ebd29c13",
    ),
    # A true silhouette: nearly black before the scrim, so the heaviest lift
    # here and still the darkest ground of the sixteen.
    "lord-teach-us-to-pray-2": Ground(0.44, 0.84, 0.03, 2.50,
        source="d1a60e268eb163232e075407d5b3ca24ee2caf70b056dce1f02ad048117c6da0",
    ),
    "prayer-the-pulse-of-life": Ground(0.56, 0.84, 0.11, 1.50,
        source="29030df615f17c8cf480f36a1bf738c14a7407cf9cc51c0e178cc480386cc3e1",
    ),
    "purity-of-heart": Ground(0.55, 0.79, 0.12, 2.00,
        source="f3659ad885cb95c3bf8f0d954d45c078c709674407fd560fcc4cf96d1bd60554",
    ),
    # Full-bleed at 0.02 took the whole stream and, being a 3:4 crop of a 3:4
    # cover, came out three parts blurred extension to one part water. Cropping
    # IN to the centre 40% makes the band taller than the plate, so every pixel
    # is photograph: the stones and the current are sharp instead of a wash.
    "stepping-stones-2": Ground(0.28, 0.63, 0.30, 1.15,
        source="f3564c524858961bbe55d4a7b900f70b88589a349ca8ad56f9b94ef92bce15da",
    ),
    "talks-to-the-farmer": Ground(0.46, 0.78, 0.09, 1.45,
        source="120ca61d19bce6c692bc1bc8c9eecc38543224945496fbb427f0c1ecdbf6ed48",
    ),
    "the-god-of-all-comfort": Ground(0.50, 0.78, 0.11, 1.10,
        source="d2917c2f827ac26b0570ef7995dfe2c7bc0560ad81e4ccf1937dbc265b1a9dcd",
    ),
    # The doorway itself is an unlit room — a black rectangle at any lift its
    # highlights survive — so this takes the lintel and sandstone ABOVE it,
    # under the byline. The one work here whose ground is not its cover's
    # subject, because its subject is an absence of light.
    "the-inner-chamber": Ground(0.13, 0.33, 0.10, 1.60,
        source="524abc40f0fb242aaba695875851382a6d98481799a6178304d47c8befbde671",
    ),
    "the-key-in-my-hand": Ground(0.26, 0.60, 0.02, 1.05,
        source="3e1a5e8c26072334f96a3a1039808ab24d0e749aad148613c23948c987fb1b62",
    ),
    "the-person-and-work-of-the-holy-spirit": Ground(0.41, 0.82, 0.10, 1.00,
        source="854342772afb4da0ac470fdc3b92b253794051942e82bde23a3681388c7bab60",
    ),
    "the-unselfishness-of-god": Ground(0.44, 0.80, 0.09, 1.15, sky=0.15,
        source="da76ca7d2a047bac2463d0ab58af54f40d987ce0bf5127001d102d553f8f4078",
    ),
}

#: ``DESIGNED`` re-indexed by slug — the key every OTHER cover registry uses
#: (``CURATED``, ``emblem_for_book``, ``art_url``, ``cover_path``), so a caller
#: holding a slug does not have to guess at an extension to ask a question here.
#: Two of these covers are ``.png`` and twenty-five are ``.jpg``, which is
#: exactly the detail a second copy gets wrong the first time one is replaced.
#:
#: A re-index, not a second source of truth: every ``DESIGNED`` key is
#: ``/covers/<slug>.<ext>`` and the stems are unique.
#: Only covers directly under ``/covers/`` are indexed. A translated edition is
#: allowed designed artwork of ITS own one day, at ``/covers/<lang>/<slug>.<ext>``
#: (two gates say so explicitly), and that file's stem is the same slug — so
#: indexing it here would let ``/covers/sw/humility-2.jpg`` silently win the key
#: belonging to ``/covers/humility-2.jpg`` and hand every consumer the wrong
#: cover. ``test_designed_covers_index_cleanly`` fails on a collision rather
#: than letting one entry quietly replace another.
DESIGNED_BY_SLUG: dict[str, str] = {
    url.removeprefix("/covers/").rsplit(".", 1)[0]: url
    for url in DESIGNED
    if "/" not in url.removeprefix("/covers/")
}


def is_designed(cover_url: str) -> bool:
    """Is this URL a registered hand-made cover — one no tool may rewrite?

    Asked by ``ensure_og_twin`` before it writes. Not a guess from the
    extension: a ``.png`` under ``/covers/`` is a designed cover for two works
    and a generated og twin for thirty, and only the registry can tell those
    apart.
    """
    return cover_url in DESIGNED


def digest(path: Path) -> str:
    """The SHA-256 of a file, as ``DESIGNED`` records it."""
    return hashlib.sha256(path.read_bytes()).hexdigest()
