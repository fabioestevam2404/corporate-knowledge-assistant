from cka.observability.logging import configure_logging, get_logger


def test_get_logger_returns_usable_bound_logger() -> None:
    configure_logging("INFO")

    logger = get_logger("test")
    logger.info("test_event", key="value")
