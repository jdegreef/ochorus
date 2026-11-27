"""Recording that a scheduled job ran — see :class:`library.models.JobHeartbeat`.

Use :func:`beat` around the work::

    with beat("send_lifecycle_emails"):
        call_command("send_lifecycle_emails")

It stamps the start, then the finish and the outcome, and re-raises whatever
the job raised: a heartbeat records a failure, it never swallows one. A failure
to WRITE the heartbeat (a missing table on the first deploy, a dropped
connection) is logged and ignored — the job matters more than its record.
"""

from __future__ import annotations

import logging
from contextlib import contextmanager

from django.db.models import F
from django.utils import timezone

logger = logging.getLogger(__name__)


def _write(name: str, **fields) -> None:
    from .models import JobHeartbeat

    try:
        updated = JobHeartbeat.objects.filter(name=name).update(**fields)
        if not updated:
            JobHeartbeat.objects.create(
                name=name, **{k: v for k, v in fields.items() if k != "runs"}
            )
    except Exception:  # noqa: BLE001 — see module docstring
        logger.exception("could not record heartbeat for %s", name)


@contextmanager
def beat(name: str):
    """Record one run of the job ``name`` around the ``with`` block."""
    _write(name, last_started_at=timezone.now())
    try:
        yield
    except BaseException as exc:
        _write(
            name,
            last_finished_at=timezone.now(),
            last_error=f"{type(exc).__name__}: {exc}"[:2000],
            runs=F("runs") + 1,
        )
        raise
    now = timezone.now()
    _write(
        name, last_finished_at=now, last_ok_at=now, last_error="", runs=F("runs") + 1
    )
