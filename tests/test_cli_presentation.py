from __future__ import annotations

from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

from _pytest.monkeypatch import MonkeyPatch
from rich.console import Console
from typer.testing import CliRunner

import nexus_tech.cli as cli_module
from nexus_tech.cli import app
from nexus_tech.content.models import ScenarioDefinition, ScenarioProductSeed
from nexus_tech.domain.models import (
    Company,
    CompanyStrategy,
    Employee,
    EmployeeRole,
    EventCategory,
    EventOption,
    GameState,
    LifecycleStage,
    PendingEvent,
    Product,
    Seniority,
)
from nexus_tech.presentation.dashboard import render_dashboard, render_turn_resolution
from nexus_tech.simulation.balance import BALANCE
from nexus_tech.simulation.engine import create_new_game, resolve_turn
from nexus_tech.simulation.randomness import RandomSource

runner = CliRunner()


def make_demo_state(*, include_pending_event: bool = False) -> GameState:
    primary_product = Product(
        name="Nexus One",
        lifecycle_stage=LifecycleStage.GROWTH,
        quality=66,
        bug_level=14,
        market_fit=58,
        technical_debt=20,
        user_count=48,
        revenue_per_user=Decimal("31.00"),
        feature_count=2,
        maintenance_cost=Decimal("320.00"),
        acquisition_rate=Decimal("0.0650"),
        churn_rate=Decimal("0.0460"),
    )
    secondary_product = Product(
        name="Nexus Flow",
        lifecycle_stage=LifecycleStage.PROTOTYPE,
        quality=49,
        bug_level=24,
        market_fit=41,
        technical_debt=28,
        user_count=11,
        revenue_per_user=Decimal("18.00"),
        feature_count=1,
        maintenance_cost=Decimal("180.00"),
        acquisition_rate=Decimal("0.0410"),
        churn_rate=Decimal("0.0530"),
    )
    employee = Employee(
        full_name="Ada Wong",
        role=EmployeeRole.ENGINEER,
        seniority=Seniority.MID,
        salary=Decimal("780.00"),
        energy=77,
        morale=73,
        productivity=69,
        specialization="platform",
        assigned_product_id=primary_product.id,
    )
    pending_event = None
    if include_pending_event:
        pending_event = PendingEvent(
            event_id="competitor_pressure",
            category=EventCategory.MARKET_OPPORTUNITY,
            title="Competitor Pressure",
            description="A rival launched a comparable feature this morning.",
            triggered_turn=3,
            cooldown_turns=4,
            target_product_id=primary_product.id,
            options=[
                EventOption(
                    id="counter_launch",
                    label="Counter-launch",
                    description="Push a fast response with some delivery risk.",
                )
            ],
        )
    return GameState(
        company=Company(
            name="NEXUS TECH",
            cash_on_hand=Decimal("8120.00"),
            reputation=56,
            current_turn=3,
        ),
        products=[primary_product, secondary_product],
        employees=[employee],
        pending_event=pending_event,
        action_points_remaining=BALANCE.actions_per_turn,
    )


def test_cli_help_lists_core_commands_and_debug_flag() -> None:
    result = runner.invoke(app, ["--help"])

    assert result.exit_code == 0
    assert "new-game" in result.output
    assert "load-game" in result.output
    assert "continue-last-game" in result.output
    assert "--debug" in result.output


def test_root_command_dispatches_to_start_new_game(
    monkeypatch: MonkeyPatch,
    tmp_path: Path,
) -> None:
    captured: dict[str, object] = {}

    def fake_start_new_game(
        company_name: str | None,
        product_name: str | None,
        scenario_id: str,
        seed: int | None,
        db_path: Path,
        slot_name: str,
    ) -> None:
        captured.update(
            company_name=company_name,
            product_name=product_name,
            scenario_id=scenario_id,
            seed=seed,
            db_path=db_path,
            slot_name=slot_name,
        )

    monkeypatch.setattr(cli_module, "start_new_game", fake_start_new_game)

    db_path = tmp_path / "demo.db"
    result = runner.invoke(
        app,
        [
            "--company-name",
            "Demo Corp",
            "--product-name",
            "Alpha",
            "--scenario",
            "vc_sprint",
            "--seed",
            "13",
            "--db-path",
            str(db_path),
            "--slot",
            "showcase",
        ],
    )

    assert result.exit_code == 0
    assert captured == {
        "company_name": "Demo Corp",
        "product_name": "Alpha",
        "scenario_id": "vc_sprint",
        "seed": 13,
        "db_path": db_path,
        "slot_name": "showcase",
    }


def test_new_game_command_dispatches_to_start_new_game(
    monkeypatch: MonkeyPatch,
    tmp_path: Path,
) -> None:
    captured: dict[str, object] = {}

    def fake_start_new_game(
        company_name: str | None,
        product_name: str | None,
        scenario_id: str,
        seed: int | None,
        db_path: Path,
        slot_name: str,
    ) -> None:
        captured.update(
            company_name=company_name,
            product_name=product_name,
            scenario_id=scenario_id,
            seed=seed,
            db_path=db_path,
            slot_name=slot_name,
        )

    monkeypatch.setattr(cli_module, "start_new_game", fake_start_new_game)

    db_path = tmp_path / "new-game.db"
    result = runner.invoke(
        app,
        [
            "new-game",
            "--company-name",
            "Demo Corp",
            "--product-name",
            "Beta",
            "--scenario",
            "bootstrap_studio",
            "--seed",
            "21",
            "--db-path",
            str(db_path),
            "--slot",
            "slot-b",
        ],
    )

    assert result.exit_code == 0
    assert captured["product_name"] == "Beta"
    assert captured["scenario_id"] == "bootstrap_studio"
    assert captured["seed"] == 21
    assert captured["db_path"] == db_path
    assert captured["slot_name"] == "slot-b"


def test_list_scenarios_command_renders_catalog(monkeypatch: MonkeyPatch) -> None:
    scenarios = (
        ScenarioDefinition(
            scenario_id="bootstrap_studio",
            title="Bootstrap Studio",
            description="A lean company with a modest runway.",
            company_name="Bootstrap Studio",
            company_strategy=CompanyStrategy.EFFICIENCY,
            cash_on_hand=Decimal("6400.00"),
            reputation=47,
            products=[
                ScenarioProductSeed(
                    key="core",
                    template_id="saas_tool",
                    name="Studio Suite",
                )
            ],
        ),
    )

    monkeypatch.setattr(cli_module, "get_available_scenarios", lambda: scenarios)

    result = runner.invoke(app, ["list-scenarios"])

    assert result.exit_code == 0
    assert "Scenario Catalog" in result.output
    assert "bootstrap_studio" in result.output
    assert "Bootstrap Studio" in result.output


def test_load_game_command_resumes_loaded_slot(
    monkeypatch: MonkeyPatch,
    tmp_path: Path,
) -> None:
    state = make_demo_state()
    captured: dict[str, object] = {}

    class FakeCoordinator:
        def __init__(self, db_path: Path) -> None:
            captured["db_path"] = db_path

        def load_game(self, slot_name: str) -> SimpleNamespace:
            captured["load_slot"] = slot_name
            return SimpleNamespace(
                slot_name=slot_name,
                state=state,
                rng=RandomSource(seed=11),
            )

    def fake_run_game_loop(
        *,
        state: GameState,
        rng: RandomSource,
        db_path: Path,
        slot_name: str,
    ) -> None:
        captured["loop_state"] = state
        captured["loop_seed"] = rng.seed
        captured["loop_db_path"] = db_path
        captured["loop_slot"] = slot_name

    monkeypatch.setattr(cli_module, "SaveLoadCoordinator", FakeCoordinator)
    monkeypatch.setattr(cli_module, "run_game_loop", fake_run_game_loop)

    db_path = tmp_path / "load.db"
    result = runner.invoke(app, ["load-game", "--db-path", str(db_path), "--slot", "showcase"])

    assert result.exit_code == 0
    assert captured["db_path"] == db_path
    assert captured["load_slot"] == "showcase"
    assert captured["loop_state"] == state
    assert captured["loop_seed"] == 11
    assert captured["loop_db_path"] == db_path
    assert captured["loop_slot"] == "showcase"


def test_continue_last_game_command_resumes_latest_slot(
    monkeypatch: MonkeyPatch,
    tmp_path: Path,
) -> None:
    state = make_demo_state()
    captured: dict[str, object] = {}

    class FakeCoordinator:
        def __init__(self, db_path: Path) -> None:
            captured["db_path"] = db_path

        def continue_last_game(self) -> SimpleNamespace:
            return SimpleNamespace(
                slot_name="latest",
                state=state,
                rng=RandomSource(seed=17),
            )

    def fake_run_game_loop(
        *,
        state: GameState,
        rng: RandomSource,
        db_path: Path,
        slot_name: str,
    ) -> None:
        captured["loop_state"] = state
        captured["loop_seed"] = rng.seed
        captured["loop_db_path"] = db_path
        captured["loop_slot"] = slot_name

    monkeypatch.setattr(cli_module, "SaveLoadCoordinator", FakeCoordinator)
    monkeypatch.setattr(cli_module, "run_game_loop", fake_run_game_loop)

    db_path = tmp_path / "continue.db"
    result = runner.invoke(app, ["continue-last-game", "--db-path", str(db_path)])

    assert result.exit_code == 0
    assert captured["db_path"] == db_path
    assert captured["loop_state"] == state
    assert captured["loop_seed"] == 17
    assert captured["loop_db_path"] == db_path
    assert captured["loop_slot"] == "latest"


def test_dashboard_rendering_contains_required_sections() -> None:
    state = make_demo_state(include_pending_event=True)
    console = Console(record=True, width=140)

    render_dashboard(console, state)
    output = console.export_text()

    assert "Company Overview" in output
    assert "Product Portfolio" in output
    assert "Team Table" in output
    assert "Action Menu" in output
    assert "Event Notification" in output
    assert "Strategy" in output
    assert "Price" in output


def test_turn_resolution_rendering_contains_summary_sections() -> None:
    state = create_new_game("NEXUS TECH", "Nexus One")
    resolution = resolve_turn(state, RandomSource(seed=5))
    console = Console(record=True, width=140)

    render_turn_resolution(console, resolution)
    output = console.export_text()

    assert f"Turn {resolution.resolved_turn} Summary" in output
    assert "Portfolio Results" in output
    assert "Outlook" in output
    assert "Cash On Hand" in output
