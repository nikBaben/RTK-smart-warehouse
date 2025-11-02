import logging
from app.scheduler.config import load_config
from app.scheduler.runner import loop, run_once

logging.basicConfig(level=logging.INFO, format="[%(asctime)s] [%(levelname)s] %(message)s")


def main():
    cfg = load_config()
    if cfg.run_once:
        run_once(cfg)
    else:
        loop(cfg)


if __name__ == "__main__":
    main()
