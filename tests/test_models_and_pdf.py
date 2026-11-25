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
    GROUPS,
    SEMANTIC_ARROW_LABELS,
    Circle,
    InvariantLabState,
    InvariantViolation,
    Rectangle,
    Square,
    SquareShape,
    Triangle,
    __version__,
    check_rectangle_contract,
    circle_area,
    composition_component_count,
    dispatch_draw,
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
