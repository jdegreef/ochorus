# Scratch — NOT part of the library

Working set for an in-flight translation (job #790, `waiting-on-god` -> uk).
Committed only so a lost container cannot lose the finished chapters; the whole
directory is deleted in the commit that adds the real fixture, before the PR
leaves draft. Nothing here is read by the app, the seeds, or the tests.

* `out/chNN.json`   chapters that have passed put_uk.py (title + body_html)
* `srcNN.json`      their inputs — prose plus {{BOOK C:V}} scripture tokens
* `nodes.py`        expands the tokens from the Kulish text; refuses an
                    incomplete chapter and rejects doubled punctuation
* `put_uk.py`       the gate: tag sequence, digits, script mixing, ratio
