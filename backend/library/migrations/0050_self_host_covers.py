"""Serve every book cover from Ochorus itself.

Two gaps, one cause — cover artwork lived outside the app's control:

1. 28 covers hotlinked ochorus.com's WordPress media (the site we are moving
   away from). Every translated edition reuses the English artwork, so the same
   URLs appear on 28 distinct rows across en/es/sw/lg — hence matching on the
   URL rather than the slug. The files now ship with the frontend
   (frontend/static/covers/), resized to the 600px canvas the generated covers
   already use: 33.9MB of originals became 1.5MB.
2. 18 books rendered as blank cards. Their generated SVGs were committed and are
   serving fine at /covers/<slug>.svg — only Book.cover_url was never set on
   prod, because `generate_covers` writes the file and updates the LOCAL db, and
   that db change was never given a vehicle to production.

Seeds never update an existing book row, so the fixture change alone would only
reach fresh installs; this carries both halves to production. Idempotent: (1)
matches the old external URL, (2) only fills a still-empty cover_url — so a
re-run, or a row already switched, is a no-op. cover_url is deliberately outside
the search-vector derivation (see Book.save), so .update() is correct here.
"""

from django.db import migrations

# ochorus.com WordPress URL -> the copy we now ship.
COVER_MAP = {
    "https://ochorus.com/wp-content/uploads/2025/08/65d59905f191ae452489ab6e_He-holds-my-tomorrows-1.png": "/covers/he-holds-my-tomorrows.jpg",
    "https://ochorus.com/wp-content/uploads/2025/08/6646102f6cbbe1aee0dda4ae_Jesus20Himself20220comp-01-p-500-1.jpg": "/covers/jesus-himself-2.jpg",
    "https://ochorus.com/wp-content/uploads/2025/08/664610306cbbe1aee0dda4f5_Soar20like20the20eagle-p-500-1.png": "/covers/soar-like-the-eagle-3.jpg",
    "https://ochorus.com/wp-content/uploads/2025/08/664610306cbbe1aee0dda52b_Key20in20my20hand-p-500-1.png": "/covers/the-key-in-my-hand.jpg",
    "https://ochorus.com/wp-content/uploads/2025/08/Feating-at-the-table-BC.jpg": "/covers/feasting-at-the-table.jpg",
    "https://ochorus.com/wp-content/uploads/2025/08/Humility.jpg": "/covers/humility-2.jpg",
    "https://ochorus.com/wp-content/uploads/2025/08/Inner-Chamber.jpg": "/covers/the-inner-chamber.jpg",
    "https://ochorus.com/wp-content/uploads/2025/08/Lord-teach-us-to-pray.jpg": "/covers/lord-teach-us-to-pray-2.jpg",
    "https://ochorus.com/wp-content/uploads/2025/08/Masters-Indwelling.jpg": "/covers/the-masters-indwelling.jpg",
    "https://ochorus.com/wp-content/uploads/2025/08/Prayer-the-pulse-of-life-new-design.png": "/covers/prayer-the-pulse-of-life.png",
    "https://ochorus.com/wp-content/uploads/2025/08/Secret-of-guidance.png": "/covers/the-secret-of-guidance.jpg",
    "https://ochorus.com/wp-content/uploads/2025/08/Stepping-Stones.jpg": "/covers/stepping-stones-2.jpg",
    "https://ochorus.com/wp-content/uploads/2025/08/The-Christians-secret-of-a-happy-life.jpg": "/covers/the-christians-secret-of-a-happy-life-4.jpg",
    "https://ochorus.com/wp-content/uploads/2025/09/The-Person-and-Work-of-the-Holy-Spirit-FC.jpg": "/covers/the-person-and-work-of-the-holy-spirit.jpg",
    "https://ochorus.com/wp-content/uploads/2025/12/Artboard-10100.jpg": "/covers/how-to-manage-a-library.jpg",
    "https://ochorus.com/wp-content/uploads/2026/02/big.png": "/covers/baptism-with-the-holy-spirit.png",
    "https://ochorus.com/wp-content/uploads/2026/03/POH-Front.jpg": "/covers/purity-of-heart.jpg",
    "https://ochorus.com/wp-content/uploads/2026/04/GOC-Face-Cover.png": "/covers/the-god-of-all-comfort.jpg",
    "https://ochorus.com/wp-content/uploads/2026/06/Clothed-with-strength-Front-cover-1.png": "/covers/clothed-with-strength-and-dignity.jpg",
    "https://ochorus.com/wp-content/uploads/2026/06/Men-and-women-who-gave-everything-Front-cover-1.png": "/covers/men-and-women-who-gave-everything-2.jpg",
    "https://ochorus.com/wp-content/uploads/2026/06/Men-of-Prayer-Front-cover-1.png": "/covers/men-of-prayer-2.jpg",
    "https://ochorus.com/wp-content/uploads/2026/06/Men-who-Tended-the-Flock-Front-cover.png": "/covers/men-who-tended-the-flock-2.jpg",
    "https://ochorus.com/wp-content/uploads/2026/06/Men-who-moved-Heaven-Front-cover-2.png": "/covers/men-who-moved-heaven.jpg",
    "https://ochorus.com/wp-content/uploads/2026/06/Rise-up-men-of-God-Front.png": "/covers/rise-up-men-of-god-2.jpg",
    "https://ochorus.com/wp-content/uploads/2026/06/Talks-to-the-Farmer-Front.jpg": "/covers/talks-to-the-farmer.jpg",
    "https://ochorus.com/wp-content/uploads/2026/06/The-Unselfishness-of-God-Front.png": "/covers/the-unselfishness-of-god.jpg",
    "https://ochorus.com/wp-content/uploads/2026/06/Women-who-moved-Heaven-Front-cover-1.png": "/covers/women-who-moved-heaven-2.jpg",
    "https://ochorus.com/wp-content/uploads/2026/07/Godliness-front.jpg": "/covers/godliness.jpg",
}

# Books whose generated SVG is already committed and served, but whose
# cover_url never made it to prod.
GENERATED_COVER_SLUGS = [
    "a-call-to-the-unconverted",
    "all-things-for-good",
    "answers-to-prayer",
    "freedom-of-the-will",
    "grace-abounding",
    "life-and-diary-of-david-brainerd",
    "pilgrims-progress",
    "plain-account-christian-perfection",
    "religious-affections",
    "revival-lectures",
    "selected-sermons-whitefield",
    "sermons-on-several-occasions",
    "susanna-wesley-clarke",
    "ten-commandments",
    "the-reformed-pastor",
    "things-as-they-are",
    "union-and-communion",
    "way-into-holiest",
]


def forwards(apps, schema_editor):
    Book = apps.get_model("library", "Book")
    for old, new in COVER_MAP.items():
        Book.objects.filter(cover_url=old).update(cover_url=new)
    for slug in GENERATED_COVER_SLUGS:
        Book.objects.filter(slug=slug, cover_url="").update(
            cover_url=f"/covers/{slug}.svg"
        )


def backwards(apps, schema_editor):
    Book = apps.get_model("library", "Book")
    for old, new in COVER_MAP.items():
        Book.objects.filter(cover_url=new).update(cover_url=old)
    for slug in GENERATED_COVER_SLUGS:
        Book.objects.filter(slug=slug, cover_url=f"/covers/{slug}.svg").update(
            cover_url=""
        )


class Migration(migrations.Migration):
    dependencies = [
        ("library", "0049_backfill_author_short_bios"),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
