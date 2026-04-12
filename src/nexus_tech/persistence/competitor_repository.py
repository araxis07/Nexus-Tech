"""Repository for persisted competitors."""

from __future__ import annotations

import sqlite3
from uuid import UUID

from nexus_tech.domain.models import Competitor, MarketSegment, PricingTier


class CompetitorRepository:
    """Save and load competitors for a slot."""

    def save_all(
        self,
        connection: sqlite3.Connection,
        slot_name: str,
        competitors: list[Competitor],
    ) -> None:
        """Replace the competitor roster for one slot."""

        connection.execute("DELETE FROM competitors WHERE slot_name = ?", (slot_name,))
        connection.executemany(
            """
            INSERT INTO competitors (
                slot_name,
                competitor_id,
                display_order,
                name,
                focus_segment,
                strength,
                aggression,
                pricing_tier,
                active_product_count
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    slot_name,
                    str(competitor.id),
                    index,
                    competitor.name,
                    competitor.focus_segment.value,
                    competitor.strength,
                    competitor.aggression,
                    competitor.pricing_tier.value,
                    competitor.active_product_count,
                )
                for index, competitor in enumerate(competitors)
            ],
        )

    def load_all(self, connection: sqlite3.Connection, slot_name: str) -> list[Competitor]:
        """Load competitors for one slot."""

        rows = connection.execute(
            """
            SELECT
                competitor_id,
                name,
                focus_segment,
                strength,
                aggression,
                pricing_tier,
                active_product_count
            FROM competitors
            WHERE slot_name = ?
            ORDER BY display_order ASC
            """,
            (slot_name,),
        ).fetchall()
        return [
            Competitor(
                id=UUID(row["competitor_id"]),
                name=row["name"],
                focus_segment=MarketSegment(row["focus_segment"]),
                strength=row["strength"],
                aggression=row["aggression"],
                pricing_tier=PricingTier(row["pricing_tier"]),
                active_product_count=row["active_product_count"],
            )
            for row in rows
        ]
