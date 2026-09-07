"""Portraits for thirteen more biography-page authors, plus the fields that let
a Creative Commons portrait carry its credit.

Same convention as 0015 / 0027 / 0036: each image was found on Wikimedia
Commons, its licence VERIFIED by loading the File: page, then downloaded,
converted to black-and-white and scaled to 600px tall (width follows the
source), self-hosted under frontend/static/portraits/<slug>.jpg.

Public domain — no attribution due (recorded here for provenance only):
  gregory-the-great   File:Francisco de Goya - Saint Gregory the Great, Pope ...  (PD-Art, Goya d.1828)
  monica-of-hippo     File:Monica of Hippo by Gozzoli.jpg                        (PD-Art, Gozzoli d.1497)
  martin-luther       File:Portrait of Martin Luther ... Lucas Cranach ...jpg    (PD-Art, Cranach 1517)
  john-calvin         File:Portrait of John Calvin ... Museum Catharijneconvent  (PD-Art, anon c.1550)
  teresa-of-avila     File:Santa Teresa de Ávila. (Museo del Prado).jpg          (PD-Art, after Ribera)
  billy-graham        File:Billy Graham bw photo, April 11, 1966 (cropped).jpg   (PD, US News/LoC, Leffler)
  corrie-ten-boom     File:CorrieTenBoom.jpg                                      (PD, anonymous, 1921)

Creative Commons — attribution shipped in photo_attribution and shown on the
author page (photo_source_url links the File: page):
  william-law         File:William Law.jpg                                       (CC BY 4.0)
  alexander-maclaren  File:Alexander Maclaren (01).jpg                           (CC BY-SA 4.0)
  dietrich-bonhoeffer File:Bundesarchiv Bild 146-1987-074-16 ...jpg              (CC BY-SA 3.0 DE)
  john-stott          File:John stott.jpg                                        (CC BY 3.0)
  timothy-keller      File:Timothy Keller.jpg                                    (CC BY-SA 2.0)
  loren-cunningham    File:Loren Cunningham, Teófilo e Junia Hayashi ...png      (CC BY-SA 4.0, cropped)

Intentionally still blank — Commons has no genuinely free portrait (a dubious
"own work" claim on a photo of a long-dead figure is rejected, as in 0027):
A. W. Tozer (only a CC0 SVG traced from a copyrighted photo), John Hyde, Rees
Howells, Gladys Aylward (PD-China only, no US clearance), Bill Bright & Helen
Roseveare (dubious own-work), Derek Prince, Elisabeth & Jim Elliot, Evelyn
Christenson, Henry Blackaby, Martyn Lloyd-Jones, and the East African Revival
figures (Kigozi, Sabiti, Kivengere, Luwum, Church, Barham, Nsibambi, Nagenda,
Kanamuzeyi, Kinuka, Buyinza). They keep the initials avatar.

Idempotent.
"""

from django.db import migrations, models

# slug -> (attribution, source_url). "" attribution == public domain, no credit due.
PORTRAITS = {
    "gregory-the-great": ("", ""),
    "monica-of-hippo": ("", ""),
    "martin-luther": ("", ""),
    "john-calvin": ("", ""),
    "teresa-of-avila": ("", ""),
    "billy-graham": ("", ""),
    "corrie-ten-boom": ("", ""),
    "william-law": (
        "National Galleries of Scotland (engraving by John Scott, 1827), CC BY 4.0 — adapted (cropped, black-and-white)",
        "https://commons.wikimedia.org/wiki/File:William_Law.jpg",
    ),
    "alexander-maclaren": (
        "Ardfern, CC BY-SA 4.0, via Wikimedia Commons (from Manchester Faces and Places, 1889) — adapted (black-and-white)",
        "https://commons.wikimedia.org/wiki/File:Alexander_Maclaren_(01).jpg",
    ),
    "dietrich-bonhoeffer": (
        "Bundesarchiv, Bild 146-1987-074-16 / unknown / CC BY-SA 3.0 DE — adapted (black-and-white)",
        "https://commons.wikimedia.org/wiki/File:Bundesarchiv_Bild_146-1987-074-16,_Dietrich_Bonhoeffer.jpg",
    ),
    "john-stott": (
        "Langham Partnership International, CC BY 3.0, via Wikimedia Commons — adapted (black-and-white)",
        "https://commons.wikimedia.org/wiki/File:John_stott.jpg",
    ),
    "timothy-keller": (
        "Frank Licorice, CC BY-SA 2.0, via Wikimedia Commons — adapted (black-and-white)",
        "https://commons.wikimedia.org/wiki/File:Timothy_Keller.jpg",
    ),
    "loren-cunningham": (
        "Dunamis Movement, CC BY-SA 4.0, via Wikimedia Commons — adapted (cropped, black-and-white)",
        "https://commons.wikimedia.org/wiki/File:Loren_Cunningham,_Te%C3%B3filo_e_Junia_Hayashi_na_Dunamis_Farm.png",
    ),
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
        ("library", "0128_alter_adminaction_action"),
    ]

    operations = [
        migrations.AddField(
            model_name="author",
            name="photo_attribution",
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name="author",
            name="photo_source_url",
            field=models.URLField(blank=True),
        ),
        migrations.RunPython(apply, unapply),
    ]
