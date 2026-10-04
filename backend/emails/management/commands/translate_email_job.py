"""Check a worker's email translation and print the comment to post.

    manage.py translate_email_job issue.md --answer answer.json

``issue.md`` is the body of a ``[translation] email:broadcast-<id> -> <lang>``
job filed from the admin email designer (or just its JSON block). The worker
translates the job's ``subject``, ``preheader`` and ``texts`` in-session, writes
``{"subject", "preheader", "texts": [...]}`` to a file and passes it as
``--answer``; the command checks it against the job and prints the reply. Post
it as a comment on the issue exactly as printed, then close the issue; the
admin pulls the draft in and approves it. See emails/translation_jobs.py.
"""

from __future__ import annotations

import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from emails.translation_jobs import (
    JSON_BLOCK,
    TranslationJobError,
    check_answer,
    reply_comment,
)


def _read_json(path: str) -> dict:
    text = Path(path).read_text(encoding="utf-8")
    match = JSON_BLOCK.search(text)
    try:
        return json.loads(match.group(1) if match else text)
    except json.JSONDecodeError as exc:
        raise CommandError(f"no JSON in {path}: {exc}") from exc


class Command(BaseCommand):
    help = "Check an email translation job's answer; print the reply comment."

    def add_arguments(self, parser):
        parser.add_argument("job", help="The issue body, or the job's JSON, in a file")
        parser.add_argument(
            "--answer",
            required=True,
            help='A file with your translation: {"subject", "preheader", "texts": [...]}',
        )

    def handle(self, *args, **opts):
        payload = _read_json(opts["job"])
        if payload.get("type") != "email":
            raise CommandError("this is not an email translation job")
        try:
            reply = check_answer(payload, _read_json(opts["answer"]))
        except TranslationJobError as exc:
            raise CommandError(str(exc)) from exc
        self.stdout.write(reply_comment(reply))
