# TheAssassin/pyuploadtool

import logging
import os

import coloredlogs


def setup_logging():
    loglevel = logging.INFO
    force_colors = False

    if "DEBUG" in os.environ:
        loglevel = logging.DEBUG

    if "FORCE_COLORS" in os.environ:
        force_colors = True

    fmt = "%(asctime)s,%(msecs)03d %(name)s [%(levelname)s] %(message)s"

    # basic logging setup
    styles = coloredlogs.DEFAULT_FIELD_STYLES
    styles["pathname"] = {
        "color": "magenta",
    }
    styles["levelname"] = {
        "color": "cyan",
    }

    # configure our own loggers only
    base_logger = make_logger()
    base_logger.setLevel(loglevel)

    kwargs = dict(fmt=fmt, styles=styles, logger=base_logger)

    if force_colors:
        kwargs["isatty"] = True

    coloredlogs.install(loglevel, **kwargs)

    # hide all other loggers by default
    logging.getLogger().setLevel(logging.DEBUG)
    base_logger.setLevel(loglevel)

    # allow user to re-enable some loggers for debugging
    if "DEBUG_TELEGRAM" in os.environ:
        logging.getLogger("telegram").setLevel(logging.INFO)
        logging.getLogger("apscheduler").setLevel(logging.INFO)


def make_logger(name: str = None) -> logging.Logger:
    base_logger = logging.getLogger("lyrix")

    if name is None:
        return base_logger

    return base_logger.getChild(name)
