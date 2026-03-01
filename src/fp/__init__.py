"""Foundation Protocol Python runtime."""

from .app import FPClient, FPServer, make_default_entity
from .protocol import *  # noqa: F401,F403

__version__ = "0.1.0"

__all__ = ["FPClient", "FPServer", "make_default_entity", "__version__"]
