"""
DB log facade: respects DUCK_DB_VERBOSE for production-safe output.

- verbose 0: no output
- verbose 1: info, warn, error
- verbose 2: + debug, full detail
"""
from __future__ import annotations

import logging
from typing import Any

from _db.config import duck_db_verbose

_logger = logging.getLogger("qbrain._db")


def db_log(level: str, msg: str, **kwargs: Any) -> None:
    """
    Log DB message when DUCK_DB_VERBOSE allows.
    level: info, warn, error, debug
    """
    verbose = duck_db_verbose()
    if verbose == 0:
        return
    if level == "debug" and verbose < 2:
        return

    extra = " " + " ".join(f"{k}={v}" for k, v in kwargs.items()) if kwargs else ""
    full_msg = f"{msg}{extra}"

    if level == "info":
        _logger.info(full_msg)
    elif level == "warn":
        _logger.warning(full_msg)
    elif level == "error":
        _logger.error(full_msg)
    elif level == "debug":
        _logger.debug(full_msg)


def duck_print_result(op: str, **kwargs: Any) -> None:
    """Thin wrapper for table_handling compatibility; logs when verbose."""
    db_log("debug", f"[duck] {op}", **kwargs)
