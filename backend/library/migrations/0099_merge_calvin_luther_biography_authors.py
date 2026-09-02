"""Merge the two 0098 biography-author leaves.

0098_john_calvin_biography_author and 0098_martin_luther_biography_author were
filed from parallel branches, each depending on 0097; this unifies them.
"""

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("library", "0098_john_calvin_biography_author"),
        ("library", "0098_martin_luther_biography_author"),
    ]

    operations = []
