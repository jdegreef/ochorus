from django.db import migrations


def paper_to_unset(apps, schema_editor):
    # "paper" was the old model default, and no current client pushes it (the
    # web app's themes are system/light/dark/sepia), so a row still holding it
    # never had a device's prefs saved. Blank it so the next sign-in keeps that
    # device's theme instead of forcing "light" (see UserProfile.theme).
    UserProfile = apps.get_model("accounts", "UserProfile")
    UserProfile.objects.filter(theme="paper").update(theme="")


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0012_userprofile_theme_unset"),
    ]

    operations = [migrations.RunPython(paper_to_unset, migrations.RunPython.noop)]
