"""Central logging setup.

One place to configure the stdlib `logging` so every module can just do
`log = logging.getLogger(__name__)` and emit through a consistent format/level.
"""

import logging

# Map the CLI's --log-level choices to stdlib levels.
_LEVELS = {
    "info": logging.INFO,
    "warn": logging.WARNING,
    "error": logging.ERROR,
}


def setup_logging(level: str = "info") -> None:
    """Configure root logging once, at startup, from the CLI log level."""
    logging.basicConfig(
        level=_LEVELS.get(level, logging.INFO),
        format="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S%z",
    )
