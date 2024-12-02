import logging


def configure_logger() -> None:
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(
        logging.Formatter("%(levelname)s: [%(asctime)s] %(module)s | %(message)s")
    )

    logger.addHandler(console_handler)
