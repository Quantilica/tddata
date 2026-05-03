from . import downloader
from .constants import (
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
    from . import plot, reader

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

__version__ = "2.1.1"
