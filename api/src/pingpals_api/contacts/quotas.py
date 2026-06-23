"""Per-user resource quotas (issue 040, SEC-6.3).

Bounds the number of contacts and categories and the size of any single import batch, so scheduler
evaluation stays bounded (NFR-1.1) and no account exhausts shared storage/workers. Quotas live
behind this config object so deployment values change without caller code changes (AC-05).
Exceeding a quota fails closed: the create/import is rejected with a field-level error and no
partial write (AC-01/AC-03/AC-04).
"""

from __future__ import annotations

from dataclasses import dataclass


class QuotaExceeded(Exception):
    """A per-user quota would be exceeded — reject with no partial write."""

    def __init__(self, field: str, message: str) -> None:
        super().__init__(message)
        self.field = field
        self.message = message


@dataclass(frozen=True)
class QuotaConfig:
    max_contacts: int = 5000
    max_categories: int = 200
    max_import_batch: int = 500

    def check_contacts(self, current_count: int) -> None:
        if current_count >= self.max_contacts:
            raise QuotaExceeded("contacts", "contact quota reached")

    def check_categories(self, current_count: int) -> None:
        if current_count >= self.max_categories:
            raise QuotaExceeded("categories", "category quota reached")

    def check_import_batch(self, batch_size: int) -> None:
        if batch_size > self.max_import_batch:
            raise QuotaExceeded("import", "import batch exceeds the per-batch limit")
