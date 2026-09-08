# Widen Favorite.kind to cover topics, articles and individual quotes
# (in addition to authors, books, plans and sermons). Choices-only change:
# no column alteration, so this is a state-only AlterField.
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('reading', '0019_bookmark_rls'),
    ]

    operations = [
        migrations.AlterField(
            model_name='favorite',
            name='kind',
            field=models.CharField(
                choices=[
                    ('author', 'Author'),
                    ('book', 'Book'),
                    ('plan', 'Plan'),
                    ('sermon', 'Sermon'),
                    ('topic', 'Topic'),
                    ('article', 'Article'),
                    ('quote', 'Quote'),
                ],
                max_length=10,
            ),
        ),
    ]
