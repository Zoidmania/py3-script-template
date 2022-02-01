import logging
from rich.console import Console
from rich.logging import RichHandler
from rich.theme import Theme

logging_theme = Theme({
    "logging.level.debug": "bright_magenta",
    "logging.level.info": "bright_green",
    "logging.level.warning": "bright_yellow",
    "logging.level.error": "bright_red",
    "logging.level.critical": "white on red",
})

handler = RichHandler(markup=True, rich_tracebacks=True, console=Console(theme=logging_theme))

logging.basicConfig(level="NOTSET", format="%(message)s", datefmt="[%X]", handlers=[handler,])
logger = logging.getLogger("rich")
logger.info("Hello, World!")
logger.warning("Something's funky!")
logger.debug("foo bar baz")
logger.error("[bold red blink]Server is shutting down![/]", extra={"markup": True})
logger.critical("Yowza!")
