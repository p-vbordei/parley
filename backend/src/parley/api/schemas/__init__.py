"""Shared schema types.

`IsoDatetime` forces response bodies to serialize datetimes with Python's
`.isoformat()` output (e.g. `2026-04-24T12:00:00.000000+00:00`) instead
of Pydantic's default RFC 3339 Z-suffix form. This matches the bytes the
backend signs over, so a client can reconstruct canonical bytes from a
response and re-verify the stored signature — SPEC §10.1's
"tampering at rest is detectable" guarantee.
"""

from datetime import datetime
from typing import Annotated

from pydantic import PlainSerializer

IsoDatetime = Annotated[
    datetime,
    PlainSerializer(lambda dt: dt.isoformat(), return_type=str, when_used="json"),
]
