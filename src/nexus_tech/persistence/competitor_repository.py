"""Repository for persisted competitors."""

from __future__ import annotations

import sqlite3
from uuid import UUID

from nexus_tech.domain.models import Competitor, CompetitorMove, MarketSegment, PricingTier


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
                archetype_id,
                focus_segment,
                strength,
                aggression,
                pricing_tier,
                active_product_count,
                current_move,
                momentum,
                funding_level
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    slot_name,
                    str(competitor.id),
                    index,
                    competitor.name,
                    competitor.archetype_id,
                    competitor.focus_segment.value,
                    competitor.strength,
                    competitor.aggression,
                    competitor.pricing_tier.value,
                    competitor.active_product_count,
                    competitor.current_move.value,
                    competitor.momentum,
                    competitor.funding_level,
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
                archetype_id,
                focus_segment,
                strength,
                aggression,
                pricing_tier,
                active_product_count,
                current_move,
                momentum,
                funding_level
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
                archetype_id=row["archetype_id"],
                focus_segment=MarketSegment(row["focus_segment"]),
                strength=row["strength"],
                aggression=row["aggression"],
                pricing_tier=PricingTier(row["pricing_tier"]),
                active_product_count=row["active_product_count"],
                current_move=CompetitorMove(row["current_move"] or CompetitorMove.HOLD.value),
                momentum=row["momentum"] if row["momentum"] is not None else 50,
                funding_level=row["funding_level"] if row["funding_level"] is not None else 0,
            )
            for row in rows
        ]
