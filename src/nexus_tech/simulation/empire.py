"""Long-run strategy layer for the optional Empire Mode scenario."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum

from nexus_tech.domain.models import (
    CampaignGoalId,
    CompetitorMove,
    GameState,
    MarketSegment,
)
from nexus_tech.simulation.support import clamp_int

EMPIRE_SCENARIO_ID = "empire_founder_journey"
EMPIRE_MIN_VICTORY_TURN = 25


class EmpireEraId(StrEnum):
    """Strategic eras used to pace a long-form Empire run."""

    FOUNDATION = "foundation"
    GROWTH = "growth"
    SCALE = "scale"
    EXPANSION = "expansion"
    LEGACY = "legacy"


class ScaleThesisId(StrEnum):
    """Long-run operating thesis derived from the selected campaign goal."""

    OPERATING_FLYWHEEL = "operating_flywheel"
    PLATFORM_ECOSYSTEM = "platform_ecosystem"
    CATEGORY_STANDARD = "category_standard"


class TerritoryStatus(StrEnum):
    """Readable control state for one customer territory."""

    UNTAPPED = "untapped"
    UNDER_PRESSURE = "under_pressure"
    CONTESTED = "contested"
    FOOTHOLD = "foothold"
    LEADING = "leading"


class EmpireCrisisId(StrEnum):
    """Cross-system pressure lanes that can dominate an Empire run."""

    PLATFORM_INTEGRITY = "platform_integrity"
    MARKET_BACKLASH = "market_backlash"
    LEADERSHIP_BOTTLENECK = "leadership_bottleneck"


@dataclass(frozen=True)
class EmpireEra:
    """One long-run chapter and its immediate operating objective."""

    era_id: EmpireEraId
    title: str
    turn_window: str
    objective: str
    progress: float


@dataclass(frozen=True)
class ScaleThesis:
    """Player-facing interpretation of an existing campaign goal."""

    thesis_id: ScaleThesisId
    title: str
    summary: str
    operating_rule: str


@dataclass(frozen=True)
class TerritorySnapshot:
    """Derived market-control snapshot for one existing customer segment."""

    segment: MarketSegment
    score: int
    status: TerritoryStatus
    active_products: int
    users: int
    active_accounts: int
    active_partners: int
    rival_pressure: int


@dataclass(frozen=True)
class EmpireCrisis:
    """The strongest current cross-system risk, if one is material."""

    crisis_id: EmpireCrisisId
    title: str
    severity: int
    detail: str


@dataclass(frozen=True)
class EmpireSnapshot:
    """Complete derived Empire plan used by reports and turn consequences."""

    era: EmpireEra
    thesis: ScaleThesis
    territories: tuple[TerritorySnapshot, ...]
    empire_score: int
    controlled_territories: int
    strongest_territory: TerritorySnapshot
    weakest_territory: TerritorySnapshot
    dominant_crisis: EmpireCrisis | None
    strategic_priority: str
    next_milestone: str


@dataclass(frozen=True)
class EmpireTurnSummary:
    """Compact result of Empire-only end-of-turn consequences."""

    reputation_delta: int
    rival_response: str
    thesis_effect: str
    crisis_effect: str
    summary: str


_THESIS_BY_GOAL = {
    CampaignGoalId.PROFIT_MACHINE: ScaleThesis(
        thesis_id=ScaleThesisId.OPERATING_FLYWHEEL,
        title="Operating Flywheel",
        summary="Compound profitable operations into reliability and board trust.",
        operating_rule="Positive cash flow steadily repairs the operating core.",
    ),
    CampaignGoalId.PORTFOLIO_EMPIRE: ScaleThesis(
        thesis_id=ScaleThesisId.PLATFORM_ECOSYSTEM,
        title="Platform Ecosystem",
        summary="Connect multiple products and segments into one defensible platform.",
        operating_rule="A diversified portfolio improves the weakest product-market fit.",
    ),
    CampaignGoalId.CATEGORY_LEADER: ScaleThesis(
        thesis_id=ScaleThesisId.CATEGORY_STANDARD,
        title="Category Standard",
        summary="Turn quality and trust into the standard competitors must follow.",
        operating_rule="Sustained portfolio quality converts into market reputation.",
    ),
}


def is_empire_scenario(scenario_id: str) -> bool:
    """Return whether a scenario activates the optional long-run layer."""

    return scenario_id == EMPIRE_SCENARIO_ID


def get_empire_era(turn: int) -> EmpireEra:
    """Return the five-era pacing model for a one-based turn number."""

    if turn <= 5:
        return EmpireEra(
            EmpireEraId.FOUNDATION,
            "Foundation",
            "Turns 1-5",
            "Build one reliable product loop and preserve strategic runway.",
            _era_progress(turn, 1, 5),
        )
    if turn <= 10:
        return EmpireEra(
            EmpireEraId.GROWTH,
            "Growth",
            "Turns 6-10",
            "Open a second growth engine without abandoning the core business.",
            _era_progress(turn, 6, 10),
        )
    if turn <= 16:
        return EmpireEra(
            EmpireEraId.SCALE,
            "Scale",
            "Turns 11-16",
            "Turn portfolio reach into repeatable operations and leadership depth.",
            _era_progress(turn, 11, 16),
        )
    if turn <= 24:
        return EmpireEra(
            EmpireEraId.EXPANSION,
            "Expansion",
            "Turns 17-24",
            "Control multiple territories while rivals attack your strongest position.",
            _era_progress(turn, 17, 24),
        )
    return EmpireEra(
        EmpireEraId.LEGACY,
        "Legacy",
        "Turn 25+",
        "Prove the company can sustain its thesis through mature-market pressure.",
        min(1.0, 0.2 + ((turn - 25) * 0.2)),
    )


def get_scale_thesis(goal_id: CampaignGoalId) -> ScaleThesis:
    """Map the selected campaign goal to its Empire-scale operating thesis."""

    return _THESIS_BY_GOAL[goal_id]


def build_empire_snapshot(state: GameState) -> EmpireSnapshot:
    """Derive the long-run strategy view without adding persistence fields."""

    territories = tuple(_build_territory(state, segment) for segment in MarketSegment)
    strongest = max(territories, key=lambda territory: (territory.score, territory.users))
    weakest = min(territories, key=lambda territory: (territory.score, territory.users))
    controlled = sum(
        territory.status in {TerritoryStatus.FOOTHOLD, TerritoryStatus.LEADING}
        for territory in territories
    )
    active_products = [product for product in state.products if product.is_active]
    leadership_depth = sum(employee.is_team_lead for employee in state.employees)
    territory_average = sum(territory.score for territory in territories) // len(territories)
    empire_score = clamp_int(
        territory_average
        + min(12, max(0, len(active_products) - 1) * 4)
        + (state.company.reputation // 10)
        + min(8, leadership_depth * 2)
        + min(8, max(0, int(state.company.cash_on_hand / Decimal("5000.00")))),
    )
    crisis = _find_dominant_crisis(state)
    era = get_empire_era(state.company.current_turn)
    thesis = get_scale_thesis(state.campaign_goal_id)
    return EmpireSnapshot(
        era=era,
        thesis=thesis,
        territories=territories,
        empire_score=empire_score,
        controlled_territories=controlled,
        strongest_territory=strongest,
        weakest_territory=weakest,
        dominant_crisis=crisis,
        strategic_priority=_build_strategic_priority(
            state,
            controlled_territories=controlled,
            crisis=crisis,
            thesis=thesis,
        ),
        next_milestone=_build_next_milestone(
            era,
            active_products=len(active_products),
            controlled_territories=controlled,
        ),
    )


def apply_empire_turn_effects(
    state: GameState,
    *,
    resolved_turn: int,
    net_cash_flow: Decimal,
) -> EmpireTurnSummary | None:
    """Apply deterministic thesis, crisis, and rival effects to Empire Mode only."""

    if not is_empire_scenario(state.scenario_id):
        return None

    snapshot = build_empire_snapshot(state)
    reputation_delta = 0
    thesis_effect = _apply_thesis_effect(state, snapshot.thesis, net_cash_flow)
    rival_response = _apply_rival_response(state, snapshot, resolved_turn)
    crisis_effect, crisis_reputation_delta = _apply_crisis_effect(
        state,
        snapshot.dominant_crisis,
    )
    reputation_delta += crisis_reputation_delta
    if snapshot.thesis.thesis_id is ScaleThesisId.CATEGORY_STANDARD:
        active_products = [product for product in state.products if product.is_active]
        average_quality = (
            sum(product.quality for product in active_products) // len(active_products)
            if active_products
            else 0
        )
        if average_quality >= 65:
            state.company.reputation = clamp_int(state.company.reputation + 1)
            reputation_delta += 1
            thesis_effect = "Category-level quality converted into one reputation point."

    updated = build_empire_snapshot(state)
    summary = f"{updated.era.title} | control {updated.controlled_territories}/4"
    return EmpireTurnSummary(
        reputation_delta=reputation_delta,
        rival_response=rival_response,
        thesis_effect=thesis_effect,
        crisis_effect=crisis_effect,
        summary=summary,
    )


def _build_territory(state: GameState, segment: MarketSegment) -> TerritorySnapshot:
    products = [
        product
        for product in state.products
        if product.is_active and product.target_segment is segment
    ]
    users = sum(product.user_count for product in products)
    average_quality = (
        sum(product.quality for product in products) // len(products) if products else 0
    )
    average_fit = (
        sum(product.market_fit for product in products) // len(products) if products else 0
    )
    accounts = [
        account
        for account in state.customer_accounts
        if account.status.value != "churned" and account.segment is segment
    ]
    product_ids = {product.id for product in products}
    partners = [
        partnership
        for partnership in state.partnerships
        if partnership.status.value != "paused" and partnership.product_id in product_ids
    ]
    rivals = [competitor for competitor in state.competitors if competitor.focus_segment is segment]
    rival_pressure = sum(
        ((competitor.strength + competitor.aggression + competitor.momentum) // 15)
        + (competitor.active_product_count * 2)
        + competitor.funding_level
        for competitor in rivals
    )
    market_signal = (
        (len(products) * 12)
        + min(18, users // 20)
        + (average_fit // 8)
        + (average_quality // 10)
        + (len(accounts) * 4)
        + (len(partners) * 3)
    )
    score = clamp_int(market_signal - (rival_pressure // 3)) if products else 0
    if score >= 70:
        status = TerritoryStatus.LEADING
    elif score >= 50:
        status = TerritoryStatus.FOOTHOLD
    elif score >= 32:
        status = TerritoryStatus.CONTESTED
    elif rival_pressure >= 12:
        status = TerritoryStatus.UNDER_PRESSURE
    else:
        status = TerritoryStatus.UNTAPPED
    return TerritorySnapshot(
        segment=segment,
        score=score,
        status=status,
        active_products=len(products),
        users=users,
        active_accounts=len(accounts),
        active_partners=len(partners),
        rival_pressure=rival_pressure,
    )


def _find_dominant_crisis(state: GameState) -> EmpireCrisis | None:
    active_products = [product for product in state.products if product.is_active]
    average_debt = (
        sum(product.technical_debt for product in active_products) // len(active_products)
        if active_products
        else 0
    )
    average_bugs = (
        sum(product.bug_level for product in active_products) // len(active_products)
        if active_products
        else 0
    )
    platform_severity = max(
        0,
        average_debt - 42,
        average_bugs - 32,
        state.support_program.backlog_queue // 2,
    )
    active_accounts = [
        account for account in state.customer_accounts if account.status.value != "churned"
    ]
    at_risk_accounts = sum(account.status.value == "at_risk" for account in active_accounts)
    average_rival_momentum = (
        sum(competitor.momentum for competitor in state.competitors) // len(state.competitors)
        if state.competitors
        else 0
    )
    market_severity = max(
        0,
        average_rival_momentum - 62,
        45 - state.company.reputation,
        at_risk_accounts * 8,
    )
    average_energy = (
        sum(employee.energy for employee in state.employees) // len(state.employees)
        if state.employees
        else 100
    )
    lead_count = sum(employee.is_team_lead for employee in state.employees)
    leadership_severity = max(
        0,
        (len(state.employees) - 3) * 3 if lead_count == 0 else 0,
        48 - average_energy,
    )
    candidates = (
        EmpireCrisis(
            EmpireCrisisId.PLATFORM_INTEGRITY,
            "Platform integrity",
            platform_severity,
            "Debt, defects, or support load are weakening the shared operating core.",
        ),
        EmpireCrisis(
            EmpireCrisisId.MARKET_BACKLASH,
            "Market backlash",
            market_severity,
            "Rival momentum, customer risk, or weak trust is eroding market control.",
        ),
        EmpireCrisis(
            EmpireCrisisId.LEADERSHIP_BOTTLENECK,
            "Leadership bottleneck",
            leadership_severity,
            "The organization has outgrown its leadership depth or available energy.",
        ),
    )
    dominant = max(candidates, key=lambda crisis: crisis.severity)
    return dominant if dominant.severity >= 8 else None


def _apply_thesis_effect(
    state: GameState,
    thesis: ScaleThesis,
    net_cash_flow: Decimal,
) -> str:
    active_products = [product for product in state.products if product.is_active]
    if thesis.thesis_id is ScaleThesisId.OPERATING_FLYWHEEL:
        if net_cash_flow <= 0 or not active_products:
            return "Flywheel inactive: restore positive cash flow."
        highest_debt = max(active_products, key=lambda product: product.technical_debt)
        highest_debt.technical_debt = clamp_int(highest_debt.technical_debt - 1)
        state.support_program.backlog_queue = max(0, state.support_program.backlog_queue - 1)
        state.finance.board_profitability_score = clamp_int(
            state.finance.board_profitability_score + 1
        )
        return "Positive cash flow repaired debt, backlog, and profitability confidence."
    if thesis.thesis_id is ScaleThesisId.PLATFORM_ECOSYSTEM:
        segment_count = len({product.target_segment for product in active_products})
        if len(active_products) < 2 or segment_count < 2:
            return "Ecosystem inactive: reach two products across two territories."
        weakest_fit = min(active_products, key=lambda product: product.market_fit)
        weakest_fit.market_fit = clamp_int(weakest_fit.market_fit + 1)
        state.finance.board_portfolio_focus_score = clamp_int(
            state.finance.board_portfolio_focus_score + 1
        )
        return "Portfolio diversity strengthened the weakest product-market fit."
    return "Quality below 65 pauses the Category Standard reputation effect."


def _apply_rival_response(
    state: GameState,
    snapshot: EmpireSnapshot,
    resolved_turn: int,
) -> str:
    if resolved_turn < 8 or resolved_turn % 4 != 0:
        return "Rivals are observing the current expansion posture."
    target_segment = snapshot.strongest_territory.segment
    candidates = [
        competitor for competitor in state.competitors if competitor.focus_segment is target_segment
    ]
    if not candidates:
        return f"No rival is positioned to counter {target_segment.value} this cycle."
    rival = max(candidates, key=lambda competitor: competitor.strength + competitor.momentum)
    rival.aggression = clamp_int(rival.aggression + 2)
    rival.momentum = clamp_int(rival.momentum + 2)
    rival.current_move = (
        CompetitorMove.DISCOUNT_PUSH
        if snapshot.thesis.thesis_id is ScaleThesisId.OPERATING_FLYWHEEL
        else CompetitorMove.FEATURE_SPRINT
    )
    return (
        f"{rival.name} countered the {target_segment.value} lead with "
        f"{rival.current_move.value.replace('_', ' ')}."
    )


def _apply_crisis_effect(
    state: GameState,
    crisis: EmpireCrisis | None,
) -> tuple[str, int]:
    if crisis is None:
        return "No empire-scale crisis is active.", 0
    if crisis.crisis_id is EmpireCrisisId.PLATFORM_INTEGRITY:
        state.finance.board_reliability_score = clamp_int(state.finance.board_reliability_score - 1)
        reputation_delta = -1 if crisis.severity >= 18 else 0
        state.company.reputation = clamp_int(state.company.reputation + reputation_delta)
        return "Platform strain reduced board reliability confidence.", reputation_delta
    if crisis.crisis_id is EmpireCrisisId.MARKET_BACKLASH:
        state.finance.board_confidence = clamp_int(state.finance.board_confidence - 1)
        reputation_delta = -1 if crisis.severity >= 18 else 0
        state.company.reputation = clamp_int(state.company.reputation + reputation_delta)
        return "Market backlash reduced board confidence.", reputation_delta
    state.finance.board_team_health_score = clamp_int(state.finance.board_team_health_score - 2)
    for employee in state.employees:
        employee.morale = clamp_int(employee.morale - 1)
    return "Leadership strain reduced team health and morale.", 0


def _build_strategic_priority(
    state: GameState,
    *,
    controlled_territories: int,
    crisis: EmpireCrisis | None,
    thesis: ScaleThesis,
) -> str:
    if crisis is not None:
        return f"Resolve {crisis.title.lower()}"
    active_products = [product for product in state.products if product.is_active]
    if len(active_products) < 2:
        return "Launch product 2"
    if controlled_territories < 2:
        return "Secure territory 2"
    if thesis.thesis_id is ScaleThesisId.OPERATING_FLYWHEEL:
        return "Stack profitable turns"
    if thesis.thesis_id is ScaleThesisId.PLATFORM_ECOSYSTEM:
        return "Build shared portfolio leverage"
    return "Hold average quality above 65"


def _build_next_milestone(
    era: EmpireEra,
    *,
    active_products: int,
    controlled_territories: int,
) -> str:
    if era.era_id is EmpireEraId.FOUNDATION:
        return "Growth at Turn 6 with a healthy core"
    if active_products < 2:
        return "Two active products"
    if controlled_territories < 2:
        return "Control two customer territories"
    if era.era_id in {EmpireEraId.GROWTH, EmpireEraId.SCALE}:
        return "Expansion at Turn 17 with resilient operations"
    if era.era_id is EmpireEraId.EXPANSION:
        return "Legacy victory gate at Turn 25"
    return "Complete the selected Scale Thesis"


def _era_progress(turn: int, start: int, end: int) -> float:
    return min(1.0, max(0.0, (turn - start + 1) / (end - start + 1)))
