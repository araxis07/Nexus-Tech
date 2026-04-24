"""Commercial contract helpers for key accounts and enterprise revenue."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from nexus_tech.domain.models import (
    ContractBillingModel,
    ContractCadence,
    CustomerAccount,
    MarketSegment,
    PricingTier,
    Product,
)
from nexus_tech.domain.money import quantize_money
from nexus_tech.simulation.balance import BALANCE
from nexus_tech.simulation.support import clamp_int, clamp_rate


@dataclass(frozen=True)
class ContractSupportDelta:
    """Support-side drift created by one account during a turn."""

    support_load_delta: int
    open_tickets_delta: int
    sla_breach_delta: int


@dataclass(frozen=True)
class ContractRenewalDelta:
    """Commercial changes applied when an account renews successfully."""

    contract_value_delta: Decimal
    seat_delta: int
    usage_delta: int
    add_on_delta: int
    cadence_upgraded: bool
    downgraded: bool
    annual_prepay_enabled: bool


def calculate_account_recurring_revenue(account: CustomerAccount) -> Decimal:
    """Return one account's recurring value after its billing model is applied."""

    recurring_value = account.contract_value
    if account.billing_model is ContractBillingModel.SEAT_BASED:
        recurring_value += Decimal(account.seat_count) * BALANCE.contract_seat_unit_revenue
    elif account.billing_model is ContractBillingModel.USAGE_BASED:
        recurring_value += Decimal(account.usage_units) * BALANCE.contract_usage_unit_revenue
    recurring_value += (
        Decimal(account.add_on_count)
        * BALANCE.contract_add_on_unit_revenue_by_plan[account.plan_tier.value]
    )
    recurring_value = quantize_money(recurring_value)
    return quantize_money(recurring_value * (Decimal("1.0000") - account.discount_rate))


def build_contract_shape(
    segment: MarketSegment,
    *,
    pricing_tier: PricingTier,
) -> tuple[ContractBillingModel, int, int]:
    """Return the default billing structure for a newly created account."""

    billing_model = ContractBillingModel(
        BALANCE.contract_default_billing_model_by_segment[segment.value]
    )
    seat_count = BALANCE.contract_default_seat_commitment_by_segment[segment.value]
    usage_units = BALANCE.contract_default_usage_commitment_by_segment[segment.value]

    if pricing_tier is PricingTier.PREMIUM:
        if billing_model is ContractBillingModel.SEAT_BASED:
            seat_count += 4
        elif billing_model is ContractBillingModel.USAGE_BASED:
            usage_units += 6
    elif pricing_tier is PricingTier.BUDGET:
        if billing_model is ContractBillingModel.SEAT_BASED:
            seat_count = max(4, seat_count - 2)
        elif billing_model is ContractBillingModel.USAGE_BASED:
            usage_units = max(10, usage_units - 4)

    return billing_model, seat_count, usage_units


def apply_support_drift(
    account: CustomerAccount,
    product: Product,
    *,
    customer_success_bonus: int = 0,
) -> ContractSupportDelta:
    """Update support load, tickets, and SLA risk for one account."""

    ticket_relief = 0
    if getattr(account, "annual_prepay", False):
        ticket_relief += 1

    support_load_delta = clamp_int(
        (product.bug_level // BALANCE.key_account_support_load_bug_divisor)
        - (product.quality // BALANCE.key_account_support_load_quality_relief_divisor)
        - customer_success_bonus
        - BALANCE.key_account_support_load_cs_relief,
        -BALANCE.key_account_support_load_cap,
        BALANCE.key_account_support_load_cap,
    )
    account.support_load = clamp_int(account.support_load + support_load_delta)

    open_tickets_delta = clamp_int(
        (product.bug_level // BALANCE.contract_ticket_bug_divisor)
        + (account.support_load // BALANCE.key_account_support_load_bug_divisor)
        - (product.quality // BALANCE.contract_ticket_quality_relief_divisor)
        - customer_success_bonus
        - ticket_relief
        - BALANCE.contract_ticket_close_base_relief,
        -BALANCE.key_account_support_load_cap,
        BALANCE.key_account_support_load_cap,
    )
    account.open_tickets = max(0, account.open_tickets + open_tickets_delta)

    sla_breach_delta = clamp_int(
        (account.open_tickets // BALANCE.contract_sla_ticket_divisor)
        + (account.support_load // BALANCE.contract_sla_support_divisor)
        - (account.onboarding_health // BALANCE.contract_sla_onboarding_relief_divisor)
        - customer_success_bonus,
        -BALANCE.key_account_support_load_cap,
        BALANCE.key_account_support_load_cap,
    )
    account.sla_breach_risk = clamp_int(account.sla_breach_risk + sla_breach_delta)

    return ContractSupportDelta(
        support_load_delta=support_load_delta,
        open_tickets_delta=open_tickets_delta,
        sla_breach_delta=sla_breach_delta,
    )


def apply_commercial_renewal(
    account: CustomerAccount,
    *,
    customer_success_bonus: int = 0,
) -> ContractRenewalDelta:
    """Apply expansion or downgrade effects after a successful renewal."""

    contract_value_delta = Decimal("0.00")
    seat_delta = 0
    usage_delta = 0
    add_on_delta = 0
    cadence_upgraded = False
    downgraded = False
    annual_prepay_enabled = False

    healthy_account = (
        account.satisfaction >= BALANCE.key_account_satisfaction_good_threshold
        and account.onboarding_health >= BALANCE.key_account_onboarding_good_threshold
        and account.sla_breach_risk < BALANCE.contract_sla_risk_threshold
    )
    weak_account = (
        account.satisfaction <= BALANCE.contract_downgrade_satisfaction_threshold
        or account.sla_breach_risk >= BALANCE.contract_sla_severe_threshold
    )

    if healthy_account:
        if account.billing_model is ContractBillingModel.SEAT_BASED:
            seat_delta = BALANCE.contract_seat_expansion_gain + max(0, customer_success_bonus // 2)
            account.seat_count += seat_delta
        elif account.billing_model is ContractBillingModel.USAGE_BASED:
            usage_delta = BALANCE.contract_usage_expansion_gain + max(0, customer_success_bonus)
            account.usage_units += usage_delta
        else:
            contract_value_delta = BALANCE.contract_flat_expansion_contract_gain
            account.contract_value = quantize_money(account.contract_value + contract_value_delta)
        add_on_delta = BALANCE.contract_add_on_expansion_gain
        account.add_on_count += add_on_delta

        account.expansion_potential = clamp_int(account.expansion_potential - 4, 0, 100)
    elif weak_account:
        downgraded = True
        if account.billing_model is ContractBillingModel.SEAT_BASED and account.seat_count > 1:
            seat_delta = -min(account.seat_count - 1, BALANCE.contract_seat_downgrade_loss)
            account.seat_count += seat_delta
        elif account.billing_model is ContractBillingModel.USAGE_BASED and account.usage_units > 0:
            usage_delta = -min(account.usage_units, BALANCE.contract_usage_downgrade_loss)
            account.usage_units += usage_delta
        else:
            maximum_loss = quantize_money(
                max(
                    Decimal("0.00"), account.contract_value - BALANCE.key_account_min_contract_value
                )
            )
            contract_value_delta = -min(
                maximum_loss,
                BALANCE.contract_flat_downgrade_contract_loss,
            )
            account.contract_value = quantize_money(account.contract_value + contract_value_delta)
        add_on_delta = -min(account.add_on_count, BALANCE.contract_add_on_downgrade_loss)
        account.add_on_count += add_on_delta

    if (
        account.contract_cadence is ContractCadence.MONTHLY
        and account.satisfaction >= 78
        and account.onboarding_health >= 72
        and account.sla_breach_risk < BALANCE.contract_sla_risk_threshold
    ):
        account.contract_cadence = ContractCadence.ANNUAL
        account.discount_rate = clamp_rate(account.discount_rate + Decimal("0.0100"))
        cadence_upgraded = True
    if (
        account.contract_cadence is ContractCadence.ANNUAL
        and not account.annual_prepay
        and account.satisfaction >= BALANCE.key_account_satisfaction_good_threshold
        and account.invoice_risk < BALANCE.contract_invoice_risk_threshold
    ):
        account.annual_prepay = True
        annual_prepay_enabled = True

    return ContractRenewalDelta(
        contract_value_delta=contract_value_delta,
        seat_delta=seat_delta,
        usage_delta=usage_delta,
        add_on_delta=add_on_delta,
        cadence_upgraded=cadence_upgraded,
        downgraded=downgraded,
        annual_prepay_enabled=annual_prepay_enabled,
    )


def get_contract_interval(cadence: ContractCadence) -> int:
    """Return the turn interval between contract renewals."""

    if cadence is ContractCadence.MONTHLY:
        return BALANCE.key_account_monthly_renewal_interval
    return BALANCE.key_account_renewal_interval
