from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("library", "0162_sync_stepping_stones_chapters"),
    ]

    operations = [
        migrations.AddField(
            model_name="book",
            name="cover_title",
            field=models.CharField(blank=True, max_length=120),
        ),
    ]
