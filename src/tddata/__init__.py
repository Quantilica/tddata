from quantilica_core.logging import get_logger

__version__ = "2.1.1"
logger = get_logger(__name__)

from . import downloader  # noqa: E402  (must follow `logger` definition)
from .constants import (  # noqa: E402
    AccountStatus,
    BondType,
    Channel,
    Column,
    Gender,
    MaritalStatus,
    OperationType,
    TradedLast12Months,
)

# Optional imports - only available if analysis extras are installed
try:
    from . import plot, reader  # noqa: E402

    _HAS_ANALYSIS = True
except ImportError:
    _HAS_ANALYSIS = False
    plot = None  # type: ignore
    reader = None  # type: ignore

__all__ = [
    "downloader",
    "Column",
    "BondType",
    "OperationType",
    "Channel",
    "Gender",
    "MaritalStatus",
    "AccountStatus",
    "TradedLast12Months",
]

if _HAS_ANALYSIS:
    __all__.extend(["plot", "reader"])
