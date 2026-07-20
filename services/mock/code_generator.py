"""Generate realistic Python function code"""

import random
from dataclasses import dataclass
from typing import Optional


@dataclass
class FunctionCode:
    name: str
    source: str
    has_error_handling: bool
    exception_types: list[str]
    retry_logic: bool


