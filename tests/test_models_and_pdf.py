"""Unit and integration tests for oop_guide models and the PDF builder."""

from __future__ import annotations

import math
import re
import shutil
import subprocess
from pathlib import Path

import pytest

from oop_guide import (
    CASE_STUDIES,
    CONCEPTS,
    AbsorbanceDetector,
    AnalysisPipeline,
    AnalyticalSample,
    ArrheniusFirstOrderKinetics,
    CSTRMixing,
    CompetitiveInhibitionEnzyme,
    ConstantFirstOrderKinetics,
    ContractBreakingEnzyme,
    ContractBreakingReactionRateModel,
    DETECTOR_INTERFACE,
    Detector,
    DomainValidationError,
    ElectrochemicalSensor,
    ENZYME_INHERITANCE,
    FirstOrderReaction,
    FluorescenceDetector,
    GROUPS,
    KINETIC_POLYMORPHISM,
    MichaelisMentenEnzyme,
    MichaelisMentenKinetics,
    NumericalModelError,
    PlugFlowMixing,
    REACTOR_COMPOSITION,
    RateContractError,
    ReactionState,
    Reactor,
    SecondOrderKinetics,
    ZeroOrderKinetics,
    SODIUM_CHLORIDE,
    SOLUTION_ENCAPSULATION,
    SEMANTIC_ARROW_LABELS,
    Circle,
    InvariantLabState,
    InvariantViolation,
    Rectangle,
    Square,
    SquareShape,
    Solution,
    Triangle,
    __version__,
    check_rectangle_contract,
    check_enzyme_contract,
    circle_area,
    composition_component_count,
    dispatch_draw,
    dispatch_reaction_rate,
    reference_shapes,
    resolve_describe_overload,
    resolve_translate,
    runtime_draw_target,
    square_area,
    square_perimeter,
    subclass_explosion_count,
    triangle_area,
    validate_catalog,
)
from oop_guide.models import ENGINES, TRAIT_DIMENSIONS, engine_by_name
from oop_guide.pdf_builder import (
    ALLOWED_FONTS,
    DEFAULT_OUTPUT,
    GROUP_FIGURES,
    MIN_FONT_SIZE,
    build_pdf,
    deterministic_check_rows,
    figure_dispatch,
    figure_overload,
    main,
)

ROOT = Path(__file__).resolve().parents[1]
WEB_INDEX = ROOT / "web" / "index.html"


# --- catalog ---------------------------------------------------------------


def test_version_is_semver() -> None:
    assert re.fullmatch(r"\d+\.\d+\.\d+", __version__)


def test_four_structure_groups_and_membership() -> None:
    assert [g.title for g in GROUPS] == [
        "Object Lifecycle & State",
        "Contracts & Abstraction",
        "Code Reuse & Structure",
        "Polymorphic Dispatch",
    ]
    membership = {g.key: g.concept_keys for g in GROUPS}
    assert membership == {
        "lifecycle": ("class", "object", "constructor", "encapsulation"),
        "contracts": ("abstraction", "interface"),
        "reuse": ("inheritance", "composition"),
        "dispatch": ("polymorphism",),
    }


def test_catalog_is_consistent() -> None:
    report = validate_catalog()
    assert report.ok, report.problems


def test_concept_framing_is_accurate() -> None:
    by_key = {c.key: c for c in CONCEPTS}
    assert all("self-governing" not in c.narrative for c in CONCEPTS)
    assert "invariant" in by_key["object"].narrative
    ctor = by_key["constructor"].narrative
    for phrase in ("initial state", "dependencies", "invariants", "Languages differ"):
        assert phrase in ctor
    assert "access control" in by_key["encapsulation"].narrative
    assert "hiding implementation details" in by_key["abstraction"].narrative
    assert "substitutable" in by_key["inheritance"].narrative
    assert "has-a" in by_key["composition"].narrative
    poly = by_key["polymorphism"].narrative
    assert "runtime type" in poly and "signatures" in poly


def test_case_studies_cover_required_failures() -> None:
    titles = " | ".join(c.title for c in CASE_STUDIES)
    for needle in ("Liskov", "Fragile Base", "Diamond", "Subclass Explosion",
                   "Anemic Encapsulation", "Concrete Implementation Coupling"):
        assert needle in titles


# --- fuel invariant --------------------------------------------------------


def test_burn_and_refuel_within_bounds() -> None:
    tank = InvariantLabState(fuel_kg=600.0)
    tank = tank.burn(4)
    assert tank.fuel_kg == 500.0
    tank = tank.refuel(200)
    assert tank.fuel_kg == 700.0
    assert tank.headroom_kg() == 300.0
    assert tank.burn(28).fuel_kg == 0.0


@pytest.mark.parametrize("op,arg", [
    ("burn", -1), ("burn", 24.1), ("refuel", 0), ("refuel", -5), ("refuel", 400.1),
])
def test_rejected_operations_preserve_state(op: str, arg: float) -> None:
    tank = InvariantLabState(fuel_kg=600.0)
    with pytest.raises(InvariantViolation):
        getattr(tank, op)(arg)
    assert tank.fuel_kg == 600.0


def test_refuel_exactly_to_capacity_is_allowed() -> None:
    assert InvariantLabState(fuel_kg=600.0).refuel(400).fuel_kg == 1000.0


@pytest.mark.parametrize("kwargs", [
    {"fuel_kg": -1.0}, {"fuel_kg": 1001.0}, {"fuel_kg": 1.0, "capacity_kg": 0},
    {"fuel_kg": 1.0, "burn_rate_kg_s": 0},
])
def test_constructor_validates_invariant(kwargs: dict) -> None:
    with pytest.raises(InvariantViolation):
        InvariantLabState(**kwargs)


# --- scientific solution model --------------------------------------------


def test_solution_dilution_conserves_solute_and_objects_are_independent() -> None:
    solution_a = Solution(SODIUM_CHLORIDE, 0.100, 0.500, 298.15)
    solution_b = Solution(SODIUM_CHLORIDE, 0.250, 0.200, 298.15)
    assert solution_a is not solution_b
    assert solution_a.solute is solution_b.solute
    assert math.isclose(solution_a.solute_amount_mol, 0.050)
    solution_a.dilute(1.000)
    assert math.isclose(solution_a.solute_amount_mol, 0.050)
    assert math.isclose(solution_a.concentration_mol_l, 0.050)
    assert solution_a.volume_l == 1.000
    assert math.isclose(solution_b.concentration_mol_l, 0.250)
    assert solution_b.volume_l == 0.200


def test_solution_add_solute_and_remove_homogeneous_aliquot() -> None:
    solution = Solution(SODIUM_CHLORIDE, 0.100, 0.500, 298.15)
    solution.add_solute(0.010)
    assert math.isclose(solution.solute_amount_mol, 0.060)
    assert math.isclose(solution.concentration_mol_l, 0.120)
    solution.remove_volume(0.100)
    assert math.isclose(solution.volume_l, 0.400)
    assert math.isclose(solution.solute_amount_mol, 0.048)
    assert math.isclose(solution.concentration_mol_l, 0.120)


@pytest.mark.parametrize(
    "concentration,volume,temperature",
    [
        (-0.1, 0.5, 298.15),
        (0.1, 0, 298.15),
        (0.1, -0.5, 298.15),
        (0.1, 0.5, 0),
        (0.1, 0.5, -1),
        (float("nan"), 0.5, 298.15),
        (0.1, float("inf"), 298.15),
    ],
)
def test_solution_constructor_rejects_invalid_domain_state(
    concentration: float, volume: float, temperature: float
) -> None:
    with pytest.raises(DomainValidationError):
        Solution(SODIUM_CHLORIDE, concentration, volume, temperature)


@pytest.mark.parametrize(
    "operation,argument",
    [
        ("dilute", 0.5),
        ("dilute", -1),
        ("dilute", float("nan")),
        ("add_solute", 0),
        ("add_solute", -0.01),
        ("add_solute", float("inf")),
        ("remove_volume", 0),
        ("remove_volume", 0.5),
        ("remove_volume", 0.6),
    ],
)
def test_rejected_solution_operations_preserve_state(operation: str, argument: float) -> None:
    solution = Solution(SODIUM_CHLORIDE, 0.100, 0.500, 298.15)
    before = solution.snapshot()
    with pytest.raises(DomainValidationError):
        getattr(solution, operation)(argument)
    assert solution.snapshot() == before


def test_solution_reports_floating_point_limit_without_mutation() -> None:
    with pytest.raises(NumericalModelError):
        Solution(SODIUM_CHLORIDE, 1e308, 1e308, 298.15)
    solution = Solution(SODIUM_CHLORIDE, 1e308, 1.0, 298.15)
    before = solution.snapshot()
    with pytest.raises(NumericalModelError):
        solution.add_solute(1e308)
    assert solution.snapshot() == before


def test_solution_concept_schema_covers_the_reference_workbench() -> None:
    assert SOLUTION_ENCAPSULATION.oop_concept == "Encapsulation"
    assert {example.language for example in SOLUTION_ENCAPSULATION.code_examples} == {
        "Python", "Java", "TypeScript",
    }
    assert any("C1 V1 = C2 V2" in equation for equation in SOLUTION_ENCAPSULATION.governing_equations)
    assert {failure.category for failure in SOLUTION_ENCAPSULATION.failure_cases} == {
        "DOMAIN VALIDATION FAILURE", "SOFTWARE DESIGN FAILURE",
        "TYPE/CONTRACT FAILURE", "NUMERICAL/MODEL LIMITATION",
    }


def test_detector_contract_dispatch_and_calibrated_responses() -> None:
    sample = AnalyticalSample(SODIUM_CHLORIDE, 0.072)
    detectors = (
        (AbsorbanceDetector(10, 1), 0.72, "dimensionless absorbance"),
        (FluorescenceDetector(1000), 72, "RFU"),
        (ElectrochemicalSensor(200, 5), 19.4, "microA"),
    )
    for detector, expected, units in detectors:
        measurement = AnalysisPipeline(detector).analyze(sample)
        assert math.isclose(measurement.value, expected)
        assert measurement.units == units
        assert measurement.detector_name == type(detector).__name__
        assert math.isfinite(measurement.value)
    with pytest.raises(TypeError):
        AnalysisPipeline(object())
    with pytest.raises(DomainValidationError):
        AnalyticalSample(SODIUM_CHLORIDE, -1)
    with pytest.raises(NumericalModelError):
        AbsorbanceDetector(1e308, 1e308).measure(
            AnalyticalSample(SODIUM_CHLORIDE, 1)
        )


def test_enzyme_subtypes_satisfy_behavioral_contract() -> None:
    michaelis_menten = MichaelisMentenEnzyme(10, 0.05)
    competitive = CompetitiveInhibitionEnzyme(10, 0.05, 0.02, 0.03)
    for enzyme in (michaelis_menten, competitive):
        check = check_enzyme_contract(enzyme)
        assert check.holds, check.failures
        assert check.rates[0] == 0
        assert all(0 <= rate <= enzyme.vmax_umol_l_s for rate in check.rates)
    assert michaelis_menten.rate(0.05) == 5
    assert competitive.rate(0.05) < michaelis_menten.rate(0.05)
    broken = check_enzyme_contract(ContractBreakingEnzyme(10, 0.05))
    assert not broken.holds
    assert any("within [0, Vmax]" in failure for failure in broken.failures)
    with pytest.raises(DomainValidationError):
        michaelis_menten.rate(-0.1)


def test_reactor_composition_swaps_kinetics_and_mixing_models() -> None:
    cstr = Reactor(ConstantFirstOrderKinetics(0.1), CSTRMixing()).outlet(
        0.1, 10, 298.15
    )
    pfr = Reactor(ConstantFirstOrderKinetics(0.1), PlugFlowMixing()).outlet(
        0.1, 10, 298.15
    )
    assert math.isclose(cstr.outlet_mol_l, 0.05)
    assert math.isclose(pfr.outlet_mol_l, 0.1 * math.exp(-1))
    assert cstr.mixing_model == "CSTRMixing"
    assert pfr.mixing_model == "PlugFlowMixing"
    arrhenius = ArrheniusFirstOrderKinetics(0.2, 10000)
    expected_k = 0.2 * math.exp(-10000 / (8.31446261815324 * 298.15))
    assert math.isclose(arrhenius.rate_constant_s_inv(298.15), expected_k)
    with pytest.raises(DomainValidationError):
        Reactor(ConstantFirstOrderKinetics(0.1), CSTRMixing()).outlet(0.1, 10, 0)
    with pytest.raises(TypeError):
        Reactor(object(), CSTRMixing())


def test_kinetic_runtime_dispatch_uses_selected_rate_law() -> None:
    state = ReactionState(0.05)
    cases = (
        (ZeroOrderKinetics(0.01), 0.01),
        (FirstOrderReaction(0.1), 0.005),
        (SecondOrderKinetics(1), 0.0025),
        (MichaelisMentenKinetics(1e-5, 0.05), 5e-6),
    )
    for model, expected in cases:
        assert math.isclose(dispatch_reaction_rate(model, state), expected)
    with pytest.raises(RateContractError):
        dispatch_reaction_rate(ContractBreakingReactionRateModel(), state)
    with pytest.raises(NumericalModelError):
        dispatch_reaction_rate(FirstOrderReaction(1e308), ReactionState(1e308))


def test_scientific_workbench_schemas_cover_language_and_domain_questions() -> None:
    for spec in (DETECTOR_INTERFACE, ENZYME_INHERITANCE, REACTOR_COMPOSITION, KINETIC_POLYMORPHISM):
        assert spec.oop_question and spec.scientific_question and spec.computational_question
        assert {example.language for example in spec.code_examples} == {
            "Python", "Java", "TypeScript",
        }
        assert spec.governing_equations and spec.assumptions and spec.variables


def test_engine_swap_keeps_tank_and_changes_rate() -> None:
    tank = InvariantLabState(fuel_kg=600.0)
    ion = tank.swap_engine(engine_by_name("IonThruster"))
    assert ion.fuel_kg == 600.0
    assert ion.engine_name == "IonThruster"
    assert ion.max_burn_seconds() == 1200.0
    assert ion.burn(100).fuel_kg == 550.0
    with pytest.raises(KeyError):
        engine_by_name("WarpDrive")


# --- geometry & dispatch ---------------------------------------------------


def test_reference_geometry() -> None:
    assert round(circle_area(1.5), 4) == 7.0686
    assert square_area(3) == 9
    assert square_perimeter(3) == 12
    assert triangle_area(4, 3.5) == 7
    assert math.isclose(Circle(1.5).perimeter(), 3 * math.pi)
    with pytest.raises(ValueError):
        circle_area(0)


def test_runtime_dispatch_through_shape_reference() -> None:
    shapes = reference_shapes()
    assert [type(s) for s in shapes] == [Circle, SquareShape, Triangle]
    calls = dispatch_draw(shapes)
    assert [c.split(".")[0] for c in calls] == ["Circle", "Square", "Triangle"]
    assert runtime_draw_target("Circle") == "Circle.draw()"


def test_overload_resolution_by_signature() -> None:
    assert resolve_translate(1.0, 2.0) == "translate(float x, float y)"
    assert resolve_translate(1.0, 2.0, 3.0) == "translate(float x, float y, float z)"
    with pytest.raises(TypeError):
        resolve_translate(1.0)
    with pytest.raises(TypeError):
        resolve_translate(1.0, "2")
    # Static type picks the overload even when the runtime object is a Circle.
    assert resolve_describe_overload("Shape") == "describe(Shape s)"
    assert resolve_describe_overload("Circle") == "describe(Circle c)"


# --- Liskov & composition --------------------------------------------------


def test_liskov_rectangle_holds_square_fails() -> None:
    rect = check_rectangle_contract(Rectangle(1, 1))
    square = check_rectangle_contract(Square(1))
    assert rect.holds and rect.actual_area == 20
    assert not square.holds and square.actual_area == 16
    assert square.expected_area == 20


def test_subclass_explosion_vs_composition() -> None:
    sizes = [len(v) for v in TRAIT_DIMENSIONS.values()]
    assert sizes == [3, 2, 2]
    assert subclass_explosion_count(sizes) == 12
    assert composition_component_count(sizes) == 7
    assert subclass_explosion_count([4, 2, 2]) == 16
    assert composition_component_count([4, 2, 2]) == 8
    for bad in ([], [0, 2], [True]):
        with pytest.raises(ValueError):
            subclass_explosion_count(bad)


def test_engines_match_contract_figure() -> None:
    assert {e.name: e.burn_rate_kg_s for e in ENGINES} == {
        "ChemicalEngine": 25.0, "ColdGasThruster": 2.0, "IonThruster": 0.5,
    }


# --- figures ---------------------------------------------------------------


def test_figures_fit_frames_and_use_semantic_labels() -> None:
    for makers in GROUP_FIGURES.values():
        for make in makers:
            fig = make()
            assert fig.layout_problems() == []
            for edge in fig.edges:
                assert edge.label in SEMANTIC_ARROW_LABELS


def test_figure_4_1_is_pure_dispatch() -> None:
    fig = figure_dispatch()
    text = " ".join([fig.title, fig.caption] + [n.title for n in fig.nodes]
                    + [s for n in fig.nodes for s in n.signatures])
    assert {e.label for e in fig.edges} == {"dispatches to"}
    assert {n.title for n in fig.nodes} >= {"Circle", "Square", "Triangle"}
    for clutter in ("area", "perimeter", "7.0686", "r=1.5"):
        assert clutter not in text


def test_figure_4_2_is_signature_selection() -> None:
    fig = figure_overload()
    sigs = {s for n in fig.nodes for s in n.signatures}
    assert "translate(float x, float y)" in sigs
    assert "translate(float x, float y, float z)" in sigs
    assert {e.label for e in fig.edges} == {"matches"}
    assert "call signature" in fig.caption and "runtime object type" in fig.caption


def test_deterministic_check_rows() -> None:
    rows = deterministic_check_rows()
    assert rows["geometry"][0][1] == "7.0686"
    assert rows["geometry"][1][1:] == ("9", "12")
    assert rows["geometry"][2][1] == "7"
    outcomes = [r[2] for r in rows["fuel"]]
    assert outcomes[0] == "OK -> 500 kg" and outcomes[1] == "OK -> 700 kg"
    assert all("REJECTED" in o for o in outcomes[2:5])
    assert outcomes[5] == "OK -> 0 kg"
    assert [r[3] for r in rows["lsp"]] == ["HOLDS", "FAILS"]
    assert rows["explosion"] == [("3 x 2 x 2", "12", "3 + 2 + 2", "7")]


# --- PDF integration -------------------------------------------------------


@pytest.fixture(scope="module")
def built(tmp_path_factory: pytest.TempPathFactory):
    out = tmp_path_factory.mktemp("pdf") / "guide.pdf"
    return build_pdf(out)


def test_pdf_is_valid_and_non_empty(built) -> None:
    data = built.path.read_bytes()
    assert data.startswith(b"%PDF-")
    assert b"%%EOF" in data[-1024:]
    assert len(data) > 10_000
    assert built.pages >= 8


def test_pdf_includes_materials_worksheet(built) -> None:
    text = " ".join(built.texts)
    for phrase in ("Materials Lab", "Fine mesh", "sample.glyph()", "Print / Save session as PDF"):
        assert phrase in text


def test_pdf_typography_rules(built) -> None:
    assert built.fonts_used <= ALLOWED_FONTS
    assert built.min_font_size >= MIN_FONT_SIZE
    for font in built.fonts_used:
        for banned in ("Script", "Hand", "Caveat", "Comic", "Brush", "Marker"):
            assert banned.lower() not in font.lower()


def test_pdf_uses_every_semantic_arrow_label(built) -> None:
    assert set(built.arrow_labels) == set(SEMANTIC_ARROW_LABELS)
    assert built.figures == ["1.1", "2.1", "3.1", "4.1", "4.2"]


def test_pdf_has_no_leaked_font_or_prompt_strings(built) -> None:
    for s in built.texts:
        lowered = s.lower()
        for leak in ("font", "prompt", "todo", "lorem", "caveat", "kalam"):
            assert leak not in lowered, s


def test_pdf_build_is_deterministic(tmp_path: Path, built) -> None:
    again = build_pdf(tmp_path / "again.pdf")
    assert again.path.read_bytes() == built.path.read_bytes()


def test_cli_writes_default_location(tmp_path: Path, monkeypatch, capsys) -> None:
    monkeypatch.chdir(tmp_path)
    assert main([]) == 0
    out = tmp_path / DEFAULT_OUTPUT
    assert out.read_bytes()[:5] == b"%PDF-"
    assert "dist" in capsys.readouterr().out


def test_repository_pdf_builds_to_dist() -> None:
    report = build_pdf(ROOT / DEFAULT_OUTPUT)
    data = (ROOT / "dist" / "oop_visual_study_guide.pdf").read_bytes()
    assert report.pages >= 8 and data.startswith(b"%PDF")


# --- web workbench consistency --------------------------------------------


def test_web_workbench_mirrors_catalog() -> None:
    html = WEB_INDEX.read_text(encoding="utf-8")
    for group in GROUPS:
        assert group.title.replace("&", "&amp;") in html or group.title in html
    for concept in CONCEPTS:
        assert concept.name in html
    for case in CASE_STUDIES:
        assert case.title in html
    for label in SEMANTIC_ARROW_LABELS:
        assert label in html
    for feature in ("Narrative", "Conceptual Diagram", "Code vs. Trap",
                    "Invariant Lab", "translate(float x, float y, float z)"):
        assert feature in html
    for hexcode in ("#F7F3E8", "#E6DFC8", "#162B4D", "#9E3B24", "#1C5D58"):
        assert hexcode.lower() in html.lower()
    for feature in ("Solution State &amp; Dilution", "Scientific Model ↔ Software Model",
                    "C₁V₁ = C₂V₂", "DOMAIN VALIDATION FAILURE",
                    "SOLUTION_CONCEPT", "solution.dilute(finalVolumeL)"):
        assert feature in html
    assert "TODO" not in html
    assert not re.search(r"(src|href)\s*=\s*[\"']https?://", html)
    assert "@import" not in html and "url(http" not in html


def test_materials_experiment_logic() -> None:
    node = shutil.which("node")
    if node is None:
        pytest.skip("Node.js is required to exercise the inline browser model")
    html = WEB_INDEX.read_text(encoding="utf-8")
    model = html.split('<script id="materials-model">', 1)[1].split("</script>", 1)[0]
    checks = """
    const assert = require("node:assert/strict");
    const run = (key, changes = {}) => runMaterialExperiment(key, {
      material: "salt", amount: "12", delta: "-4", filter: "fine", instrument: "scale",
      ...changes,
    });
    const amounts = result => result.views.map(view => view.amount);
    assert.deepEqual(Object.keys(MATERIAL_LESSONS).sort(), ["abstraction", "class", "composition",
      "constructor", "encapsulation", "inheritance", "interface", "object", "polymorphism"]);
    assert.match(run("class").message, /A === B is false/);
    assert.deepEqual(amounts(run("object")), [8, 12]);
    for (const amount of ["", "-1", "25", "1.5"]) {
      assert.equal(run("constructor", { amount }).ok, false);
    }
    assert.equal(run("constructor", { amount: "24" }).ok, true);
    const rejected = run("encapsulation", { delta: "-13" });
    assert.equal(rejected.ok, false);
    assert.deepEqual(amounts(rejected), [12, 12]);
    assert.deepEqual(amounts(run("abstraction")), [12, 0]);
    assert.match(run("interface", { instrument: "counter" }).message, /12 particle unit/);
    assert.match(run("interface").message, /24 demo mass unit/);
    assert.deepEqual(amounts(run("composition", { material: "dye" })), [12, 12]);
    assert.match(run("composition", { material: "quartz", filter: "open" }).message, /36 demo mass unit/);
    for (const material of ["salt", "quartz", "dye"]) {
      assert.deepEqual(amounts(run("inheritance", { material })), [12, 11]);
      assert.equal(run("inheritance", { material, amount: "0" }).ok, true);
    }
    assert.equal(run("polymorphism", { material: "dye" }).right, "DyeSample.glyph()");
    assert.equal(run("polymorphism", { material: "quartz" }).views[0].glyph, "grain");
    """
    result = subprocess.run([node, "-"], input=model + checks, text=True,
                            capture_output=True, timeout=10)
    assert result.returncode == 0, result.stderr


def test_solution_browser_model() -> None:
    node = shutil.which("node")
    if node is None:
        pytest.skip("Node.js is required to exercise the inline browser model")
    html = WEB_INDEX.read_text(encoding="utf-8")
    model = html.split('<script id="solution-model">', 1)[1].split("</script>", 1)[0]
    checks = """
    "use strict";
    const assert = require("node:assert/strict");
    const close = (actual, expected) => assert.ok(Math.abs(actual - expected) < 1e-12,
      `${actual} is not close to ${expected}`);
    const nacl = new ChemicalSpecies("Sodium chloride", "NaCl", 58.44);
    const solution = new Solution(nacl, 0.100, 0.500, 298.15);
    const independent = new Solution(nacl, 0.250, 0.200, 298.15);
    assert.notEqual(solution, independent);
    assert.equal(solution.solute, independent.solute);
    assert.equal(solution.soluteAmountMol, 0.05);
    solution.dilute(1.000);
    assert.equal(solution.soluteAmountMol, 0.05);
    assert.equal(solution.concentrationMolL, 0.05);
    assert.equal(independent.concentrationMolL, 0.25);
    solution.addSolute(0.010);
    close(solution.concentrationMolL, 0.06);
    solution.removeVolume(0.100);
    assert.equal(solution.volumeL, 0.9);
    close(solution.concentrationMolL, 0.06);
    for (const [c, v, t] of [[-1, 1, 298], [1, 0, 298], [1, 1, 0], [1, 1, NaN]]) {
      assert.throws(() => new Solution(nacl, c, v, t), DomainValidationError);
    }
    assert.throws(() => new Solution(nacl, 1e308, 1e308, 298), NumericalModelError);
    const large = new Solution(nacl, 1e308, 1, 298);
    const largeBefore = large.snapshot();
    assert.throws(() => large.addSolute(1e308), NumericalModelError);
    assert.deepEqual(large.snapshot(), largeBefore);
    const before = solution.snapshot();
    assert.throws(() => solution.dilute(0.9), DomainValidationError);
    assert.throws(() => solution.addSolute(-1), DomainValidationError);
    assert.throws(() => solution.removeVolume(0.9), DomainValidationError);
    assert.deepEqual(solution.snapshot(), before);
    assert.equal(Reflect.set(solution, "concentrationMolL", -1), false);
    assert.equal(SOLUTION_CONCEPT.variables[0][2], "mol/L");
    """
    result = subprocess.run([node, "-"], input=model + checks, text=True,
                            capture_output=True, timeout=10)
    assert result.returncode == 0, result.stderr


def test_scientific_browser_models() -> None:
    node = shutil.which("node")
    if node is None:
        pytest.skip("Node.js is required to exercise the inline browser model")
    html = WEB_INDEX.read_text(encoding="utf-8")
    model = html.split('<script id="scientific-models">', 1)[1].split("</script>", 1)[0]
    checks = """
    "use strict";
    const assert = require("node:assert/strict");
    const close = (actual, expected) => assert.ok(Math.abs(actual - expected) < 1e-12,
      `${actual} is not close to ${expected}`);
    const sample = new AnalyticalSample(0.072);
    const measurements = [
      [new AbsorbanceDetector(10, 1), 0.72, "dimensionless absorbance"],
      [new FluorescenceDetector(1000), 72, "RFU"],
      [new ElectrochemicalSensor(200, 5), 19.4, "microA"],
    ];
    for (const [detector, expected, units] of measurements) {
      const actual = new AnalysisPipeline(detector).analyze(sample);
      close(actual.value, expected);
      assert.equal(actual.units, units);
      assert.equal(actual.detectorName, detector.constructor.name);
    }
    assert.throws(() => new AnalysisPipeline({ measure() {} }), TypeError);
    assert.throws(() => new AnalyticalSample(-1), DomainValidationError);
    assert.throws(() => new AbsorbanceDetector(1e308, 1e308).measure(new AnalyticalSample(1)),
      NumericalModelError);
    const mm = new MichaelisMentenEnzyme(10, 0.05);
    const competitive = new CompetitiveInhibitionEnzyme(10, 0.05, 0.02, 0.03);
    assert.equal(checkEnzymeContract(mm, [0, 0.01, 0.05, 0.2]).holds, true);
    assert.equal(checkEnzymeContract(competitive, [0, 0.01, 0.05, 0.2]).holds, true);
    assert.ok(competitive.rate(0.05) < mm.rate(0.05));
    assert.equal(checkEnzymeContract(new ContractBreakingEnzyme(10, 0.05),
      [0, 0.01, 0.05, 0.2]).holds, false);
    const cstr = new Reactor(new ConstantFirstOrderKinetics(0.1), new CSTRMixing())
      .outlet(0.1, 10, 298.15);
    const pfr = new Reactor(new ConstantFirstOrderKinetics(0.1), new PlugFlowMixing())
      .outlet(0.1, 10, 298.15);
    close(cstr.outletMolL, 0.05);
    close(pfr.outletMolL, 0.1 * Math.exp(-1));
    const expectedK = 0.2 * Math.exp(-10000 / (GAS_CONSTANT_J_MOL_K * 298.15));
    close(new ArrheniusFirstOrderKinetics(0.2, 10000).rateConstant(298.15), expectedK);
    const state = new ReactionState(0.05);
    for (const [model, expected] of [
      [new ZeroOrderKinetics(0.01), 0.01],
      [new FirstOrderReaction(0.1), 0.005],
      [new SecondOrderKinetics(1), 0.0025],
      [new MichaelisMentenKinetics(1e-5, 0.05), 5e-6],
    ]) close(dispatchReactionRate(model, state), expected);
    assert.throws(() => dispatchReactionRate(new ContractBreakingReactionRateModel(), state),
      RateContractError);
    """
    result = subprocess.run([node, "-"], input=model + checks, text=True,
                            capture_output=True, timeout=10)
    assert result.returncode == 0, result.stderr
