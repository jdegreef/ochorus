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

When a designed cover has no picture that survives losing its words — a void
behind a doorway, a blur behind a mark — there is nothing to crop, and the work
takes a museum painting as its ground instead (``curated_art.CURATED_GROUND``).
Same shape, different source; ``covers.keeps_english_designed`` is true of both.

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
    "/covers/a-retrospect-children.jpg":
        "df182354203c95fb652f66605aca61511ebf76b1c2f3a4f1dc4930249cfde4c7",
    "/covers/a-retrospect-teens.jpg":
        "4b6813f19ad8ca22775338f4ed812187306dd7e3b9a9f497a36f27aa6ea0f444",
    "/covers/amanda-smith-autobiography-children.jpg":
        "8a499dcd89376c202a5eaf63356f33b66b350eff6555b59f7992585a94ded811",
    "/covers/amanda-smith-autobiography-teens.jpg":
        "e8edd6cb79044d4d6ee9d5552e641256c0b4f75a35c6e6c7488b43cb475cb5fc",
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
    "/covers/pilgrims-progress-children.jpg":
        "9250c3a997cdeff08f92539bc745ab5ee7adb483788d16e610c2b924125c98fe",
    "/covers/pilgrims-progress-teens.jpg":
        "5e38bc71fc780ffdba0c2c3ee3df4276c2f47e5f6f6d9323667005641a3df66a",
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
    "/covers/talks-to-the-farmer-children.jpg":
        "bdc9b9dcb04b2e12fa7699fe5c101e55bf44864693a27cb3b25122e7c0cf219c",
    "/covers/talks-to-the-farmer-teens.jpg":
        "476d31c3de2cf2a401fe72bc31f1faa26b96128a0834610a7f7a9ea257591d2c",
    "/covers/the-christians-secret-of-a-happy-life-4.jpg":
        "d9b9836cb2eaa1cd8d669cb3f2fc880ed884c0ab020e13afb7fde2e6ea2685e5",
    "/covers/the-god-of-all-comfort.jpg":
        "d2917c2f827ac26b0570ef7995dfe2c7bc0560ad81e4ccf1937dbc265b1a9dcd",
    "/covers/the-inner-chamber.jpg":
        "524abc40f0fb242aaba695875851382a6d98481799a6178304d47c8befbde671",
    "/covers/the-key-in-my-hand.jpg":
        "3e1a5e8c26072334f96a3a1039808ab24d0e749aad148613c23948c987fb1b62",
    "/covers/the-life-of-trust-children.jpg":
        "71984f6a7041ad1bd19388512f88044e57e62efc49823a2f38bc2c2c7e834ba1",
    "/covers/the-life-of-trust-teens.jpg":
        "65c2b20e3fa9bdd79b0ae99354579b4a81ade87f573cba9e7d9db495bbe892cf",
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


class Erase(NamedTuple):
    """A box of lettering to paint out of a designed cover before it is cropped.

    Fractions of the designed cover, like ``Ground``'s band. Only the INK in the
    box is repainted — pixels darker (or lighter) than their neighbourhood —
    from the picture around it, so a sky keeps its gradient and a stone its
    edge. That makes it an eraser for thin type over a quiet ground — a
    subtitle, a ministry URL, a hairline — and not for a title set over a
    subject: ``localize_covers`` learned that a scrim cannot hide one, and a
    repaint of a subject is a guess about what was behind it.

    It exists because a band is a rectangle and type is not. The eagle on
    ``soar-like-the-eagle-3`` flies between the lines of its own title, so no
    rectangle holds the bird without letters; erasing the letters around it is
    the only crop in which the translations keep the book's picture.
    """

    x0: float
    y0: float
    x1: float
    y1: float
    #: "dark" for ink darker than what it is set on, "light" for lighter, "any"
    #: for a mark drawn in both — the Ochorus lockup prints white on a dark
    #: photograph and grey on a pale one.
    ink: str = "dark"
    #: Erase only type-thin ink (the default), leaving any broad shape the
    #: contrast test also catches — a branch, the bright side of a page edge.
    #: False erases everything it finds, for a hairline that touches such a
    #: shape and would otherwise be kept as part of it.
    thin: bool = True


class Ground(NamedTuple):
    """How one designed cover is cropped into a wordless ground.

    The recipe lives here rather than in the script that draws it, for the
    reason ``curated_art.CURATED`` does: what a work's artwork should be is
    catalogue knowledge, and a script is a thing you run. Keeping it here also
    means there is ONE table keyed by these fourteen slugs instead of two that a
    hand-written consistency check has to hold together.

    No rule finds these numbers, which is why they are written down one work at
    a time: the ministry mark sits at 78% on one cover and over the subject on
    the next, and ``jesus-himself-2`` has a hairline rule at 0.594 that a crop
    from 0.56 quietly included.
    """

    #: The words-free band, as fractions of the designed cover's height. Every
    #: one of these excludes the byline, the title, any rule, and the Ochorus or
    #: garethevansministries.org mark at the foot — or ``erase`` paints the
    #: lettering it cannot exclude out of it first.
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
    #: The brightest a pixel may come out, out of 255. The lift cannot help a
    #: blown highlight — a gamma leaves 255 at 255 — so a ground whose sun or
    #: bare white key sits where the title goes needs its top end brought down
    #: before any scrim strength the stylesheet can draw will carry white type.
    peak: int = 255
    #: How much of the band's top the out-of-focus extension is built from. The
    #: default suits a photograph whose top is already background; a silhouette
    #: against a sunset wants less, or its subject blurs upward into the sky it
    #: was cut out of.
    sky: float = 0.35
    #: How much of the plate's height, at the foot, continues the band's bottom
    #: out of focus instead of showing it. `BookCover` centres the title and
    #: sets the Ochorus mark at the foot, so a band that ends on its subject —
    #: two walkers, a key in a hand — puts the mark on top of it. A foot lifts
    #: the subject into the clear space between the two.
    foot: float = 0.0
    #: Lettering painted out before the crop (see ``Erase``), which is what
    #: lets a band reach past a subtitle or a URL instead of stopping at it.
    erase: tuple[Erase, ...] = ()
    #: The ``DESIGNED`` digest of the cover this ground was actually cut from.
    #:
    #: WHY A GROUND RECORDS ITS SOURCE. Replacing a hand-made cover is meant to
    #: be a two-line diff — new file, new digest — and for the eleven
    #: English-only works it is. For these fourteen it cannot be: the ground and
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
#: cover of the same name, and the crop that makes it. Only works that HAVE
#: translations are here — a work read in one language needs no language-neutral
#: ground, and drawing one nobody points at is how a file with no reader gets
#: committed.
#:
#: NOT every translated work with a designed cover, which is what membership
#: here looks like from the outside. Two of them had nothing croppable left
#: once the words were gone — a black doorway and a blur — and take a museum
#: painting instead (``curated_art.CURATED_GROUND``). So the rule is "designed
#: cover, and translations, AND a picture in it that survives losing the
#: words", and ``test_a_translated_designed_work_has_a_ground`` accepts either
#: table.
#:
#: The designed cover each is cut from is NOT restated here: it is
#: ``designed_url(slug)``, derived from ``DESIGNED`` above, so replacing one of
#: those files with a different extension stays the two-line diff this module
#: advertises rather than quietly needing a third edit here.
#
#: WHERE A SUBJECT SHOULD LAND DEPENDS ON THE AUTHOR'S LAYOUT
#: (``coverLayouts.AUTHOR_LAYOUT``), not only on the framed composition. Framed:
#: clear of the centred title and of the mark at ~0.9. R. A. Torrey's
#: ``diagonal`` shows only the top ~40% of the ground, so his doves are lifted
#: there with a large ``foot``. Andrew Murray's ``wash`` fades the top into
#: paper, so his subjects stay LOW. Spurgeon's ``band`` shows the lower half.
#: Render the real cover before trusting a crop (see the level-up-cover skill).
#:
#: The Ochorus mark at a designed cover's foot is erased with one box —
#: ``Erase(0.36, 0.82, 0.64, 0.935, "any", thin=False)`` — rather than cropped
#: above: the lockup's quill reaches up to ~0.83, and it prints white on a dark
#: photograph and grey on a pale one.
DERIVED_GROUND: dict[str, Ground] = {
    "baptism-with-the-holy-spirit": Ground(0.41, 0.84, 0.11, 1.15, foot=0.40,
        source="d7a50b3b4aef331a353c928d60f5a0a4db8328429a9e024e80dab6f11a8d9667",
    ),
    "clothed-with-strength-and-dignity": Ground(0.41, 0.83, 0.10, 1.45, foot=0.10,
        source="818722e5ec6ae8ad955eb88481552b54c8822084238e62af8957274f18a54fe4",
    ),
    # The open Bible on the wooden table, from just under the lower title rule
    # (~0.455) to just above the frame's foot (~0.945). The designed cover's own
    # hairline frame (x ~0.08 and ~0.92) and its Ochorus mark (~0.80-0.87) sit
    # INSIDE that band, and cropping around them — the old 0.07 inset and 0.83
    # foot — left a stripe of the frame down the left edge and the top of the
    # mark along the bottom. Erased instead, the crop takes the whole spread
    # full-bleed, at the least magnification this cover allows.
    "feasting-at-the-table": Ground(0.47, 0.93, 0.02, 1.15, sky=0.25, erase=(
        Erase(0.06, 0.45, 0.10, 0.95, "light", thin=False),
        Erase(0.90, 0.45, 0.94, 0.95, "light", thin=False),
        Erase(0.36, 0.79, 0.64, 0.885, "light"),
    ),
        source="75428579274b21090f44604464e1608fa54321307892f01791ac7b1f46a28713",
    ),
    "godliness": Ground(0.36, 0.84, 0.09, 1.85, foot=0.08,
        source="50b72ef83e3f24780d1274148d034ea55317bb5c2d36c1b339d2213c80593dd1",
    ),
    # Two walkers climbing a dune, from under the subtitle (~0.395) to their
    # footprints above the URL (~0.925). The band used to stop at their feet,
    # which put `BookCover`'s Ochorus mark on top of them; a small foot lifts
    # them into the gap between the title and the mark.
    "he-holds-my-tomorrows": Ground(0.40, 0.915, 0.02, 1.10, sky=0.20, foot=0.04,
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
    # here and still the darkest ground of the fourteen.
    "lord-teach-us-to-pray-2": Ground(0.44, 0.84, 0.03, 2.50,
        source="d1a60e268eb163232e075407d5b3ca24ee2caf70b056dce1f02ad048117c6da0",
    ),
    # A photograph of hands on an open Bible, a finger following the text. The
    # title fills the upper third and the "Volume 2 …" subtitle ends by ~0.65;
    # the words-free picture is the open page spread below it, taken past the
    # Ochorus mark (erased) to the frame's foot so the spread is not a sliver.
    # Two shepherds walking their flock through dust at sunset. The words-free
    # band runs from under the "10 Mighty Christian Pastors" subtitle (~0.51)
    # to the frame's foot (~0.935); the 0.09 inset crops inside the white
    # hairline frame (x ~0.08 / ~0.92) instead of erasing it over pale sheep.
    # The Ochorus lockup sits on the dust between the sheep, painted out.
    "men-who-tended-the-flock-2": Ground(0.52, 0.93, 0.09, 1.10, sky=0.25, foot=0.05,
        erase=(Erase(0.40, 0.82, 0.60, 0.90, "light"),),
        source="e051d1a0e83eb33f8254ef9a68fbe79c2cc6f0ba3b271a0a10de15a77a5eb1b5",
    ),
    "men-and-women-who-gave-everything-2": Ground(0.62, 0.93, 0.08, 1.12, sky=0.22,
        erase=(Erase(0.36, 0.82, 0.64, 0.935, "any", thin=False),),
        source="40ae45aab2c1e92e509dc5b655d7ca07c53f42988a3a0907581f2e4591807bca",
    ),
    # Two men praying over an open Bible, from just under the subtitle (~0.485)
    # to the frame's foot (~0.94), the subtitle's hairline rule (~0.53) erased; the 0.09 inset crops inside the
    # hairline frame (x ~0.08 / ~0.92). The Ochorus mark sits on their hands
    # and the page, painted out.
    "men-of-prayer-2": Ground(0.49, 0.93, 0.09, 1.12, sky=0.12,
        erase=(Erase(0.15, 0.515, 0.85, 0.55, "light"),
               Erase(0.36, 0.82, 0.64, 0.935, "any", thin=False)),
        source="3be5d85a8b6ab71b7b8d0d7d88a43e10d1d39dddbe52382c57eea5fa25db4ac1",
    ),
    "purity-of-heart": Ground(0.54, 0.93, 0.09, 2.00,
        erase=(Erase(0.36, 0.82, 0.64, 0.935, "any", thin=False),),
        source="f3659ad885cb95c3bf8f0d954d45c078c709674407fd560fcc4cf96d1bd60554",
    ),
    # Four men in silhouette, arms raised against a sea sunset — the words-free
    # band from just under the title (~0.46) to the frame's foot. A silhouette
    # against a bright sky wants a low sky so the men don't blur upward into it,
    # and a small foot lifts them clear of the Ochorus mark BookCover sets at the
    # plate's foot. The ministry lockup sits at the lower right, painted out.
    "rise-up-men-of-god-2": Ground(0.46, 0.93, 0.08, 1.10, sky=0.20, foot=0.05,
        erase=(Erase(0.37, 0.865, 0.63, 0.96, "any", thin=False),),
        source="183c80450cd76f8c3522bdae6a8ca1490896ba71656cefbd645b741387237d31",
    ),
    # The whole stream between the title (~0.20) and the URL (~0.93), with the
    # "Walking by Faith" subtitle painted out of the water. The last recipe
    # cropped IN to the centre 40% to avoid a blurred extension, which cost a
    # 3.3x enlargement of a 443px source — every stone came out soft. This one
    # is 1.4x and still needs no extension. 0.03 clears the rounded corners.
    "stepping-stones-2": Ground(0.21, 0.92, 0.03, 1.15,
        erase=(Erase(0.18, 0.63, 0.80, 0.73, "light"),),
        source="f3564c524858961bbe55d4a7b900f70b88589a349ca8ad56f9b94ef92bce15da",
    ),
    "talks-to-the-farmer": Ground(0.48, 0.93, 0.09, 1.45,
        erase=(Erase(0.36, 0.82, 0.64, 0.935, "any", thin=False),),
        source="120ca61d19bce6c692bc1bc8c9eecc38543224945496fbb427f0c1ecdbf6ed48",
    ),
    # A golden sunset with an eagle. The bird flies between the lines of the
    # title, so the old crop settled for the sky below the subtitle — and the
    # translations of "Soar Like the Eagle" had no eagle. The ends of "LIKE
    # THE" and "EAGLE" and the subtitle are erased instead, and the band starts
    # just above the bird so it flies ABOVE the translated title, not behind
    # it; the foot continues the haze under the mark. The sun sits where the
    # title goes, so its top end is brought down (`peak`).
    "soar-like-the-eagle-3": Ground(
        0.217, 0.87, 0.07, 1.0, sky=0.4, foot=0.19, peak=240, erase=(
        Erase(0.33, 0.215, 0.66, 0.315),
        Erase(0.375, 0.325, 0.62, 0.435),
        Erase(0.19, 0.56, 0.79, 0.63),
        ),
        source="2db8925dd6782464cd895d241508324b7955d9678acf8f6afd33d4c4a5d2c107",
    ),
    "the-god-of-all-comfort": Ground(0.51, 0.93, 0.15, 1.10,
        erase=(Erase(0.36, 0.82, 0.64, 0.935, "any", thin=False),),
        source="d2917c2f827ac26b0570ef7995dfe2c7bc0560ad81e4ccf1937dbc265b1a9dcd",
    ),
    # A key held out in two hands, from under the title (~0.21) to above the
    # URL (~0.93), with "Opening Heaven" painted out of the sleeve. The old band
    # was a third of that height and came out a pink wash with the key under
    # the Ochorus mark; the foot lifts the key's bow into the space above the
    # translated title. A pale photograph, so its top end comes down (`peak`).
    "the-key-in-my-hand": Ground(0.22, 0.915, 0.02, 1.05, foot=0.11, peak=240,
        erase=(Erase(0.25, 0.72, 0.80, 0.80),),
        source="3e1a5e8c26072334f96a3a1039808ab24d0e749aad148613c23948c987fb1b62",
    ),
    # A dusk seascape: the band between the lower title rule (~0.57) and the
    # Ochorus wordmark on the water (~0.88) is pure sunset over sea — sky
    # gradient into the sun's glow, no words. Full-bleed photo, so inset 0.02.
    "the-masters-indwelling": Ground(0.58, 0.83, 0.02, 1.12, sky=0.30,
        source="389d6f2248dd21120d79be7def954bebe8ed895a93b0517eefa45e6ee8715949",
    ),
    # The title and byline fill the top and middle over two jumping figures; the
    # words-free picture is the band BELOW the title (~0.56) and above the Ochorus
    # mark at the foot (~0.86) — wet sand, the sunset's reflection and the lower
    # silhouettes. inset 0.05 clears the cover's white hairline frame; the band is
    # a silhouette against a sunset, so a shallow sky extension (0.22) keeps the
    # figures from blurring up into the sky, and a slight lift carries white type.
    "the-christians-secret-of-a-happy-life-4": Ground(0.56, 0.82, 0.06, 1.15, sky=0.22,
        source="d9b9836cb2eaa1cd8d669cb3f2fc880ed884c0ab020e13afb7fde2e6ea2685e5",
    ),
    "the-person-and-work-of-the-holy-spirit": Ground(0.41, 0.82, 0.10, 1.00, foot=0.45,
        source="854342772afb4da0ac470fdc3b92b253794051942e82bde23a3681388c7bab60",
    ),
    # The staircase and title fill the middle; the words-free picture is the
    # luminous band ABOVE the title — the radiant gate, the cross and the sunlit
    # clouds — from just inside the frame (~0.05) to just above "The Secret of"
    # (~0.26). The band is very bright (a central light-shaft), so lift 0.5 pulls
    # the sky down to a teal-gold dusk that carries white type (scrim 0.60); the
    # top is cloud, so a shallow sky extension.
    "the-secret-of-guidance": Ground(0.05, 0.26, 0.10, 0.5, sky=0.28,
        source="a990801a9928f654ed2da0760f6d7c0a64d974e24d72d3ff9485fc05ac4ddfc6",
    ),
    "the-unselfishness-of-god": Ground(0.44, 0.74, 0.09, 1.15, sky=0.15,
        erase=(Erase(0.15, 0.30, 0.85, 0.47),),
        source="da76ca7d2a047bac2463d0ab58af54f40d987ce0bf5127001d102d553f8f4078",
    ),
    # The title, byline and subtitle fill the top half over a darkened worship
    # scene; the words-free picture is the band BELOW the subtitle (~0.58) and
    # above the Ochorus wordmark at the foot (~0.88) — the praying women with
    # hands raised. Indoor scene, so no sky extension.
    "women-who-moved-heaven-2": Ground(0.59, 0.93, 0.10, 1.20,
        erase=(Erase(0.36, 0.82, 0.64, 0.935, "any", thin=False),),
        source="471f2e18290bd563bab4220c6664aea4adebbcc06e1c07749f9843ef805cad0f",
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
