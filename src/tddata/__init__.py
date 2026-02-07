# Copyright (C) 2020-2026 Daniel Kiyoyudi Komesu
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.


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

__version__ = "2.1.0"
