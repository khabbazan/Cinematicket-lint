"""Shared violation type for all custom_lint checks."""

from dataclasses import dataclass


@dataclass
class Violation:
    path: str
    line: int
    code: str
    message: str

    def __str__(self) -> str:
        return f'{self.path}:{self.line}: {self.code} {self.message}'
