"""Log the requests that grow this process's memory, so we can see what pushes
the 512 MB Starter instance over its limit.

Render restarted ochorus-api twice during the 2026-11-19 web build (the build
crawls every public page against the live API), and every web deploy from
2026-11-16 to 11-19 failed on the gap. One line per heavy request names the
endpoint to slim, instead of guessing:

    [memory] +34 MB → 412 MB  GET /api/library/books/?language=en  (1.8s)

Reads /proc/self/status (Linux, as on Render); a no-op elsewhere. The cost is
one small file read per request.
"""

from __future__ import annotations

import logging
import time
from pathlib import Path

logger = logging.getLogger("ochorus.memory")

#: Log a request whose resident memory grew by at least this many MB.
GROWTH_MB = 20
#: ...or that finished with the process above this many MB, whatever it grew by.
HIGH_WATER_MB = 400

_STATUS = Path("/proc/self/status")


def rss_mb() -> int | None:
    """This process's resident memory in MB, or None off Linux."""
    try:
        for line in _STATUS.read_text().splitlines():
            if line.startswith("VmRSS:"):
                return int(line.split()[1]) // 1024
    except OSError:
        return None
    return None


class MemoryLogMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        self.enabled = rss_mb() is not None

    def __call__(self, request):
        if not self.enabled:
            return self.get_response(request)
        before = rss_mb() or 0
        started = time.monotonic()
        response = self.get_response(request)
        after = rss_mb() or 0
        grew = after - before
        if grew >= GROWTH_MB or after >= HIGH_WATER_MB:
            # The four worker threads share one process, so a delta can include
            # a concurrent request's growth; repeated lines for one URL are the
            # signal, a single one is a hint.
            logger.warning(
                "[memory] %+d MB → %d MB  %s %s  (%.1fs)",
                grew,
                after,
                request.method,
                request.get_full_path(),
                time.monotonic() - started,
            )
        return response
