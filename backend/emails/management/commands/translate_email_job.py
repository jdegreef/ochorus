"""Translate one email translation job and print the comment to post.

    manage.py translate_email_job job.json --print-texts       # what to translate
    manage.py translate_email_job job.json --answer answer.json  # in-session translation
    manage.py translate_email_job job.json                     # model translation (needs a key)

``job.json`` is the issue's body (or just its JSON block) — a
``[translation] email:broadcast-<id> -> <lang>`` job filed from the admin email
designer. Worker sessions usually translate in-session (no API key): print the
texts, translate them following the printed rules, write ``{"subject", "preheader",
"texts"}`` to a file and pass it as ``--answer``; the command checks it against
the source and prints the reply. Never run on the API server. Post the printed text as a comment on the issue, exactly as printed,
then close the issue; the admin pulls the draft in and approves it.
See emails/translation_jobs.py.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import anthropic
from django.core.management.base import BaseCommand, CommandError

from emails.translate import (
    INSTRUCTIONS,
    TranslateError,
    assemble,
    reply_comment,
    source_texts,
    translate_payload,
)
from library.translation import verify_glossary


class Command(BaseCommand):
    help = "Translate an email translation job's words; print the reply comment."

    def add_arguments(self, parser):
        parser.add_argument("job", help="The issue body, or the job's JSON, in a file")
        parser.add_argument(
            "--print-texts",
            action="store_true",
            help="Print the rules and the strings to translate, as JSON; translate nothing",
        )
        parser.add_argument(
            "--answer",
            help='A file with your translation: {"subject", "preheader", "texts": [...]}',
        )

    def handle(self, *args, **opts):
        text = Path(opts["job"]).read_text(encoding="utf-8")
        match = re.search(r"```json\s*(\{.*?\})\s*```", text, re.S)
        try:
            payload = json.loads(match.group(1) if match else text)
        except json.JSONDecodeError as exc:
            raise CommandError(f"no job JSON in {opts['job']}: {exc}") from exc
        if payload.get("type") != "email":
            raise CommandError("this is not an email translation job")
        if opts["print_texts"]:
            self.stdout.write(INSTRUCTIONS + "\n\n")
            self.stdout.write(json.dumps(source_texts(payload), ensure_ascii=False, indent=2))
            return
        try:
            if opts["answer"]:
                answer = json.loads(Path(opts["answer"]).read_text(encoding="utf-8"))
                reply = assemble(payload, answer)
            else:
                verify_glossary(payload["target"])  # before any paid model work
                reply = translate_payload(anthropic.Anthropic(), payload)
        except (ValueError, TranslateError) as exc:
            raise CommandError(str(exc)) from exc
        self.stdout.write(reply_comment(reply))
