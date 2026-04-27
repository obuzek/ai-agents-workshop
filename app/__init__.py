import logging
import sys

from uvicorn.logging import DefaultFormatter


def _detect_server_name() -> str:
    """Derive a friendly server name from CLI args."""
    for arg in sys.argv[1:]:
        if ":" in arg and "." in arg.split(":")[0]:
            # uvicorn lab4.agent.api:app → lab4-agent
            module = arg.split(":")[0]
            parts = module.split(".")
            if parts[0] == "app":
                return "ehr-api"
            return f"{parts[0]}-agent"
    if any("streamlit" in a for a in sys.argv[:1]):
        return "ui"
    return "server"


_SERVER_NAME = _detect_server_name()


class _ServerNameFilter(logging.Filter):
    """Replace unhelpful uvicorn.* logger names with the actual server name."""
    def filter(self, record):
        if record.name.startswith("uvicorn"):
            record.name = _SERVER_NAME
        return True


_handler = logging.StreamHandler()
_handler.setFormatter(DefaultFormatter("%(levelprefix)s %(name)s: %(message)s"))
_handler.addFilter(_ServerNameFilter())
logging.root.addHandler(_handler)
logging.root.setLevel(logging.INFO)

# Strip uvicorn's own handlers so everything propagates to root above.
for _name in ("uvicorn", "uvicorn.access", "uvicorn.error"):
    _uvicorn_logger = logging.getLogger(_name)
    _uvicorn_logger.handlers.clear()
    _uvicorn_logger.propagate = True

logging.getLogger("presidio-analyzer").setLevel(logging.ERROR)
