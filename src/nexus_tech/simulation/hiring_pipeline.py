"""Persistent hiring pipeline beyond direct one-click hiring."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from nexus_tech.domain.models import (
    CandidateTrait,
    GameState,
    HiringCandidate,
    HiringCandidateStage,
)
from nexus_tech.domain.money import format_money, quantize_money
from nexus_tech.simulation.balance import BALANCE
from nexus_tech.simulation.hiring import CandidateProfile, generate_candidate_pool
from nexus_tech.simulation.randomness import RandomSource
from nexus_tech.simulation.support import clamp_int
from nexus_tech.simulation.team import create_employee


@dataclass(frozen=True)
class HiringPipelineSummary:
    """Summary of one hiring pipeline action."""

    message: str


_TRAIT_ACCEPTANCE_BONUS = {
    CandidateTrait.STEADY_OPERATOR: 2,
    CandidateTrait.FAST_LEARNER: 4,
    CandidateTrait.EXPENSIVE_EXPERT: -6,
    CandidateTrait.BURNOUT_RISK: 1,
}


def source_candidates(state: GameState, *, count: int = 3) -> HiringPipelineSummary:
    """Source a fresh set of candidates into the persistent pipeline."""

    if state.company.cash_on_hand < BALANCE.hiring_source_cost:
        raise ValueError("Not enough cash to source hiring candidates this turn.")

    state.company.cash_on_hand = quantize_money(
        state.company.cash_on_hand - BALANCE.hiring_source_cost
    )
    _prune_terminal_candidates(state, current_turn=state.company.current_turn)
    existing_names = {candidate.full_name.casefold() for candidate in state.hiring_candidates}
    seed = (
        state.company.current_turn * 211
        + len(state.employees) * 17
        + len(state.hiring_candidates) * 29
        + len(state.customer_accounts) * 13
    )
    generated = generate_candidate_pool(RandomSource(seed=seed), count=count + 2)
    sourced_count = 0
    for profile in generated:
        if profile.full_name.casefold() in existing_names:
            continue
        state.hiring_candidates.append(_candidate_from_profile(profile, state))
        existing_names.add(profile.full_name.casefold())
        sourced_count += 1
        if sourced_count >= count:
            break

    state.hiring_candidates = state.hiring_candidates[-BALANCE.hiring_pipeline_candidate_limit :]
    return HiringPipelineSummary(
        message=(f"Sourced {sourced_count} candidate(s). Cash -{BALANCE.hiring_source_cost}.")
    )


def interview_candidate(state: GameState, candidate_id: UUID) -> HiringPipelineSummary:
    """Advance one sourced candidate through an interview step."""

    candidate = get_hiring_candidate_by_id(state, candidate_id)
    if candidate.stage is not HiringCandidateStage.SCREENED:
        raise ValueError("Only screened candidates can be interviewed.")
    if state.company.cash_on_hand < BALANCE.hiring_interview_cost:
        raise ValueError("Not enough cash to run an interview this turn.")

    state.company.cash_on_hand = quantize_money(
        state.company.cash_on_hand - BALANCE.hiring_interview_cost
    )
    candidate.stage = HiringCandidateStage.INTERVIEWED
    candidate.interview_score = clamp_int(
        candidate.interview_score
        + BALANCE.hiring_interview_score_gain
        + (state.company.reputation // 10),
        0,
        BALANCE.hiring_interview_score_cap,
    )
    candidate.acceptance_chance = clamp_int(
        candidate.acceptance_chance
        + (candidate.interview_score // 6)
        + (state.company.reputation // 18),
    )
    candidate.expires_turn = state.company.current_turn + BALANCE.hiring_pipeline_candidate_ttl
    return HiringPipelineSummary(
        message=(
            f"Interviewed {candidate.full_name}. Acceptance now {candidate.acceptance_chance}% "
            f"and cash -{BALANCE.hiring_interview_cost}."
        )
    )


def screen_candidate(state: GameState, candidate_id: UUID) -> HiringPipelineSummary:
    """Run a lighter screening pass before investing in a full interview."""

    candidate = get_hiring_candidate_by_id(state, candidate_id)
    if candidate.stage is not HiringCandidateStage.SOURCED:
        raise ValueError("Only sourced candidates can be screened.")
    if state.company.cash_on_hand < BALANCE.hiring_screen_cost:
        raise ValueError("Not enough cash to screen a candidate this turn.")

    state.company.cash_on_hand = quantize_money(
        state.company.cash_on_hand - BALANCE.hiring_screen_cost
    )
    candidate.stage = HiringCandidateStage.SCREENED
    candidate.interview_score = clamp_int(
        candidate.interview_score
        + BALANCE.hiring_screen_score_gain
        + (state.company.reputation // 20),
        0,
        BALANCE.hiring_interview_score_cap,
    )
    candidate.acceptance_chance = clamp_int(
        candidate.acceptance_chance
        + BALANCE.hiring_screen_acceptance_gain
        + max(0, (state.company.reputation - 50) // 15)
        - (candidate.market_salary_pressure // 8),
    )
    candidate.market_salary_pressure = clamp_int(
        candidate.market_salary_pressure + BALANCE.hiring_salary_pressure_gain
    )
    candidate.offer_deadline_turn = max(
        candidate.offer_deadline_turn,
        state.company.current_turn + (BALANCE.hiring_pipeline_candidate_ttl - 1),
    )
    return HiringPipelineSummary(
        message=(
            f"Screened {candidate.full_name}. "
            f"Acceptance now {candidate.acceptance_chance}% and cash "
            f"-{BALANCE.hiring_screen_cost}."
        )
    )


def make_hiring_offer(state: GameState, candidate_id: UUID) -> HiringPipelineSummary:
    """Make an offer to an interviewed candidate and convert on acceptance."""

    candidate = get_hiring_candidate_by_id(state, candidate_id)
    if candidate.stage is not HiringCandidateStage.INTERVIEWED:
        raise ValueError("Only interviewed candidates are ready for an offer.")

    required_cash_buffer = quantize_money(
        candidate.salary_expectation * BALANCE.hiring_offer_cash_buffer_multiplier
    )
    if state.company.cash_on_hand < required_cash_buffer:
        raise ValueError(
            "Not enough cash buffer to make a credible offer to this candidate right now."
        )

    acceptance_score = clamp_int(
        candidate.acceptance_chance
        + (candidate.interview_score // BALANCE.hiring_acceptance_interview_divisor)
        + min(
            12,
            int(state.company.cash_on_hand / BALANCE.hiring_acceptance_cash_buffer_divisor),
        ),
    )
    if acceptance_score >= BALANCE.hiring_acceptance_offer_threshold:
        employee = create_employee(
            full_name=candidate.full_name,
            role=candidate.role,
            seniority=candidate.seniority,
            specialization=candidate.specialization,
            existing_employees=state.employees,
            trait=candidate.trait,
        )
        employee.salary = candidate.salary_expectation
        employee.productivity = clamp_int(candidate.expected_productivity)
        state.employees.append(employee)
        state.hiring_candidates = [
            active_candidate
            for active_candidate in state.hiring_candidates
            if active_candidate.id != candidate.id
        ]
        return HiringPipelineSummary(
            message=(
                f"{candidate.full_name} accepted the offer at "
                f"{format_money(candidate.salary_expectation)}. "
                "The team grows without using the quick-hire path."
            )
        )

    if acceptance_score >= BALANCE.hiring_acceptance_negotiate_threshold:
        candidate.negotiation_rounds += 1
        candidate.salary_expectation = quantize_money(
            candidate.salary_expectation + BALANCE.hiring_negotiation_salary_step
        )
        candidate.market_salary_pressure = clamp_int(
            candidate.market_salary_pressure + BALANCE.hiring_salary_pressure_gain
        )
        candidate.acceptance_chance = clamp_int(
            candidate.acceptance_chance + BALANCE.hiring_screen_acceptance_gain
        )
        candidate.offer_deadline_turn = max(
            state.company.current_turn + 1,
            candidate.offer_deadline_turn,
        )
        return HiringPipelineSummary(
            message=(
                f"{candidate.full_name} wants a stronger package. "
                f"Salary expectation rises to {format_money(candidate.salary_expectation)} "
                "and the candidate stays live for one more turn."
            )
        )

    candidate.stage = HiringCandidateStage.DECLINED
    candidate.expires_turn = state.company.current_turn + 1
    state.company.reputation = clamp_int(
        state.company.reputation - BALANCE.hiring_decline_reputation_loss
    )
    return HiringPipelineSummary(
        message=(
            f"{candidate.full_name} declined the offer. "
            f"Acceptance score landed at {acceptance_score}% and reputation "
            f"-{BALANCE.hiring_decline_reputation_loss}."
        )
    )


def age_hiring_candidates(state: GameState) -> None:
    """Age, expire, and prune candidates as turns advance."""

    retained_candidates: list[HiringCandidate] = []
    for candidate in state.hiring_candidates:
        if candidate.stage in {HiringCandidateStage.DECLINED, HiringCandidateStage.EXPIRED}:
            if state.company.current_turn > candidate.expires_turn:
                continue
            retained_candidates.append(candidate)
            continue

        if (
            state.company.current_turn > candidate.expires_turn
            or state.company.current_turn > candidate.offer_deadline_turn
        ):
            candidate.stage = HiringCandidateStage.EXPIRED
            candidate.expires_turn = state.company.current_turn + 1
            retained_candidates.append(candidate)
            continue

        stale_pressure = max(0, state.company.current_turn - candidate.sourced_turn - 1)
        if stale_pressure > 0:
            candidate.market_salary_pressure = clamp_int(
                candidate.market_salary_pressure + stale_pressure
            )
            candidate.salary_expectation = quantize_money(
                candidate.salary_expectation
                + (BALANCE.hiring_negotiation_salary_step * stale_pressure)
            )
            candidate.acceptance_chance = clamp_int(
                candidate.acceptance_chance - stale_pressure - (candidate.negotiation_rounds * 2)
            )
        retained_candidates.append(candidate)

    state.hiring_candidates = retained_candidates[-BALANCE.hiring_pipeline_candidate_limit :]


def get_hiring_candidate_by_id(state: GameState, candidate_id: UUID | None) -> HiringCandidate:
    """Resolve one candidate from the hiring pipeline."""

    if candidate_id is None:
        raise ValueError("This action requires selecting a hiring candidate.")

    for candidate in state.hiring_candidates:
        if candidate.id == candidate_id:
            return candidate
    raise ValueError("Selected hiring candidate was not found.")


def _candidate_from_profile(profile: CandidateProfile, state: GameState) -> HiringCandidate:
    acceptance_base = clamp_int(
        BALANCE.hiring_acceptance_base
        + (state.company.reputation // BALANCE.hiring_acceptance_reputation_divisor)
        - (state.finance.investor_pressure // 6)
        + _TRAIT_ACCEPTANCE_BONUS[profile.trait]
        + (2 if profile.seniority.value == "junior" else 0),
    )
    return HiringCandidate(
        full_name=profile.full_name,
        role=profile.role,
        seniority=profile.seniority,
        specialization=profile.specialization,
        trait=profile.trait,
        salary_expectation=profile.salary_expectation,
        expected_productivity=profile.expected_productivity,
        stage=HiringCandidateStage.SOURCED,
        sourced_turn=state.company.current_turn,
        expires_turn=state.company.current_turn + BALANCE.hiring_pipeline_candidate_ttl,
        offer_deadline_turn=(
            state.company.current_turn + (BALANCE.hiring_pipeline_candidate_ttl - 1)
        ),
        acceptance_chance=acceptance_base,
        market_salary_pressure=clamp_int(
            (8 if profile.seniority is not None and profile.seniority.value == "senior" else 4)
            + (6 if profile.trait is CandidateTrait.EXPENSIVE_EXPERT else 0)
            + (2 if profile.role.value == "engineer" else 0)
        ),
    )


def _prune_terminal_candidates(state: GameState, *, current_turn: int) -> None:
    state.hiring_candidates = [
        candidate
        for candidate in state.hiring_candidates
        if not (
            candidate.stage in {HiringCandidateStage.DECLINED, HiringCandidateStage.EXPIRED}
            and current_turn > candidate.expires_turn
        )
    ]
