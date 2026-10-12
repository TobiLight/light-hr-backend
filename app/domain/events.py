# File: app/domain/events.py
# Author: Oluwatobiloba Light Agunloye
"""Framework-independent domain-event contracts."""
from dataclasses import dataclass
from datetime import UTC, datetime, timezone
from uuid import UUID, uuid4


@dataclass(frozen=True, slots=True, kw_only=True)
class DomainEvent:
    event_id: UUID
    occurred_at: datetime

    @classmethod
    def create_metadata(cls) -> dict[str, object]:
        return {
            "event_id": uuid4(),
            "occurred_at": datetime.now(UTC),
        }