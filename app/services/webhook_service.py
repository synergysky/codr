"""Webhook processing service."""
import logging
from typing import Sequence

from .protocols import IssueEnricher

logger = logging.getLogger(__name__)


class WebhookService:
    """Service for processing webhook payloads.

    Follows Single Responsibility Principle:
    - Only responsible for orchestrating enrichers
    - Doesn't know about HTTP, GitHub, or Zenhub details
    """

    def __init__(self, enrichers: Sequence[IssueEnricher]):
        """Initialize webhook service with enrichers.

        Args:
            enrichers: List of enrichers to apply to payloads
        """
        self.enrichers = enrichers

    async def process_webhook(self, payload: dict) -> dict:
        """Process webhook payload by enriching it.

        Args:
            payload: Original webhook payload

        Returns:
            Enriched payload with data from all enrichers

        Note:
            If an enricher fails, it logs a warning and continues
            with other enrichers (graceful degradation).
        """
        enriched = payload.copy()

        for enricher in self.enrichers:
            try:
                result = await enricher.enrich(enriched)
                # Merge enriched data back into payload
                enriched.update(result)
            except Exception as e:
                logger.warning(f"Enricher {enricher.__class__.__name__} failed: {e}")
                # Continue with other enrichers

        return enriched
