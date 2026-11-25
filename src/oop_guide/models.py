"""Typed content models and deterministic OOP math / invariant helpers.

Everything in this module is pure and deterministic: the same inputs always
produce the same outputs. The PDF builder and the tests consume these helpers
so that every number printed in the study guide is computed, never typed by
hand.
"""

from __future__ import annotations

import math
from abc import ABC, abstractmethod
from dataclasses import dataclass, field, replace
from typing import Iterable, Sequence

# ---------------------------------------------------------------------------
# Content specs
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ConceptSpec:
    """One core OOP concept and the three views the guide renders for it."""

    key: str
    name: str
    group_key: str
    narrative: str
    diagram_caption: str
    code: str
    trap: str


@dataclass(frozen=True)
class GroupSpec:
    """One of the four structure groups."""

    key: str
    number: int
    title: str
    summary: str
    concept_keys: tuple[str, ...]


@dataclass(frozen=True)
class CaseStudySpec:
    """A production failure or behavioral case study."""

    key: str
    title: str
    symptom: str
    root_cause: str
    fix: str
    related_concepts: tuple[str, ...]


class InvariantViolation(ValueError):
    """Raised when an operation would break an object's invariant."""


@dataclass(frozen=True)
class InvariantLabState:
    """Propellant tank used by the Break It / Invariant Lab.

    Invariant: ``0 <= fuel_kg <= capacity_kg``. The only way to change
    ``fuel_kg`` is through :meth:`burn` and :meth:`refuel`, which validate
    their arguments and reject any request that would break the invariant.
    Rejected operations leave the state unchanged (a new state is only
    returned on success).
    """

    fuel_kg: float
    capacity_kg: float = 1000.0
    burn_rate_kg_s: float = 25.0
    engine_name: str = "ChemicalEngine"

    def __post_init__(self) -> None:
        if self.capacity_kg <= 0:
            raise InvariantViolation("capacity_kg must be > 0")
        if self.burn_rate_kg_s <= 0:
            raise InvariantViolation("burn_rate_kg_s must be > 0")
        if not 0.0 <= self.fuel_kg <= self.capacity_kg:
            raise InvariantViolation(
                f"fuel_kg={self.fuel_kg} outside [0, {self.capacity_kg}]"
            )

    def burn(self, dt: float) -> "InvariantLabState":
        """Burn for ``dt`` seconds at the engine's burn rate."""
        if dt < 0:
            raise InvariantViolation("burn(dt) requires dt >= 0")
        required = round(self.burn_rate_kg_s * dt, 6)
        if required > self.fuel_kg:
            raise InvariantViolation(
                f"burn({dt:g}) needs {required:g} kg but only "
                f"{self.fuel_kg:g} kg remain"
            )
        return replace(self, fuel_kg=round(self.fuel_kg - required, 6))

    def refuel(self, kg: float) -> "InvariantLabState":
        """Add ``kg`` of propellant without exceeding capacity."""
        if kg <= 0:
            raise InvariantViolation("refuel(kg) requires kg > 0")
        if self.fuel_kg + kg > self.capacity_kg:
            raise InvariantViolation(
                f"refuel({kg:g}) would exceed capacity "
                f"({self.fuel_kg:g} + {kg:g} > {self.capacity_kg:g})"
            )
        return replace(self, fuel_kg=round(self.fuel_kg + kg, 6))

    def max_burn_seconds(self) -> float:
        return self.fuel_kg / self.burn_rate_kg_s

    def headroom_kg(self) -> float:
        return round(self.capacity_kg - self.fuel_kg, 6)

    def swap_engine(self, engine: "EngineSpec") -> "InvariantLabState":
        """Composition: replace the collaborating engine, keep the tank."""
        return replace(
            self, burn_rate_kg_s=engine.burn_rate_kg_s, engine_name=engine.name
        )


# ---------------------------------------------------------------------------
# Shapes: runtime dispatch + exact geometry
# ---------------------------------------------------------------------------


def circle_area(r: float) -> float:
    _require_positive(r=r)
    return math.pi * r * r


def circle_perimeter(r: float) -> float:
    _require_positive(r=r)
    return 2 * math.pi * r


def square_area(s: float) -> float:
    _require_positive(s=s)
    return s * s


def square_perimeter(s: float) -> float:
    _require_positive(s=s)
    return 4 * s


def triangle_area(b: float, h: float) -> float:
    _require_positive(b=b, h=h)
    return 0.5 * b * h


def _require_positive(**values: float) -> None:
    for name, value in values.items():
        if value <= 0:
            raise ValueError(f"{name} must be > 0, got {value}")


class Shape(ABC):
    """Abstract base: callers depend on ``draw()`` and ``area()`` only."""

    @abstractmethod
    def draw(self) -> str: ...

    @abstractmethod
    def area(self) -> float: ...


@dataclass(frozen=True)
class Circle(Shape):
    r: float

    def draw(self) -> str:
        return f"Circle.draw() -> circle r={self.r:g}"

    def area(self) -> float:
        return circle_area(self.r)

    def perimeter(self) -> float:
        return circle_perimeter(self.r)


@dataclass(frozen=True)
class SquareShape(Shape):
    s: float

    def draw(self) -> str:
        return f"Square.draw() -> square s={self.s:g}"

    def area(self) -> float:
        return square_area(self.s)

    def perimeter(self) -> float:
        return square_perimeter(self.s)


@dataclass(frozen=True)
class Triangle(Shape):
    b: float
    h: float

    def draw(self) -> str:
        return f"Triangle.draw() -> triangle b={self.b:g}, h={self.h:g}"

    def area(self) -> float:
        return triangle_area(self.b, self.h)


def reference_shapes() -> tuple[Shape, ...]:
    """The three shapes used throughout Figure 4.1 and the labs."""
    return (Circle(1.5), SquareShape(3.0), Triangle(4.0, 3.5))


def dispatch_draw(shapes: Iterable[Shape]) -> list[str]:
    """Call ``draw()`` through the ``Shape`` reference: runtime dispatch."""
    return [shape.draw() for shape in shapes]


# ---------------------------------------------------------------------------
# Overloading vs overriding
# ---------------------------------------------------------------------------

TRANSLATE_SIGNATURES: dict[int, str] = {
    2: "translate(float x, float y)",
    3: "translate(float x, float y, float z)",
}


def resolve_translate(*args: float) -> str:
    """Pick a ``translate`` overload from the call signature (arity/types).

    Mirrors compile-time overload resolution in Java / C++ / C#: the chosen
    signature depends only on the arguments at the call site, never on the
    runtime type of the receiver.
    """
    for arg in args:
        if isinstance(arg, bool) or not isinstance(arg, (int, float)):
            raise TypeError(f"no translate overload accepts {type(arg).__name__}")
    try:
        return TRANSLATE_SIGNATURES[len(args)]
    except KeyError:
        raise TypeError(
            f"no translate overload takes {len(args)} argument(s)"
        ) from None


DESCRIBE_OVERLOADS: dict[str, str] = {
    "Shape": "describe(Shape s)",
    "Circle": "describe(Circle c)",
}


def resolve_describe_overload(static_type: str) -> str:
    """Overload selected from the *declared* (static) type of the argument."""
    if static_type not in DESCRIBE_OVERLOADS:
        raise TypeError(f"no describe overload for static type {static_type}")
    return DESCRIBE_OVERLOADS[static_type]


def runtime_draw_target(runtime_type: str) -> str:
    """Override selected from the *runtime* type of the receiver."""
    targets = {"Circle": "Circle.draw()", "Square": "Square.draw()",
               "Triangle": "Triangle.draw()"}
    if runtime_type not in targets:
        raise TypeError(f"{runtime_type} does not implement Shape")
    return targets[runtime_type]


# ---------------------------------------------------------------------------
# Liskov: Rectangle vs Square
# ---------------------------------------------------------------------------


class Rectangle:
    """Contract: width and height can be set independently."""

    def __init__(self, width: float, height: float) -> None:
        self._width = width
        self._height = height

    @property
    def width(self) -> float:
        return self._width

    @property
    def height(self) -> float:
        return self._height

    def set_width(self, width: float) -> None:
        self._width = width

    def set_height(self, height: float) -> None:
        self._height = height

    def area(self) -> float:
        return self._width * self._height


class Square(Rectangle):
    """Keeps its own invariant (width == height) and thereby breaks the
    Rectangle contract that setters are independent."""

    def __init__(self, side: float) -> None:
        super().__init__(side, side)

    def set_width(self, width: float) -> None:
        self._width = width
        self._height = width

    def set_height(self, height: float) -> None:
        self._width = height
        self._height = height


@dataclass(frozen=True)
class LiskovResult:
    type_name: str
    width: float
    height: float
    expected_area: float
    actual_area: float

    @property
    def holds(self) -> bool:
        return math.isclose(self.expected_area, self.actual_area)


def check_rectangle_contract(
    shape: Rectangle, width: float = 5.0, height: float = 4.0
) -> LiskovResult:
    """Client code written against Rectangle: set w, set h, expect w*h."""
    shape.set_width(width)
    shape.set_height(height)
    return LiskovResult(
        type_name=type(shape).__name__,
        width=width,
        height=height,
        expected_area=width * height,
        actual_area=shape.area(),
    )


# ---------------------------------------------------------------------------
# Composition vs subclass explosion
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class EngineSpec:
    name: str
    burn_rate_kg_s: float


ENGINES: tuple[EngineSpec, ...] = (
    EngineSpec("ChemicalEngine", 25.0),
    EngineSpec("ColdGasThruster", 2.0),
    EngineSpec("IonThruster", 0.5),
)

TRAIT_DIMENSIONS: dict[str, tuple[str, ...]] = {
    "Engine": tuple(e.name for e in ENGINES),
    "Guidance": ("StarTracker", "GpsGuidance"),
    "Comms": ("RadioLink", "LaserLink"),
}


def subclass_explosion_count(dimension_sizes: Sequence[int]) -> int:
    """Concrete subclasses needed to cover every combination by inheritance."""
    _validate_sizes(dimension_sizes)
    return math.prod(dimension_sizes)


def composition_component_count(dimension_sizes: Sequence[int]) -> int:
    """Component classes needed when each trait is a swappable collaborator."""
    _validate_sizes(dimension_sizes)
    return sum(dimension_sizes)


def _validate_sizes(dimension_sizes: Sequence[int]) -> None:
    if not dimension_sizes:
        raise ValueError("at least one trait dimension is required")
    for size in dimension_sizes:
        if isinstance(size, bool) or not isinstance(size, int) or size < 1:
            raise ValueError(f"dimension sizes must be positive ints, got {size!r}")


def engine_by_name(name: str) -> EngineSpec:
    for engine in ENGINES:
        if engine.name == name:
            return engine
    raise KeyError(name)


# ---------------------------------------------------------------------------
# Catalog content
# ---------------------------------------------------------------------------

GROUPS: tuple[GroupSpec, ...] = (
    GroupSpec(
        "lifecycle", 1, "Object Lifecycle & State",
        "How state comes into existence and stays valid.",
        ("class", "object", "constructor", "encapsulation"),
    ),
    GroupSpec(
        "contracts", 2, "Contracts & Abstraction",
        "What a caller may rely on, separated from how it is done.",
        ("abstraction", "interface"),
    ),
    GroupSpec(
        "reuse", 3, "Code Reuse & Structure",
        "Specialization (is-a) versus assembly from parts (has-a).",
        ("inheritance", "composition"),
    ),
    GroupSpec(
        "dispatch", 4, "Polymorphic Dispatch",
        "Which implementation runs: runtime type vs call signature.",
        ("polymorphism",),
    ),
)

CONCEPTS: tuple[ConceptSpec, ...] = (
    ConceptSpec(
        "class", "Class", "lifecycle",
        "A Solution class defines the shared state and operations for a chemical "
        "solution model. Its concentration is derived from solute amount and "
        "volume; it is not the physical solution itself.",
        "Solution contains a ChemicalSpecies and stores amount (mol), volume (L), "
        "and temperature (K); concentration is amount / volume.",
        "class Solution:\n"
        "    def __init__(self, solute, concentration_mol_l, volume_l, temperature_k): ...\n"
        "    def dilute(self, final_volume_l): ...\n"
        "    def add_solute(self, amount_mol): ...",
        "Trap: using an object-shaped label without scientific state or behavior. "
        "A software model is not the physical system.",
    ),
    ConceptSpec(
        "object", "Object", "lifecycle",
        "Each Solution object has independent amount, volume, and temperature "
        "state even when two solutions reference the same ChemicalSpecies value.",
        "Diluting Solution A changes its concentration while a separate Solution "
        "B containing the same solute remains unchanged.",
        "a = Solution(NACL, 0.100, 0.500, 298.15)\n"
        "b = Solution(NACL, 0.250, 0.200, 298.15)\n"
        "a.dilute(1.000)  # A: 0.050 mol/L; B unchanged",
        "Trap: confusing a shared species definition with shared mutable solution "
        "state; separate solution objects must remain independent.",
    ),
    ConceptSpec(
        "constructor", "Constructor / Initialization", "lifecycle",
        "Initialization establishes the initial state, binds required "
        "dependencies, and validates invariants before the Solution can be "
        "used. Languages differ in constructor and initialization semantics.",
        "C >= 0 mol/L; V > 0 L; T > 0 K. These are software model constraints, "
        "not physical laws enforced by OOP.",
        "solution = Solution(NACL, concentration_mol_l=0.100,\n"
        "                    volume_l=0.500, temperature_k=298.15)",
        "Trap: allowing a partially initialized object or claiming the "
        "constructor's validation enforces a law of nature.",
    ),
    ConceptSpec(
        "encapsulation", "Encapsulation", "lifecycle",
        "Encapsulation is access control in service of invariant protection: "
        "the Solution keeps amount and volume behind domain operations such "
        "as dilute(), add_solute(), and remove_volume().",
        "A dilution call validates final volume, conserves amount, updates "
        "volume, and derives the new concentration.",
        "solution.dilute(final_volume_l=1.000)\n"
        "# C2 = C1 V1 / V2 = 0.050 mol/L",
        "Trap: independently setting concentration while amount and volume "
        "remain unchanged creates contradictory model state.",
    ),
    ConceptSpec(
        "abstraction", "Abstraction", "contracts",
        "Abstraction exposes the essential capability and hides implementation "
        "details: AnalysisPipeline needs Detector.measure(sample), not "
        "instrument-specific calibration fields or equations.",
        "The pipeline can analyze a sample using Beer-Lambert absorbance, "
        "linear fluorescence, or calibrated electrochemical response.",
        "class AnalysisPipeline:\n"
        "    def __init__(self, detector: Detector): self._detector = detector\n"
        "    def analyze(self, sample): return self._detector.measure(sample)",
        "Trap: a leaky contract that forces the pipeline to inspect detector "
        "types or apply instrument-specific calibration itself.",
    ),
    ConceptSpec(
        "interface", "Interface", "contracts",
        "Detector.measure(sample) is a behavioral contract returning a "
        "Measurement with a finite value, units, implementation, and equation. "
        "The pipeline depends on this contract, not one instrument.",
        "AbsorbanceDetector, FluorescenceDetector, and ElectrochemicalSensor "
        "implement the measurement operation with distinct simplified models.",
        "interface Detector { Measurement measure(AnalyticalSample sample); }\n"
        "final class AnalysisPipeline {\n"
        "  private final Detector detector;\n"
        "  Measurement analyze(AnalyticalSample s) { return detector.measure(s); }\n"
        "}",
        "Trap: sharing a method name without honoring its output, units, and "
        "failure contract does not make implementations interchangeable.",
    ),
    ConceptSpec(
        "inheritance", "Inheritance", "reuse",
        "A biochemical rate subtype must be behaviorally substitutable wherever "
        "EnzymeRateModel is expected. Biological relatedness alone does not "
        "prove software substitutability.",
        "MichaelisMentenEnzyme and CompetitiveInhibitionEnzyme both return "
        "finite, non-negative rates bounded by Vmax and zero at [S] = 0.",
        "class EnzymeRateModel(ABC):\n"
        "    @abstractmethod\n"
        "    def rate(self, substrate_mol_l: float) -> float: ...\n"
        "rate = enzyme.rate(substrate_mol_l)  # test subtype contract",
        "Trap: assuming a biological subtype is valid because of its taxonomy. "
        "A negative rate or a violated base promise fails substitutability.",
    ),
    ConceptSpec(
        "composition", "Composition", "reuse",
        "A Reactor has kinetic and mixing components and delegates to both. "
        "Swapping either model changes the calculation without adding a host "
        "subclass for each combination.",
        "First-order CSTR and plug-flow models predict distinct outlet "
        "concentrations for the same feed, k, and residence time.",
        "reactor = Reactor(ArrheniusFirstOrderKinetics(A, Ea), CSTRMixing())\n"
        "result = reactor.outlet(Cin_mol_l, tau_s, temperature_k)",
        "Trap: subclassing Reactor for every pair of kinetic and mixing models "
        "duplicates configuration instead of composing behavior.",
    ),
    ConceptSpec(
        "polymorphism", "Polymorphism", "dispatch",
        "Calling model.rate(state) dispatches by the receiver's runtime type "
        "to the kinetic model override. "
        "Overriding is distinct from overloading: Java resolves overloads at "
        "compile time; Python has no native signature-based overload dispatch; "
        "TypeScript overload signatures describe one JavaScript implementation.",
        "Zero-, first-, and second-order laws and the simplified "
        "Michaelis-Menten model predict different rates from substrate state.",
        "model: ReactionRateModel = FirstOrderReaction(k1_s_inv=0.10)\n"
        "rate = model.rate(ReactionState(substrate_mol_l=0.050))\n"
        "# runtime override returns 0.005 mol/(L s)",
        "Trap: treating override dispatch as overload resolution, or assuming "
        "a method name alone determines which scientific rate law applies.",
    ),
)

CASE_STUDIES: tuple[CaseStudySpec, ...] = (
    CaseStudySpec(
        "liskov", "Liskov Substitution: Rectangle vs. Square",
        "Layout code resizes a shape with set_width(5); set_height(4) and the "
        "area comes back 16 instead of 20.",
        "Rectangle promises independent width/height mutation; Square enforces "
        "width == height and silently breaks that promise.",
        "Make shapes immutable or give Square and Rectangle a common Shape "
        "abstraction instead of an is-a link.",
        ("inheritance", "polymorphism"),
    ),
    CaseStudySpec(
        "fragile-base", "Fragile Base Classes & Deep Hierarchies",
        "A one-line change in BaseVehicle.update() breaks seven subclasses three "
        "levels down.",
        "Subclasses depend on undocumented call order inside base methods; a "
        "five-level tree couples every layer to every other.",
        "Keep hierarchies shallow, mark extension points explicitly (template "
        "method / final), prefer composition for variation.",
        ("inheritance", "encapsulation"),
    ),
    CaseStudySpec(
        "diamond", "Diamond Inheritance Conflicts",
        "Amphibian inherits from Car and Boat; Amphibian.move() calls the wrong "
        "parent and the shared Vehicle state is initialized twice.",
        "Two inheritance paths reach one base; method resolution order and "
        "shared-state ownership become ambiguous.",
        "Use interfaces for capability, composition for behavior, and C++ "
        "virtual inheritance or Python MRO + super() only deliberately.",
        ("inheritance", "interface"),
    ),
    CaseStudySpec(
        "explosion", "Combinatorial Subclass Explosion vs. Composition",
        "3 engines x 2 guidance x 2 comms requires 12 concrete Spacecraft "
        "subclasses; adding one engine adds 4 more.",
        "Independent axes of variation were encoded in a single inheritance "
        "tree, so classes multiply instead of add.",
        "Compose traits: 3 + 2 + 2 = 7 component classes, swapped at runtime.",
        ("composition", "inheritance"),
    ),
    CaseStudySpec(
        "anemic", "Anemic Encapsulation (Getters/Setters Everywhere)",
        "Callers set fuel_kg = -50 through setFuelKg() and the tank reports "
        "negative propellant.",
        "Every field has a public setter, so business rules live in callers "
        "and the object guards nothing.",
        "Replace setters with intention-revealing operations (burn, refuel) "
        "that validate the invariant.",
        ("encapsulation", "object"),
    ),
    CaseStudySpec(
        "coupling", "Concrete Implementation Coupling",
        "Swapping ChemicalEngine for IonThruster requires edits in 40 call "
        "sites and a full regression test.",
        "Clients construct and type against the concrete class instead of the "
        "Propulsion contract.",
        "Depend on the interface and inject the implementation through the "
        "constructor.",
        ("interface", "abstraction", "constructor"),
    ),
)

SEMANTIC_ARROW_LABELS: tuple[str, ...] = (
    "instantiates", "checks", "updates", "delegates to", "implements",
    "specializes", "contains", "dispatches to", "matches",
)


def concept_by_key(key: str) -> ConceptSpec:
    for concept in CONCEPTS:
        if concept.key == key:
            return concept
    raise KeyError(key)


def group_by_key(key: str) -> GroupSpec:
    for group in GROUPS:
        if group.key == key:
            return group
    raise KeyError(key)


@dataclass(frozen=True)
class CatalogReport:
    problems: tuple[str, ...] = field(default_factory=tuple)

    @property
    def ok(self) -> bool:
        return not self.problems


def validate_catalog() -> CatalogReport:
    """Cross-check groups, concepts and case studies for consistency."""
    problems: list[str] = []
    concept_keys = {c.key for c in CONCEPTS}
    group_keys = {g.key for g in GROUPS}
    grouped: list[str] = []
    for group in GROUPS:
        for key in group.concept_keys:
            if key not in concept_keys:
                problems.append(f"group {group.key} lists unknown concept {key}")
            grouped.append(key)
    if sorted(grouped) != sorted(concept_keys):
        problems.append("every concept must belong to exactly one group")
    for concept in CONCEPTS:
        if concept.group_key not in group_keys:
            problems.append(f"concept {concept.key} has unknown group")
        elif concept.key not in group_by_key(concept.group_key).concept_keys:
            problems.append(f"concept {concept.key} missing from its group")
    for case in CASE_STUDIES:
        for key in case.related_concepts:
            if key not in concept_keys:
                problems.append(f"case {case.key} references unknown {key}")
    return CatalogReport(tuple(problems))
