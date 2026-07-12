"""Set public-domain portraits for the biography-page authors that had none.

Same convention as 0015: Wikimedia Commons images individually verified as public
domain, downloaded, converted to black-and-white, fit to 361x600, and self-hosted
under frontend/static/portraits/<slug>.jpg. Sources / licenses:

  amanda-berry-smith     File:Amanda Berry Smith by T. B. Latchmore.jpg  (CC0 / PD)
  george-muller          File:George Muller portrait.jpg                 (PD-US, pre-1931)
  hudson-taylor          File:HudsonTaylorin1893.jpg                     (PD-US, 1893)
  richard-allen          File:Rev. Richard Allen.png                     (PD-US, 1891)
  samuel-ajayi-crowther  File:Bishop Samuel Ajayi Crowther.png           (PD-US, 1888)

Festo Kivengere (d.1988) and Simeon Nsibambi (d.1978) are intentionally left
blank: no genuinely free-licensed portrait exists (the one Kivengere image on
Commons carries a dubious "own work" claim; Nsibambi has none). They keep the
initials avatar in the UI, per the convention for authors with no PD portrait.
Idempotent.
"""

from django.db import migrations

PORTRAITS = [
    "amanda-berry-smith",
    "george-muller",
    "hudson-taylor",
    "richard-allen",
    "samuel-ajayi-crowther",
]


def apply(apps, schema_editor):
    Author = apps.get_model("library", "Author")
    for slug in PORTRAITS:
        Author.objects.filter(slug=slug).update(photo_url=f"/portraits/{slug}.jpg")


def unapply(apps, schema_editor):
    Author = apps.get_model("library", "Author")
    Author.objects.filter(slug__in=PORTRAITS).update(photo_url="")


class Migration(migrations.Migration):
    dependencies = [
        ("library", "0026_add_biography_authors"),
    ]

    operations = [
        migrations.RunPython(apply, unapply),
    ]
