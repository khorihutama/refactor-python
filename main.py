import argparse
import datetime
import logging
from collections.abc import Sequence
from pathlib import Path
from typing import Final

from scheduler.config import load_config
from scheduler.executor import TaskExecutor, default_actions
from scheduler.scheduler import Scheduler

DEFAULT_CONFIG: Final = Path("tasks.json")
LOG_FORMAT: Final = "%(asctime)s %(levelname)s %(name)s: %(message)s"

logger = logging.getLogger(__name__)


def build_scheduler(config_path: Path) -> Scheduler:
    users, tasks = load_config(config_path)
    executor = TaskExecutor(default_actions())
    return Scheduler(tasks, users, executor, clock=datetime.datetime.now)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the tasks due now.")
    parser.add_argument("config", nargs="?", type=Path, default=DEFAULT_CONFIG)
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)
    try:
        scheduler = build_scheduler(args.config)
    except (OSError, ValueError) as error:
        logger.error("Cannot load config %s: %s", args.config, error)
        return 1
    scheduler.run_due()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
