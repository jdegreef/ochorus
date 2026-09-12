"""Generate answered study questions for a sermon (off-server, like translation).

The reader shows these under "Questions for reflection" and the sermon page emits
FAQPage JSON-LD from them (see ``frontend/.../sermons/[slug]/+page.svelte``). Runs
locally — needs ANTHROPIC_API_KEY / an ``ant auth`` profile — and the result is
plain-text ``{question, answer}`` pairs shipped in the sermon's fixture, exactly
like ``summary``: prod holds no model credentials, so nothing is generated on a
deploy.

The one rule the prompt exists to enforce: ground every question and answer
STRICTLY in the sermon's own words. These are public-domain texts hosted on many
sites; the value of ours is unique, faithful study aids, not invented ones — and
an invented answer is worse than none. The pure ``parse_questions`` /
``clean_questions`` helpers are split out from the API call so they can be tested
without spending a token.
"""

from __future__ import annotations

import json
import re

from .text import html_to_text
from .translation import MODEL

#: Default number of questions per sermon. A row of reflection prompts, not an
#: index — four answered questions is enough to orient a reader and thin enough
#: to stay reviewable.
QUESTION_COUNT = 4

#: Plain-text length caps. A question is a line; an answer is 1-3 sentences. The
#: caps are guardrails against a runaway generation, not targets.
MAX_QUESTION = 200
MAX_ANSWER = 600

SYSTEM_PROMPT = (
    "You write concise study questions for a Christian sermon, for readers and "
    "small groups.\n"
    "Absolute rule: ground every question AND answer strictly in the sermon's own "
    "content. Never introduce a claim, doctrine, application, illustration, or fact "
    "the sermon does not itself make. If the sermon does not support four good "
    "questions, write fewer — never pad.\n"
    "Questions must be the kind a person actually searches for or brings to a study "
    "— \"What does this sermon say about X?\", \"Why does the preacher argue Y?\", "
    "\"How does the sermon apply Z?\" — not vague prompts like \"What can we learn?\".\n"
    "Answers are 1-3 sentences of plain prose drawn from the sermon.\n"
    "Return ONLY a JSON array of objects with keys \"question\" and \"answer\". No "
    "markdown, no HTML, no commentary before or after."
)


def _user_prompt(title: str, scripture_ref: str, body_text: str, count: int) -> str:
    ref = f" (text: {scripture_ref})" if scripture_ref else ""
    return (
        f"Sermon: {title}{ref}\n\n"
        f"Write up to {count} answered study questions grounded strictly in the "
        f"sermon below. Return a JSON array of {{\"question\", \"answer\"}} objects.\n\n"
        f"--- SERMON ---\n{body_text}"
    )


# A leading ```json fence, or a bare ``` fence, that a model sometimes wraps JSON
# in despite being told not to.
_FENCE = re.compile(r"^\s*```(?:json)?\s*|\s*```\s*$", re.IGNORECASE)


def parse_questions(raw: str) -> list[dict]:
    """The model's text -> a list of ``{question, answer}`` dicts.

    Tolerant of a ```json fence and of leading/trailing prose around the array
    (some efforts add a sentence despite the instruction): the array is located
    by its outermost brackets. Raises ``ValueError`` if no JSON array is found or
    it isn't a list — a caller turns that into a skip, never a silent empty write.
    """
    text = _FENCE.sub("", raw.strip())
    start, end = text.find("["), text.rfind("]")
    if start == -1 or end == -1 or end < start:
        raise ValueError("no JSON array in model output")
    data = json.loads(text[start : end + 1])
    if not isinstance(data, list):
        raise ValueError("model output was not a JSON array")
    return data


def clean_questions(items: list[dict], *, count: int = QUESTION_COUNT) -> list[dict]:
    """Validate, plain-text-ify and cap the parsed items.

    Every value is forced to plain text (``html_to_text`` strips any stray tag or
    entity — the field is rendered as escaped text, but a model that emits ``<b>``
    should not leave it in the data either) and length-capped. An item missing
    either half, or empty after cleaning, is dropped rather than shipped blank.
    Returns at most ``count`` items, in the model's order.
    """
    out: list[dict] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        qv, av = item.get("question"), item.get("answer")
        # Only real strings — a model that emits {"question": null} must not become
        # the literal text "None" (str(None) is truthy and would slip past the
        # gate below), which is exactly the invented content the prompt forbids.
        if not isinstance(qv, str) or not isinstance(av, str):
            continue
        q = html_to_text(qv).strip()[:MAX_QUESTION]
        a = html_to_text(av).strip()[:MAX_ANSWER]
        if q and a:
            out.append({"question": q, "answer": a})
    return out[:count]


def generate_questions(
    client,
    *,
    title: str,
    scripture_ref: str,
    body_text: str,
    effort: str = "high",
    count: int = QUESTION_COUNT,
):
    """Generate cleaned study questions for one sermon. Returns ``(items, usage)``.

    ``items`` is the ``clean_questions`` result (possibly fewer than ``count``,
    or empty if the model produced nothing usable — the caller decides what to do
    with an empty result). Mirrors the ``translation`` module's call shape: the
    house content model, adaptive thinking, effort-controlled.
    """
    response = client.messages.create(
        model=MODEL,
        # Room for adaptive thinking AND the JSON output: at high effort thinking
        # draws from this budget, and a 2000 ceiling truncated the array (a paid
        # call that then parses to nothing). Output itself is small (~4×(200+600)
        # chars); the headroom is for the reasoning.
        max_tokens=8000,
        thinking={"type": "adaptive"},
        output_config={"effort": effort},
        system=SYSTEM_PROMPT,
        messages=[
            {"role": "user", "content": _user_prompt(title, scripture_ref, body_text, count)}
        ],
    )
    text = "".join(b.text for b in response.content if b.type == "text")
    items = clean_questions(parse_questions(text), count=count)
    return items, response.usage
