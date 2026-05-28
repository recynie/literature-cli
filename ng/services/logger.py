from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class Logger(Protocol):
    """Logging interface required by the service layer."""

    def _add_log(self, key: str, message: str) -> None: ...

    def notify(self, message: str, severity: str = "information") -> None: ...


class NullLogger:
    """No-op logger for service usage outside the CLI."""

    def __bool__(self) -> bool:
        return False

    def _add_log(self, key: str, message: str) -> None:
        pass

    def notify(self, message: str, severity: str = "information") -> None:
        pass
