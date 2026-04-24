"""Repository for persisted products."""

from __future__ import annotations

import sqlite3
from decimal import Decimal
from uuid import UUID

from nexus_tech.domain.models import (
    LifecycleStage,
    MarketSegment,
    PackagingStrategy,
    PricingTier,
    Product,
)


class ProductRepository:
    """Save and load products for a slot."""

    def save_all(
        self,
        connection: sqlite3.Connection,
        slot_name: str,
        products: list[Product],
    ) -> None:
        """Replace the product portfolio for one slot."""

        connection.execute("DELETE FROM products WHERE slot_name = ?", (slot_name,))
        connection.executemany(
            """
            INSERT INTO products (
                slot_name,
                product_id,
                display_order,
                name,
                lifecycle_stage,
                quality,
                bug_level,
                market_fit,
                technical_debt,
                user_count,
                revenue_per_user,
                feature_count,
                maintenance_cost,
                acquisition_rate,
                churn_rate,
                pricing_tier,
                packaging_strategy,
                target_segment,
                is_active
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    slot_name,
                    str(product.id),
                    index,
                    product.name,
                    product.lifecycle_stage.value,
                    product.quality,
                    product.bug_level,
                    product.market_fit,
                    product.technical_debt,
                    product.user_count,
                    str(product.revenue_per_user),
                    product.feature_count,
                    str(product.maintenance_cost),
                    str(product.acquisition_rate),
                    str(product.churn_rate),
                    product.pricing_tier.value,
                    product.packaging_strategy.value,
                    product.target_segment.value,
                    int(product.is_active),
                )
                for index, product in enumerate(products)
            ],
        )

    def load_all(self, connection: sqlite3.Connection, slot_name: str) -> list[Product]:
        """Load products for one slot."""

        rows = connection.execute(
            """
            SELECT
                product_id,
                name,
                lifecycle_stage,
                quality,
                bug_level,
                market_fit,
                technical_debt,
                user_count,
                revenue_per_user,
                feature_count,
                maintenance_cost,
                acquisition_rate,
                churn_rate,
                pricing_tier,
                packaging_strategy,
                target_segment,
                is_active
            FROM products
            WHERE slot_name = ?
            ORDER BY display_order ASC
            """,
            (slot_name,),
        ).fetchall()

        return [
            Product(
                id=UUID(row["product_id"]),
                name=row["name"],
                lifecycle_stage=LifecycleStage(row["lifecycle_stage"]),
                quality=row["quality"],
                bug_level=row["bug_level"],
                market_fit=row["market_fit"],
                technical_debt=row["technical_debt"],
                user_count=row["user_count"],
                revenue_per_user=Decimal(row["revenue_per_user"]),
                feature_count=row["feature_count"],
                maintenance_cost=Decimal(row["maintenance_cost"]),
                acquisition_rate=Decimal(row["acquisition_rate"]),
                churn_rate=Decimal(row["churn_rate"]),
                pricing_tier=PricingTier(row["pricing_tier"] or PricingTier.STANDARD.value),
                packaging_strategy=PackagingStrategy(
                    row["packaging_strategy"] or PackagingStrategy.STREAMLINED.value
                ),
                target_segment=MarketSegment(row["target_segment"] or MarketSegment.STARTUP.value),
                is_active=bool(row["is_active"]),
            )
            for row in rows
        ]
