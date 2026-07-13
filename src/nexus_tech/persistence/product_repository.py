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
        """Upsert the product portfolio without breaking dependent rows."""

        connection.execute(
            """
            UPDATE products
            SET display_order = -(display_order + 1)
            WHERE slot_name = ?
            """,
            (slot_name,),
        )
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
                package_catalog_depth,
                add_on_catalog_depth,
                target_segment,
                is_active
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(slot_name, product_id) DO UPDATE SET
                display_order = excluded.display_order,
                name = excluded.name,
                lifecycle_stage = excluded.lifecycle_stage,
                quality = excluded.quality,
                bug_level = excluded.bug_level,
                market_fit = excluded.market_fit,
                technical_debt = excluded.technical_debt,
                user_count = excluded.user_count,
                revenue_per_user = excluded.revenue_per_user,
                feature_count = excluded.feature_count,
                maintenance_cost = excluded.maintenance_cost,
                acquisition_rate = excluded.acquisition_rate,
                churn_rate = excluded.churn_rate,
                pricing_tier = excluded.pricing_tier,
                packaging_strategy = excluded.packaging_strategy,
                package_catalog_depth = excluded.package_catalog_depth,
                add_on_catalog_depth = excluded.add_on_catalog_depth,
                target_segment = excluded.target_segment,
                is_active = excluded.is_active
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
                    product.package_catalog_depth,
                    product.add_on_catalog_depth,
                    product.target_segment.value,
                    int(product.is_active),
                )
                for index, product in enumerate(products)
            ],
        )

    def delete_missing(
        self,
        connection: sqlite3.Connection,
        slot_name: str,
        products: list[Product],
    ) -> None:
        """Delete stale products after every dependent table has been replaced."""

        product_ids = [str(product.id) for product in products]
        placeholders = ", ".join("?" for _ in product_ids)
        connection.execute(
            f"""
            DELETE FROM products
            WHERE slot_name = ?
              AND product_id NOT IN ({placeholders})
            """,
            (slot_name, *product_ids),
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
                package_catalog_depth,
                add_on_catalog_depth,
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
                package_catalog_depth=row["package_catalog_depth"] or 0,
                add_on_catalog_depth=row["add_on_catalog_depth"] or 0,
                target_segment=MarketSegment(row["target_segment"] or MarketSegment.STARTUP.value),
                is_active=bool(row["is_active"]),
            )
            for row in rows
        ]
