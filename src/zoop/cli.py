import argparse
from pathlib import Path

import msgspec

from zoop.config import Config, ConfigError


def load_config(path: Path) -> Config:
    try:
        return msgspec.toml.decode(path.read_bytes(), type=Config)
    except FileNotFoundError as e:
        raise ConfigError(f"config file not found: {path}") from e
    except msgspec.ValidationError as e:
        raise ConfigError(f"invalid config {path}: {e}") from e
    except msgspec.DecodeError as e:
        raise ConfigError(f"malformed TOML in {path}: {e}")


def parse_args():
    p = argparse.ArgumentParser(
        prog="zoop",
        description="lightweight data ingestion gateway",
    )

    sub = p.add_subparsers(dest="command", required=True)

    run = sub.add_parser("run", help="run the ingest gateway")
    run.add_argument(
        "--config",
        type=Path,
        default=Path("/etc/zoop/zoop.toml"),
        help="path to the config file"
    )
    run.add_argument(
        "--log-level",
        default="info",
        choices=("info", "warn", "error"),
        help="log level"
    )
    run.add_argument(
         "--check",
         action="store_true",
         help="validate config + specs and exit"
    )
    run.add_argument(
        "--plugin",
        action="append",
        default=[],
        metavar="MODULE|FILE",
        help="import an extra bridge plugin (dotted module or .py path); repeatable"
    )

    chk = sub.add_parser("check", help="validate config + specs, then exit")
    chk.add_argument(
        "--config",
        type=Path,
        default=Path("/etc/zoop/zoop.toml")
    )
    chk.add_argument(
        "--plugin",
        action="append",
        default=[],
        metavar="MODULE|FILE",
        help="import an extra bridge plugin (dotted module or .py path); repeatable"
    )

    return p.parse_args()
