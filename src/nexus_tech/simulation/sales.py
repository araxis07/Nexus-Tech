"""Enterprise sales pipeline rules."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID

from nexus_tech.domain.models import (
    ContractCadence,
    CustomerAccount,
    GameState,
    MarketSegment,
    Product,
    SalesDeal,
    SalesDealStage,
)
from nexus_tech.domain.money import format_money, quantize_money
from nexus_tech.simulation.balance import BALANCE
from nexus_tech.simulation.support import clamp_int


@dataclass(frozen=True)
class SalesActionSummary:
    """Summary text for sales pipeline actions."""

    message: str


_NEXT_STAGE = {
    SalesDealStage.LEAD: SalesDealStage.DEMO,
    SalesDealStage.DEMO: SalesDealStage.PILOT,
    SalesDealStage.PILOT: SalesDealStage.CLOSED_WON,
}


def create_sales_deal(
    state: GameState,
    product: Product,
    *,
    marketing_bonus: int = 0,
) -> SalesActionSummary:
    """Create a new sales opportunity for a product."""

    if state.company.cash_on_hand < BALANCE.sales_deal_action_cost:
        required_cash = format_money(BALANCE.sales_deal_action_cost)
        raise ValueError(f"Not enough cash to source a deal. Need {required_cash}.")
    state.company.cash_on_hand = quantize_money(
        state.company.cash_on_hand - BALANCE.sales_deal_action_cost
    )
    value = quantize_money(
        BALANCE.sales_deal_base_value + (product.revenue_per_user * 4) + (product.market_fit * 2)
    )
    probability = clamp_int(
        22 + (product.market_fit // 3) + (product.quality // 5) + (marketing_bonus * 4),
        0,
        100,
    )
    deal = SalesDeal(
        product_id=product.id,
        name=f"{product.target_segment.value.title()} buyer: {product.name}",
        segment=product.target_segment,
        value=value,
        probability=probability,
        created_turn=state.company.current_turn,
        updated_turn=state.company.current_turn,
    )
    state.sales_deals.append(deal)
    return SalesActionSummary(
        message=(
            f"Created sales deal '{deal.name}' at {format_money(value)} potential value. "
            f"Probability {probability}%, cash -{BALANCE.sales_deal_action_cost}."
        )
    )


def advance_sales_deal(
    state: GameState,
    deal_id: UUID,
    *,
    marketing_bonus: int = 0,
) -> SalesActionSummary:
    """Advance one sales deal through demo, pilot, and close."""

    deal = next(
        (
            deal
            for deal in state.sales_deals
            if deal.id == deal_id
            and deal.stage not in {SalesDealStage.CLOSED_LOST, SalesDealStage.CLOSED_WON}
        ),
        None,
    )
    if deal is None:
        raise ValueError("Selected sales deal is not active.")
    if state.company.cash_on_hand < BALANCE.sales_deal_action_cost:
        required_cash = format_money(BALANCE.sales_deal_action_cost)
        raise ValueError(f"Not enough cash to advance this deal. Need {required_cash}.")

    state.company.cash_on_hand = quantize_money(
        state.company.cash_on_hand - BALANCE.sales_deal_action_cost
    )
    deal.probability = clamp_int(
        deal.probability + BALANCE.sales_deal_probability_gain + (marketing_bonus * 3),
        0,
        100,
    )
    deal.updated_turn = state.company.current_turn
    deal.stage = _NEXT_STAGE[deal.stage]
    if deal.stage is SalesDealStage.CLOSED_WON:
        _close_won_deal(state, deal)
        return SalesActionSummary(
            message=(
                f"Closed {deal.name}. New key account added at "
                f"{format_money(deal.value)} contract value."
            )
        )

    return SalesActionSummary(
        message=(
            f"Advanced {deal.name} to {deal.stage.value}. "
            f"Probability now {deal.probability}%, cash -{BALANCE.sales_deal_action_cost}."
        )
    )


def age_sales_pipeline(state: GameState) -> None:
    """Apply light decay to stale open deals."""

    for deal in state.sales_deals:
        if deal.stage in {SalesDealStage.CLOSED_LOST, SalesDealStage.CLOSED_WON}:
            continue
        stale_turns = state.company.current_turn - deal.updated_turn
        if stale_turns >= 3:
            deal.probability = clamp_int(deal.probability - 4, 0, 100)
        if deal.probability <= 8:
            deal.stage = SalesDealStage.CLOSED_LOST


def _close_won_deal(state: GameState, deal: SalesDeal) -> None:
    product = next(product for product in state.products if product.id == deal.product_id)
    product.user_count += BALANCE.sales_deal_user_gain_by_segment[product.target_segment.value]
    product.market_fit = clamp_int(product.market_fit + 1, 0, 100)
    state.company.reputation = clamp_int(state.company.reputation + 1, 0, 100)
    state.customer_accounts.append(
        CustomerAccount(
            name=deal.name,
            product_id=deal.product_id,
            segment=deal.segment,
            contract_value=deal.value,
            contract_cadence=(
                ContractCadence.ANNUAL
                if deal.segment is MarketSegment.ENTERPRISE
                else ContractCadence.MONTHLY
            ),
            discount_rate=Decimal("0.0000"),
            satisfaction=BALANCE.sales_deal_customer_satisfaction,
            onboarding_health=BALANCE.sales_deal_customer_satisfaction - 2,
            support_load=24 if deal.segment is MarketSegment.ENTERPRISE else 18,
            expansion_potential=BALANCE.sales_deal_customer_expansion,
            renewal_turn=state.company.current_turn + 4,
            churn_risk=18 if deal.segment is MarketSegment.ENTERPRISE else 22,
        )
    )
