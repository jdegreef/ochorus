"""Translate an email translation job's words — the worker side of
``emails/translation_jobs.py``.

Run off-server by a worker session (prod holds no Anthropic credentials), via
``manage.py translate_email_job``. Uses the library's own translation system
prompt — the same theological glossary and register rules as books and sermons
— with the request shaped like ``translate_summary``: a JSON schema for the
answer, so the reply is structured rather than parsed out of prose.
"""

from __future__ import annotations

import json

from library.translation import MODEL, system_prompt

from . import blocks as blocks_mod
from .translation_jobs import MARKER, TranslationJobError, validate_draft


class TranslateError(RuntimeError):
    """The model's answer can't be used as a draft."""


def _slots(blocks: list[dict]) -> list[tuple[int, str]]:
    """``(block index, field)`` for every piece of the admin's own words."""
    return [
        (i, field)
        for i, block in enumerate(blocks)
        for field in blocks_mod.FIELDS[block["type"]]
        if field in blocks_mod.WORD_FIELDS and block.get(field)
    ]


#: How an email is translated — for the model, and printed for a worker session
#: translating in-session, so both follow the same rules.
INSTRUCTIONS = (
    "This is not a chapter: it is a short email from Ochorus to its readers. "
    "Translate its subject line, its inbox preview text and each string in "
    "`texts`, keeping the strings in the same order and the same count. Keep "
    "`{name}` exactly as written (it becomes the reader's first name). Keep each "
    "string about the length of its source; a subject line must stay short. Book "
    "and sermon titles inside the text take their published title in the target "
    "language where one exists. Return JSON with the keys `subject`, `preheader` "
    "and `texts`."
)


def _schema() -> dict:
    return {
        "type": "object",
        "properties": {
            "subject": {"type": "string"},
            "preheader": {"type": "string"},
            "texts": {"type": "array", "items": {"type": "string"}},
        },
        "required": ["subject", "preheader", "texts"],
        "additionalProperties": False,
    }


def source_texts(payload: dict) -> dict:
    """What there is to translate: ``{subject, preheader, texts}``, ``texts`` in
    block order — the shape a translator (the model, or a worker session doing it
    in-session) answers in."""
    blocks = blocks_mod.clean(payload.get("blocks"))
    return {
        "subject": payload.get("subject", ""),
        "preheader": payload.get("preheader", ""),
        "texts": [blocks[i][field] for i, field in _slots(blocks)],
    }


def assemble(payload: dict, answer: dict) -> dict:
    """The reply from a translator's ``{subject, preheader, texts}`` answer:
    the source blocks with only their words replaced, checked like fetch will."""
    blocks = blocks_mod.clean(payload.get("blocks"))
    slots = _slots(blocks)
    texts = answer.get("texts") or []
    if len(texts) != len(slots):
        raise TranslateError(f"expected {len(slots)} translated strings, got {len(texts)}")
    translated = [dict(b) for b in blocks]
    for (i, field), value in zip(slots, texts, strict=True):
        translated[i][field] = str(value).strip()
    reply = {
        "broadcast": payload["broadcast"],
        "target": payload["target"],
        "source_digest": payload.get("source_digest", ""),
        "subject": str(answer.get("subject") or "").strip(),
        "preheader": str(answer.get("preheader") or "").strip(),
        "blocks": translated,
    }
    try:
        validate_draft(blocks, reply)
    except TranslationJobError as exc:
        raise TranslateError(str(exc)) from exc
    return reply


def translate_payload(client, payload: dict) -> dict:
    """The reply for a job payload, translated by the model (where a worker has
    Anthropic credentials; a session can also translate in-session and use
    :func:`assemble` directly)."""
    source = source_texts(payload)
    response = client.messages.create(
        model=MODEL,
        max_tokens=16000,
        thinking={"type": "adaptive"},
        system=system_prompt(payload["target"]),
        messages=[
            {
                "role": "user",
                "content": INSTRUCTIONS + "\n\n" + json.dumps(source, ensure_ascii=False),
            }
        ],
        output_config={"format": {"type": "json_schema", "schema": _schema()}},
    )
    if response.stop_reason != "end_turn":
        raise TranslateError(f"the model stopped early ({response.stop_reason})")
    text = next(b.text for b in response.content if b.type == "text")
    return assemble(payload, json.loads(text))


def reply_comment(reply: dict) -> str:
    """The issue comment a worker posts — what ``translation_jobs.fetch`` reads."""
    return f"{MARKER}\nAI draft for review in the admin.\n\n```json\n{json.dumps(reply, ensure_ascii=False, indent=2)}\n```\n"
