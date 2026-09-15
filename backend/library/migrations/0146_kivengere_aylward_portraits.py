"""Portraits for Festo Kivengere and Gladys Aylward.

Both were **intentionally left blank in 0129** under the older PD-only rule
(Kivengere as a "dubious own-work" East African Revival figure; Aylward as
"PD-China only, no US clearance"). The founder's 2026-09-15 steer relaxes that:
a freely-offered, low-risk image is fine to use — Creative Commons with the
credit shown, or a Commons-PD photo. So both now ship a face. See the
`sourcing-not-strictly-pd` note and CLAUDE.md's "Sourcing" section.

Same mechanism as 0129: ``author_sync`` fill-syncs ``photo_url`` on every deploy
but NOT the credit fields, so a CC portrait's ``photo_attribution`` /
``photo_source_url`` have to be set here to reach the already-seeded prod DB (a
fresh DB gets them from ``authors.json``). Each image was found on Wikimedia
Commons, its licence read on the File: page, downloaded, converted to
black-and-white and scaled to <=600px tall, self-hosted under
``frontend/static/portraits/<slug>.jpg``.

  festo-kivengere  File:Bishop Festo Kivengere.jpg   CC BY-SA 4.0 (Korirk01) — credit shown
  gladys-aylward   File:Gladys Aylward.jpg           Public domain (from zh.wikipedia) — no credit due,
                                                     bust-cropped from a full-length courtyard photo

(Janani Luwum was also asked for, but Commons has only his burial site and a
group martyr-statue; his one portrait file is en-wiki fair-use, non-free — so he
keeps the initials avatar.)

Idempotent. RunPython only — 0129 already added the two credit columns.
"""

from django.db import migrations

# slug -> (attribution, source_url). "" attribution == public domain, no credit due.
PORTRAITS = {
    "festo-kivengere": (
        "Korirk01, CC BY-SA 4.0, via Wikimedia Commons — adapted (black-and-white)",
        "https://commons.wikimedia.org/wiki/File:Bishop_Festo_Kivengere.jpg",
    ),
    "gladys-aylward": ("", ""),
}


def apply(apps, schema_editor):
    Author = apps.get_model("library", "Author")
    for slug, (attribution, source_url) in PORTRAITS.items():
        Author.objects.filter(slug=slug).update(
            photo_url=f"/portraits/{slug}.jpg",
            photo_attribution=attribution,
            photo_source_url=source_url,
        )


def unapply(apps, schema_editor):
    Author = apps.get_model("library", "Author")
    Author.objects.filter(slug__in=PORTRAITS).update(
        photo_url="", photo_attribution="", photo_source_url=""
    )


class Migration(migrations.Migration):
    dependencies = [
        ("library", "0145_topic_qa"),
    ]

    operations = [
        migrations.RunPython(apply, unapply),
    ]
