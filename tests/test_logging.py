"""Logging configuration regression tests."""

import logging

from src.configs.logs import LOGGING_CONFIG


def test_uvicorn_logs_use_the_timestamped_console_formatter() -> None:
    """Ensure server startup and access records contain date and time."""
    for logger_name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        assert "console" in LOGGING_CONFIG["loggers"][logger_name]["handlers"]

    formatter_config = LOGGING_CONFIG["formatters"]["default"]
    formatter = logging.Formatter(
        formatter_config["format"], datefmt=formatter_config["datefmt"]
    )
    output = formatter.format(
        logging.LogRecord(
            "uvicorn.error",
            logging.INFO,
            __file__,
            1,
            "Waiting for application startup.",
            (),
            None,
        )
    )

    assert output.startswith("[")
    assert "] [INFO] uvicorn.error: Waiting for application startup." in output
