"""Source parser registry.

``--source`` selects a parser by name; ``manual`` is the default (plain markdown,
filename as id). ``keep`` (Google Keep) is reserved for a later stage and currently
reuses the manual/plain parser.
"""

from __future__ import annotations

from volundr.sources.base import Source
from volundr.sources.capacities import CapacitiesSource
from volundr.sources.notion import ManualSource, NotionSource

# maps source names to its parser class
_REGISTRY: dict[str, Source] = {
    "notion": NotionSource(),
    "capacities": CapacitiesSource(),
    "manual": ManualSource(),
    "keep": ManualSource(),  # placeholder until a dedicated Keep parser exists
}

SOURCE_NAMES = tuple(_REGISTRY)


def get_source(name: str) -> Source:
    try:
        return _REGISTRY[name]
    except KeyError:
        raise ValueError(
            f"Unknown source {name!r}. Choose one of: {', '.join(SOURCE_NAMES)}."
        ) from None
