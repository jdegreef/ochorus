# waiting-on-god.uk — scripture provenance, recorded as each chapter lands
# mined = Kulish verbatim, expanded from bible_uk.json by nodes.expand()
# self  = rendered by the translator; the reviewer's actual task

ch03 PSA 62:1   mined
ch04 GEN 49:18  mined
ch05 PSA 104:27,28 mined
ch06 PSA 145:14,15 mined
ch07 PSA 25:4,5 mined ; PSA 25:9 mined ("the meek will He guide")
ch08 PSA 25:3   mined (epigraph)
ch08 PSA 25:3   SELF — Murray uses it as a PETITION ("Let none that wait on
     Thee be ashamed"); Kulish is indicative ("all who rely on thee shall not
     be put to shame"). The prayer form is the translator's, deliberately.
ch08 PSA 104:27 + PSA 145:15  mined, but SPLICED — the English itself joins
     the two halves; each half is verbatim, the join is not a single verse.
ch08 PSA 27:14  mined ; JHN 17:26, JHN 15:9, JHN 13:34 mined (word ranges)
ch09 PSA 25:21  mined (epigraph) ; PSA 25:5, 26:1, 26:11, 36:10 mined
ch09 SELF — "На Тебе я чекаю ввесь день; я чекаю на Тебе" is Murray's own
     emphatic restatement with italics, not a quotation.
ch10 PSA 27:14 mined ; PSA 62:1 mined
ch11 PSA 31:24 mined (fragments split across <i>, replaced from the file)
ch12 PSA 33:18-22 mined (epigraph, one word-range per line) ; PSA 33:18,19,20,22
     re-quoted in the prose, mined ; PSA 62:5|1-6 (closing refrain)
ch12 REV 15:4, REV 19:5, DEU 28:58, 1CO 1:29, ISA 25:9 mined (word ranges)
ch12 ISA 25:9 CORRECTED: the ebible ukr_pan file reads "спаннєм" (=sleeping);
     Kulish writes "спасеннєм" in the other 14 places the word occurs, so the
     hapax is an upstream typo. Recorded in nodes.FIXES with that count.

## Repairs to already-gated chapters (found by a doubled-punctuation scan)
ch08-ch11 closing refrain had expanded the WHOLE of PSA 62:5, adding a clause
  the English does not quote, and ended ".!" — now {{PSA 62:5|1-6}}, matching
  ch03-ch07. ch10 "в серцї,," and ch11 "на Господа.." de-doubled.
  Ratios after: ch08 0.855, ch09 0.834, ch10 0.872, ch11 0.816 (all in band).
ch13 PSA 37:7,9 mined (epigraph + three re-quotes) ; LUK 21:19, HEB 10:36,
     JAS 1:4, ROM 9:16, PHP 4:7, ISA 60:22, PSA 62:5 mined (word ranges)
ch13 JHN 1:13 mined but SPLICED — Murray quotes "were born not of the will of
     the flesh...", omitting "of blood"; the uk splices Kulish's own "не" to
     the same continuation, mirroring the omission rather than tidying it.
ch13 SELF — the marginal readings "Мовчи перед Господом" / "Утихомирся перед
     Господом" render Murray's note on the ENGLISH margin and R.V.; Kulish's
     own line ("Вповай тихим серцем на Господа") already carries the sense,
     so the glosses are the translator's, not a second Ukrainian version.
ch14 PSA 37:34 mined (epigraph + four re-quotes) ; ISA 64:5 mined (the italic
     falls on "на дорогах своїх", where the English italicises "Thee in Thy
     ways" — Kulish's word order will not carry the pronoun into the span)
ch14 the long psalm quotation is a COMPOSITE Murray builds himself out of
     PSA 37:1,3,7,8,27,28,29,31 — each fragment is Kulish verbatim, the
     stitching is his. PSA 37:28 is further compressed ("Господь" + "не покине
     преподобних"), mirroring his own elision.
ch15 PSA 39:7,8 mined (epigraph + four re-quotes) ; PSA 78:19,20 mined
     (Israel's doubt) ; PSA 27:14 mined (closing). EPH 3:16,20 and 1CO 2:9 are
     ALLUSIONS in Murray's own prose, unquoted in the English — rendered as
     prose here too, not set as scripture.
ch16 PSA 40:1,2,3 mined (epigraph + the testimony) ; PSA 62:1,2 mined ;
     COL 1:11 mined, split around Murray's own interjection "unto all—what?"
ch16 2TH 3:5 mined but SPLICED — Murray quotes only the second half ("into
     the patience of Christ"); Kulish carries both halves in one sentence, so
     the uk joins "Господь же нехай направить серця ваші" to "і в терпіннє
     Христове", reproducing his elision rather than quoting past it.
ch17 PSA 106:13 mined (epigraph + three re-quotes) ; ACT 10:44 mined ;
     ACT 10:33 mined — the two italic spans land on exactly the phrases the
     English italicises ("before God" / "of God" -> "перед Богом" / "від Бога").
ch17 TENSION FOR THE REVIEWER — Kulish renders "counsel" in PSA 106:13 as
     "присуд" (verdict), but uses "рада" for the same idea elsewhere (EPH 1:11,
     "по радї волї своєї"). The whole chapter turns on the word. The quotes
     keep "присуд" verbatim; the prose and the chapter title use "рада". The
     seam is visible and deliberate — a native reader may want it handled
     differently, but silently amending Kulish is not an option.
ch18 PSA 130:5,6 mined (epigraph) ; ISA 60:20 mined ; PSA 62:5 (refrain)
ch18 PSA 130:6 REORDERED in the prose — Murray inverts the verse ("More than
     watchmen for the morning, my soul waiteth for the Lord"); the uk inverts
     Kulish's two halves the same way and lower-cases the joint.
ch18 2CO 4:6 mined but SPLICED twice — Murray quotes "God has shined in our
     hearts to give the light", cutting Kulish's single sentence; the uk joins
     "Бог" to "засьвітив у серцях наших...", reproducing the cut.
ch18 ratio 0.806 sits exactly on the band floor; checked node by node against
     the English — nothing is dropped, the compression is real (no articles,
     fewer prepositional chains). Longest chapter in the book at 1001w.
ch19 ISA 8:17 mined (epigraph + three re-quotes) ; PSA 130:5,6 mined (closing)
ch19 "orthodox creeds" -> "правовірними символами віри", NOT "православними":
     Murray is contrasting Protestant churches with the Greek and Roman ones a
     line earlier, so the Eastern-Orthodox word would reverse his sentence.
ch20 ISA 25:9 mined (epigraph, twice re-quoted whole) ; ACT 10:33 mined.
     Murray compresses the verse to "Lo, this is our God; this is the Lord!",
     skipping its middle; the uk joins the same two fragments.
ch21 ISA 26:8,9 / ISA 30:18 mined (the two epigraphs) ; MAL 3:2, ISA 64:1-2,
     NUM 10:35, ISA 1:27 mined. ISA 26:8 is spliced to drop "Господи", which
     Murray's own re-quote drops. ISA 64:1+64:2 join two verses as he does.
ch22 ISA 30:18 mined (epigraph + four re-quotes) ; JAS 5:7, LAM 3:25 mined.
ch23 ISA 40:27-31 mined ; PRO 20:29, DEU 32:11,12 mined. The four italic spans
     in the eagle passage land on the same words the English italicises.
ch23 digit WARN is the Kulish book naming: Deuteronomy is "5 Мойсея", so the
     citation carries a 5 the English "(Deut. 32: 11)" does not. Same benign
     class as Genesis = "1 Мойсея". Not a defect.
ch23 SCRIPTURE APOSTROPHE: Kulish uses U+02BC (303 verses, never U+2019), e.g.
     "безʼутомний" in ISA 40:28. Prose uses U+2019. The tokens carry U+02BC
     through untouched, which is what the shipped uk book already does.
ch24 ISA 49:23 / ISA 30:18 mined (both epigraphs, re-quoted through the
     chapter; the three italic spans sit on the same words as the English).
     PSA 33:20, 2CO 4:6 mined. PSA 25:3 is the ch08 SELF petition, reused
     word for word so the two chapters agree.
ch25 ISA 64:4 mined (epigraph) ; ISA 63:15,17, ISA 64:1,2,3, 1CO 2:10,11,
     ISA 30:18 mined. Murray's own ellipsis between ISA 64:1 and 64:2 is kept.
ch25 NOTE FOR THE REVIEWER — this chapter compares two ENGLISH versions (A.V.
     vs R.V.) of ISA 64:4. Kulish happens to read like the R.V. ("нїяке око не
     видало иншого Бога крім тебе"), so the epigraph and Murray's quoted R.V.
     line come out the same words. That repetition is real, not an error: a
     version-comparison passage cannot be reproduced in a language with one
     version. The two versions are named in Ukrainian (Переглянутий /
     Уповноважений переклад) rather than as Latin "R.V." / "A.V.", which the
     mixed-script scan would flag.

## Tooling defect found and fixed at ch25
The doubled-punctuation guard ran AFTER nodes.write() had already dumped the
draft, so a rejected chapter still landed on disk and put_uk.py gated it
happily. The guard now runs BEFORE the write. Its ellipsis exemption was also
wrong twice over: it first passed anything made of dots and spaces (which would
have let "на Господа.." through), then rejected Murray's own ", . . ." Now the
scan collapses real ellipses to a single character first, so "…" is invisible
to it while ".." and ".!" are still caught. All 24 chapters gated before the
fix were re-checked against the corrected guard: 0 hits.
ch26 LAM 3:25 mined (epigraph + four re-quotes) ; LAM 3:26, MRK 10:18,
     PSA 36:5, PSA 31:19, PSA 34:8 mined.
ch26 LAM 3:25 REORDERED once: the English italicises the predicate ("The Lord
     /is good/ to them that wait"), and in Ukrainian the predicate adjective
     "благий" opens Kulish's clause, so the uk puts "Господь" first and the
     italic falls on "благий" — same word emphasised, natural word order.
