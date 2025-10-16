"""Protocols (interfaces) for dependency inversion."""

from typing import Protocol


class IssueEnricher(Protocol):
    """Protocol for issue data enrichers."""

    async def enrich(self, payload: dict) -> dict:
        """Enrich payload with additional data.

        Args:
            payload: Original webhook payload

        Returns:
            Enriched payload with additional data
        """
        ...
