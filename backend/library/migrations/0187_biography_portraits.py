"""Portraits for 21 biography authors who were still wearing initials.

Same mechanism as 0129 / 0146: ``author_sync`` fill-syncs ``photo_url`` on every
deploy but NOT the credit fields, so a credited portrait's ``photo_attribution``
/ ``photo_source_url`` must be set here to reach the already-seeded prod DB (a
fresh DB gets them from ``authors.json``).

Sourcing follows the founder's 2026-10-05 steer: the photos need not be public
domain. Eight are public-domain paintings, engravings or old photographs from
Wikimedia Commons (blank credit). The rest are 20th-century photographs with no
free copy anywhere; each is the best available image from a ministry, church,
archive, publisher or news outlet, credited to that source with a link to the
page it came from. Every file was converted to black-and-white and scaled to
<=600px under ``frontend/static/portraits/<slug>.jpg``.

Only rows whose ``photo_url`` is still blank are touched, so a portrait set in
the admin since is left alone. Idempotent.
"""

from django.db import migrations

# slug -> (attribution, source_url). "" attribution == public domain, no credit due.
PORTRAITS = {
    "arthur-t-pierson": ("", ""),
    "c-s-lewis": ("", ""),
    "charles-s-price": (
        "Flower Pentecostal Heritage Center, via AG News",
        "https://news.ag.org/Features/This-Week-in-AG-History-Oct-24-1931",
    ),
    "derek-prince": (
        "Derek Prince Ministries",
        "https://www.derekprince.com/en-gb/about/derek-prince",
    ),
    "erica-sabiti": (
        "Courtesy of the Church of Uganda, via Daily Monitor",
        "https://www.monitor.co.ug/uganda/news/national/namirembe-question-troubles-anglican-church-4401686",
    ),
    "evelyn-christenson": (
        "Revive Our Hearts",
        "https://www.reviveourhearts.com/contributors/evelyn-christenson/",
    ),
    "g-k-chesterton": ("", ""),
    "george-macdonald": ("", ""),
    "isaac-watts": ("", ""),
    "janani-luwum": (
        "Anglican Focus",
        "https://anglicanfocus.org.au/2020/05/29/ugandan-anglican-martyr-archbishop-janani-luwum/",
    ),
    "jesse-lyman-hurlbut": ("", ""),
    "joe-church": (
        "From H. H. Osborn, Pioneers in the East African Revival, via Beautiful Feet",
        "https://romans1015.com/east-africa/",
    ),
    "john-foxe": ("", ""),
    "john-hyde": (
        "Photograph c. 1900s, via Život víry",
        "https://zivotviry.cz/clanek/john-nelson-hyde-muz-ktery-nikdy-nespal-101307",
    ),
    "john-milton": ("", ""),
    "lawrence-barham": (
        "Dictionary of African Christian Biography (photo from H. H. Osborn)",
        "https://dacb.org/stories/rwanda/barham-lawrence/",
    ),
    "martyn-lloyd-jones": (
        "Ligonier Ministries",
        "https://learn.ligonier.org/teachers/d-martyn-lloyd-jones",
    ),
    "rees-howells": (
        "Bible College of Wales archive, via Great Life Publishing",
        "https://greatlifepublishing.nl/portfolio/rees-howells/",
    ),
    "simeon-nsibambi": (
        "From H. H. Osborn, Pioneers in the East African Revival, via Beautiful Feet",
        "https://romans1015.com/east-africa/",
    ),
    "william-nagenda": (
        "From H. H. Osborn, Pioneers in the East African Revival, via Beautiful Feet",
        "https://romans1015.com/east-africa/",
    ),
    "yosiya-kinuka": (
        "Boston University Center for Global Christianity & Mission",
        "https://www.bu.edu/cgcm/2017/06/12/the-beginning-of-the-east-africa-revival/",
    ),
}


def apply(apps, schema_editor):
    Author = apps.get_model("library", "Author")
    for slug, (attribution, source_url) in PORTRAITS.items():
        Author.objects.filter(slug=slug, photo_url="").update(
            photo_url=f"/portraits/{slug}.jpg",
            photo_attribution=attribution,
            photo_source_url=source_url,
        )


def unapply(apps, schema_editor):
    Author = apps.get_model("library", "Author")
    for slug in PORTRAITS:
        Author.objects.filter(slug=slug, photo_url=f"/portraits/{slug}.jpg").update(
            photo_url="", photo_attribution="", photo_source_url=""
        )


class Migration(migrations.Migration):
    dependencies = [
        ("library", "0186_hi_articles_ai_unreviewed"),
    ]

    operations = [
        migrations.RunPython(apply, unapply),
    ]
