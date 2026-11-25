"""Scientific models used by the interactive OOP workbench."""

from __future__ import annotations

import math
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Literal

FailureCategory = Literal[
    "DOMAIN VALIDATION FAILURE",
    "SOFTWARE DESIGN FAILURE",
    "TYPE/CONTRACT FAILURE",
    "NUMERICAL/MODEL LIMITATION",
]


@dataclass(frozen=True)
class ChemicalSpecies:
    name: str
    formula: str
    molar_mass_g_mol: float
    charge: int = 0

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not isinstance(self.formula, str):
            raise ValueError("species name and formula must be text")
        if not self.name.strip() or not self.formula.strip():
            raise ValueError("species name and formula must not be empty")
        if not math.isfinite(self.molar_mass_g_mol) or self.molar_mass_g_mol <= 0:
            raise ValueError("molar_mass_g_mol must be finite and > 0")
        if isinstance(self.charge, bool) or not isinstance(self.charge, int):
            raise ValueError("charge must be an integer")


@dataclass(frozen=True)
class ScientificVariable:
    symbol: str
    name: str
    unit: str
    meaning: str


@dataclass(frozen=True)
class ModelMapping:
    scientific_term: str
    software_term: str


@dataclass(frozen=True)
class LanguageExample:
    language: Literal["Python", "Java", "TypeScript"]
    code: str


@dataclass(frozen=True)
class FailureCase:
    category: FailureCategory
    action: str
    expected: str


@dataclass(frozen=True)
class ScientificConceptSpec:
    id: str
    oop_concept: str
    group: str
    scientific_domain: str
    scientific_system: str
    learning_objective: str
    oop_question: str
    scientific_question: str
    computational_question: str
    governing_equations: tuple[str, ...]
    assumptions: tuple[str, ...]
    variables: tuple[ScientificVariable, ...]
    model_mappings: tuple[ModelMapping, ...]
    class_diagram: tuple[str, ...]
    execution_trace: tuple[str, ...]
    code_examples: tuple[LanguageExample, ...]
    failure_cases: tuple[FailureCase, ...]
    misconceptions: tuple[str, ...]


SODIUM_CHLORIDE = ChemicalSpecies(
    name="Sodium chloride",
    formula="NaCl",
    molar_mass_g_mol=58.44,
)


SOLUTION_ENCAPSULATION = ScientificConceptSpec(
    id="solution-encapsulation",
    oop_concept="Encapsulation",
    group="Object Lifecycle & State",
    scientific_domain="Chemistry / physical chemistry",
    scientific_system="A homogeneous aqueous sodium chloride solution",
    learning_objective=(
        "Protect solution state by exposing concentration-changing operations "
        "whose calculations follow a stated material-balance model."
    ),
    oop_question=(
        "How can callers change solution state through meaningful operations "
        "without writing concentration or amount directly?"
    ),
    scientific_question=(
        "How do solute amount, solution volume, and molar concentration relate "
        "during dilution, solute addition, and homogeneous aliquot removal?"
    ),
    computational_question=(
        "Given concentration, volume, temperature, and one operation, what "
        "state and concentration result, and which object method executes?"
    ),
    governing_equations=(
        "C = n / V",
        "C1 V1 = C2 V2  (dilution)",
        "n_after = n_before + delta_n  (solute addition)",
        "n_removed = C * V_removed  (homogeneous aliquot)",
    ),
    assumptions=(
        "The solution is homogeneous, so a removed aliquot has the bulk concentration.",
        "Dilution specifies final solution volume; solute amount is conserved.",
        "Added solute does not change volume; operations are isothermal.",
        "No reaction, precipitation, ion pairing, or activity-coefficient correction is modeled.",
        "Default numerical conditions are pedagogical, not experimental measurements.",
    ),
    variables=(
        ScientificVariable("C", "molar concentration", "mol/L", "solute amount per solution volume"),
        ScientificVariable("n", "solute amount", "mol", "amount of dissolved solute"),
        ScientificVariable("V", "solution volume", "L", "total homogeneous solution volume"),
        ScientificVariable("T", "temperature", "K", "absolute temperature"),
    ),
    model_mappings=(
        ModelMapping("chemical species", "ChemicalSpecies value object"),
        ModelMapping("solution", "Solution instance"),
        ModelMapping("solute amount, n", "private _solute_amount_mol state"),
        ModelMapping("solution volume, V", "private _volume_l state"),
        ModelMapping("concentration, C = n / V", "read-only concentration_mol_l property"),
        ModelMapping("dilution to a final volume", "solution.dilute(final_volume_l)"),
        ModelMapping("add a known solute amount", "solution.add_solute(amount_mol)"),
        ModelMapping("remove a homogeneous aliquot", "solution.remove_volume(volume_l)"),
        ModelMapping("model-valid state constraints", "constructor and operation validation"),
    ),
    class_diagram=(
        "ChemicalSpecies: name, formula, molar_mass_g_mol, charge",
        "Solution: solute, _solute_amount_mol, _volume_l, _temperature_k",
        "Solution: concentration_mol_l, dilute(), add_solute(), remove_volume()",
        "Solution contains one ChemicalSpecies",
    ),
    execution_trace=(
        "Caller selects an operation and supplies a value with units.",
        "Solution method receives the request.",
        "The method validates domain bounds before changing state.",
        "The method applies the stated material-balance relationship.",
        "Private amount/volume state changes only after validation succeeds.",
        "Concentration is derived from n / V and the resulting state is displayed.",
    ),
    code_examples=(
        LanguageExample(
            "Python",
            "from math import isfinite\n\n"
            "class Solution:\n"
            "    def __init__(self, solute, concentration_mol_l, volume_l, temperature_k):\n"
            "        if not all(isfinite(x) for x in (concentration_mol_l, volume_l, temperature_k)):\n"
            "            raise ValueError('state values must be finite')\n"
            "        if concentration_mol_l < 0 or volume_l <= 0 or temperature_k <= 0:\n"
            "            raise ValueError('C >= 0; V > 0 L; T > 0 K')\n"
            "        self._solute = solute\n"
            "        self._solute_amount_mol = concentration_mol_l * volume_l\n"
            "        self._volume_l = volume_l\n"
            "        self._temperature_k = temperature_k\n"
            "    @property\n"
            "    def concentration_mol_l(self):\n"
            "        return self._solute_amount_mol / self._volume_l\n\n"
            "    def dilute(self, final_volume_l):\n"
            "        if not isfinite(final_volume_l) or final_volume_l <= self._volume_l:\n"
            "            raise ValueError('final volume must exceed current volume')\n"
            "        self._volume_l = final_volume_l",
        ),
        LanguageExample(
            "Java",
            "final class Solution {\n"
            "  private final ChemicalSpecies solute;\n"
            "  private double soluteAmountMol;\n"
            "  private double volumeL;\n"
            "  private final double temperatureK;\n\n"
            "  Solution(ChemicalSpecies solute, double cMolL, double volumeL, double tK) {\n"
            "    if (!Double.isFinite(cMolL) || !Double.isFinite(volumeL) || !Double.isFinite(tK)\n"
            "        || cMolL < 0 || volumeL <= 0 || tK <= 0) throw new IllegalArgumentException();\n"
            "    this.solute = solute;\n"
            "    this.soluteAmountMol = cMolL * volumeL;\n"
            "    this.volumeL = volumeL;\n"
            "    this.temperatureK = tK;\n"
            "  }\n\n"
            "  double concentrationMolL() { return soluteAmountMol / volumeL; }\n"
            "  void dilute(double finalVolumeL) {\n"
            "    if (!Double.isFinite(finalVolumeL) || finalVolumeL <= volumeL)\n"
            "      throw new IllegalArgumentException();\n"
            "    volumeL = finalVolumeL;\n"
            "  }\n"
            "}",
        ),
        LanguageExample(
            "TypeScript",
            "class Solution {\n"
            "  private readonly solute: ChemicalSpecies;\n"
            "  private soluteAmountMol: number;\n"
            "  private volumeL: number;\n"
            "  private readonly temperatureK: number;\n"
            "  constructor(solute: ChemicalSpecies, cMolL: number, volumeL: number, temperatureK: number) {\n"
            "    if (![cMolL, volumeL, temperatureK].every(Number.isFinite)\n"
            "        || cMolL < 0 || volumeL <= 0 || temperatureK <= 0) throw new RangeError();\n"
            "    this.solute = solute;\n"
            "    this.soluteAmountMol = cMolL * volumeL;\n"
            "    this.volumeL = volumeL;\n"
            "    this.temperatureK = temperatureK;\n"
            "  }\n\n"
            "  get concentrationMolL(): number {\n"
            "    return this.soluteAmountMol / this.volumeL;\n"
            "  }\n"
            "  dilute(finalVolumeL: number): void {\n"
            "    if (!Number.isFinite(finalVolumeL) || finalVolumeL <= this.volumeL) throw new RangeError();\n"
            "    this.volumeL = finalVolumeL;\n"
            "  }\n"
            "}",
        ),
    ),
    failure_cases=(
        FailureCase(
            "DOMAIN VALIDATION FAILURE",
            "Construct with negative concentration, non-positive volume, or temperature <= 0 K.",
            "Reject the model state; do not create or mutate a Solution.",
        ),
        FailureCase(
            "DOMAIN VALIDATION FAILURE",
            "Dilute to a volume no greater than the current volume, or remove >= the current volume.",
            "Reject before mutation; the prior amount and volume remain unchanged.",
        ),
        FailureCase(
            "SOFTWARE DESIGN FAILURE",
            "Expose a public setter that allows callers to assign concentration independently of amount and volume.",
            "This permits contradictory model state and bypasses the operations that preserve the invariant.",
        ),
        FailureCase(
            "TYPE/CONTRACT FAILURE",
            "Assign concentration through the read-only public property.",
            "Reject the write; callers must use operations in the Solution contract.",
        ),
        FailureCase(
            "NUMERICAL/MODEL LIMITATION",
            "Use finite inputs whose product or resulting concentration exceeds floating-point range.",
            "Report the numerical limitation and leave object state unchanged.",
        ),
    ),
    misconceptions=(
        "A software invariant is a restriction of this program's model, not a law enforced by nature.",
        "A concentration property is derived state; independent public writes to C, n, and V can contradict C = n / V.",
        "The modeled solution is an approximation of a physical system, not the physical solution itself.",
    ),
)


DETECTOR_INTERFACE = ScientificConceptSpec(
    id="analytical-detector-interface",
    oop_concept="Abstraction and Interface",
    group="Contracts & Abstraction",
    scientific_domain="Analytical chemistry / instrumentation",
    scientific_system="Calibrated response of an absorbance, fluorescence, or electrochemical detector",
    learning_objective="Keep an analysis pipeline independent of concrete detector response models.",
    oop_question="How can one pipeline use different measurement implementations through one Detector contract?",
    scientific_question="How does analyte concentration map to instrument signal under each stated calibration model?",
    computational_question="Which implementation executes, what equation does it use, and what Measurement does it return?",
    governing_equations=(
        "A = epsilon * b * c  (Beer-Lambert)",
        "F = S_F * c  (linear fluorescence calibration)",
        "I = S_I * c + I_0  (linear electrochemical calibration)",
    ),
    assumptions=(
        "Calibration constants are synthetic teaching values, not reported measurements.",
        "Absorbance follows Beer-Lambert within a linear, non-scattering regime.",
        "Fluorescence response is treated as linear; quenching and inner-filter effects are excluded.",
        "The electrochemical response is a simplified calibrated linear range.",
    ),
    variables=(
        ScientificVariable("c", "analyte concentration", "mol/L", "sample concentration"),
        ScientificVariable("epsilon", "molar attenuation coefficient", "L/(mol cm)", "absorbance calibration coefficient"),
        ScientificVariable("b", "optical path length", "cm", "sample-cell path"),
        ScientificVariable("A", "absorbance", "dimensionless", "detector response"),
        ScientificVariable("F, I", "fluorescence / current", "RFU / microA", "calibrated detector output"),
    ),
    model_mappings=(
        ModelMapping("sample", "AnalyticalSample"),
        ModelMapping("measurement contract", "Detector.measure(sample) -> Measurement"),
        ModelMapping("instrument response", "concrete Detector implementation"),
        ModelMapping("analysis operation", "AnalysisPipeline.analyze(sample)"),
    ),
    class_diagram=(
        "AnalysisPipeline depends on Detector",
        "Detector.measure(AnalyticalSample) -> Measurement",
        "AbsorbanceDetector, FluorescenceDetector, ElectrochemicalSensor implement Detector",
    ),
    execution_trace=(
        "Caller supplies sample concentration and selects a detector implementation.",
        "AnalysisPipeline.analyze(sample) delegates through Detector.measure(sample).",
        "Runtime detector applies its calibration equation and returns Measurement.",
    ),
    code_examples=(
        LanguageExample(
            "Python",
            "class Detector(ABC):\n"
            "    @abstractmethod\n"
            "    def measure(self, sample: AnalyticalSample) -> Measurement: ...\n\n"
            "class AnalysisPipeline:\n"
            "    def __init__(self, detector: Detector): self._detector = detector\n"
            "    def analyze(self, sample): return self._detector.measure(sample)",
        ),
        LanguageExample(
            "Java",
            "interface Detector {\n"
            "  Measurement measure(AnalyticalSample sample);\n"
            "}\n"
            "final class AnalysisPipeline {\n"
            "  private final Detector detector;\n"
            "  Measurement analyze(AnalyticalSample s) { return detector.measure(s); }\n"
            "}",
        ),
        LanguageExample(
            "TypeScript",
            "interface Detector { measure(sample: AnalyticalSample): Measurement }\n"
            "class AnalysisPipeline {\n"
            "  constructor(private readonly detector: Detector) {}\n"
            "  analyze(sample: AnalyticalSample): Measurement {\n"
            "    return this.detector.measure(sample);\n"
            "  }\n"
            "}",
        ),
    ),
    failure_cases=(
        FailureCase("TYPE/CONTRACT FAILURE", "Inject an object without measure(sample).", "Reject the dependency before analysis."),
        FailureCase("NUMERICAL/MODEL LIMITATION", "Use a fluorescence calibration outside its linear regime.", "Report that the simplified calibration no longer applies."),
    ),
    misconceptions=(
        "An interface is a behavioral contract, not just a common method name.",
        "The pipeline stays unchanged because the abstraction boundary is useful, not because instruments are interchangeable in every scientific context.",
    ),
)


ENZYME_INHERITANCE = ScientificConceptSpec(
    id="enzyme-substitutability",
    oop_concept="Inheritance and Liskov Substitution",
    group="Code Reuse & Structure",
    scientific_domain="Biochemistry",
    scientific_system="Simplified steady-state enzyme rate models",
    learning_objective="Distinguish behavioral substitutability from biological classification.",
    oop_question="Does every enzyme-rate subtype honor the base rate contract?",
    scientific_question="How do substrate concentration and competitive inhibition affect a simplified enzyme rate?",
    computational_question="What rate does the selected runtime subtype return, and does it satisfy the shared contract?",
    governing_equations=(
        "v = Vmax * [S] / (Km + [S])",
        "v = Vmax * [S] / (Km * (1 + [I]/Ki) + [S])  (competitive inhibition)",
    ),
    assumptions=(
        "These are simplified steady-state Michaelis-Menten models, not universal enzyme laws.",
        "Vmax, Km, Ki, and inhibitor concentrations are synthetic teaching values.",
        "The competitive inhibitor model assumes reversible competitive inhibition and fixed inhibitor concentration.",
    ),
    variables=(
        ScientificVariable("[S]", "substrate concentration", "mol/L", "reaction substrate concentration"),
        ScientificVariable("v", "initial rate", "micromol/(L s)", "positive rate of substrate conversion"),
        ScientificVariable("Vmax", "maximum rate", "micromol/(L s)", "model saturation rate"),
        ScientificVariable("Km, Ki, [I]", "model parameters", "mol/L", "Michaelis constant, inhibition constant, inhibitor concentration"),
    ),
    model_mappings=(
        ModelMapping("enzyme rate model", "EnzymeRateModel base contract"),
        ModelMapping("substrate-dependent rate law", "overridden rate(substrate_mol_l)"),
        ModelMapping("biological mechanism variant", "behaviorally substitutable implementation"),
        ModelMapping("assay contract", "rate is finite, non-negative, <= Vmax, and zero at [S] = 0"),
    ),
    class_diagram=(
        "EnzymeRateModel.rate(substrate_mol_l) -> micromol/(L s)",
        "MichaelisMentenEnzyme specializes EnzymeRateModel",
        "CompetitiveInhibitionEnzyme specializes EnzymeRateModel",
    ),
    execution_trace=(
        "Caller supplies substrate concentration and chooses an enzyme-rate object.",
        "Assay invokes the shared rate(substrate_mol_l) contract.",
        "Runtime subtype evaluates its kinetic equation.",
        "Substitutability checks rate bounds, zero-substrate behavior, and monotonicity.",
    ),
    code_examples=(
        LanguageExample("Python", "class EnzymeRateModel(ABC):\n    @abstractmethod\n    def rate(self, substrate_mol_l: float) -> float: ...\n\nrate = enzyme.rate(substrate_mol_l)"),
        LanguageExample("Java", "abstract class EnzymeRateModel {\n  abstract double rate(double substrateMolL);\n}\nfinal class CompetitiveInhibitionEnzyme extends EnzymeRateModel {\n  @Override double rate(double substrateMolL) { /* kinetic equation */ }\n}"),
        LanguageExample("TypeScript", "interface EnzymeRateModel { rate(substrateMolL: number): number }\nconst rate = enzyme.rate(substrateMolL); // runtime receiver chooses implementation"),
    ),
    failure_cases=(
        FailureCase("TYPE/CONTRACT FAILURE", "Use a subtype that returns a negative rate.", "The substitutability check identifies the broken base contract."),
        FailureCase("NUMERICAL/MODEL LIMITATION", "Apply Michaelis-Menten outside its steady-state assumptions.", "Treat the result as a model limitation, not an OOP contract failure."),
    ),
    misconceptions=(
        "Enzymes being related biologically does not by itself justify an inheritance hierarchy.",
        "A subtype passes only when clients relying on the base behavioral contract still work.",
    ),
)


REACTOR_COMPOSITION = ScientificConceptSpec(
    id="reactor-composition",
    oop_concept="Composition",
    group="Code Reuse & Structure",
    scientific_domain="Chemical engineering",
    scientific_system="Steady-state first-order ideal CSTR and plug-flow reactor models",
    learning_objective="Assemble reactor behavior from kinetic and mixing collaborators.",
    oop_question="Can the reactor host remain unchanged while kinetic and mixing components are swapped?",
    scientific_question="How do first-order kinetics and residence time determine outlet concentration under different ideal mixing models?",
    computational_question="Given feed concentration, temperature, residence time, and components, what outlet concentration results?",
    governing_equations=(
        "k(T) = A * exp(-Ea / (R*T))",
        "Cout = Cin / (1 + k*tau)  (ideal steady-state CSTR)",
        "Cout = Cin * exp(-k*tau)  (ideal plug-flow reactor)",
    ),
    assumptions=(
        "Steady state, irreversible first-order reaction, constant density, and constant temperature.",
        "CSTR is ideally mixed; plug flow has no axial mixing.",
        "No transport limitation, volume change, or energy balance is modeled.",
        "Kinetic inputs are synthetic teaching values.",
    ),
    variables=(
        ScientificVariable("Cin, Cout", "inlet / outlet concentration", "mol/L", "reactant concentration"),
        ScientificVariable("k", "first-order rate constant", "s^-1", "kinetic component output"),
        ScientificVariable("tau", "residence time", "s", "reactor volume divided by volumetric flow"),
        ScientificVariable("T, Ea, A", "temperature and Arrhenius parameters", "K, J/mol, s^-1", "temperature-dependent rate constant inputs"),
    ),
    model_mappings=(
        ModelMapping("reactor", "Reactor host object"),
        ModelMapping("kinetic law", "injected FirstOrderKinetics implementation"),
        ModelMapping("mixing regime", "injected CSTRMixing or PlugFlowMixing implementation"),
        ModelMapping("assembled process", "Reactor(kinetics, mixing) composition"),
    ),
    class_diagram=(
        "Reactor contains KineticRateConstant and MixingModel",
        "ConstantFirstOrderKinetics / ArrheniusFirstOrderKinetics implement kinetic contract",
        "CSTRMixing / PlugFlowMixing implement mixing contract",
    ),
    execution_trace=(
        "Caller configures a Reactor with kinetic and mixing components.",
        "Reactor computes k(T) through the kinetic component.",
        "Reactor delegates the balance to the selected mixing component.",
        "The same host returns an outlet concentration and conversion.",
    ),
    code_examples=(
        LanguageExample("Python", "reactor = Reactor(ArrheniusFirstOrderKinetics(A, Ea), CSTRMixing())\nresult = reactor.outlet(Cin, residence_time_s, temperature_k)"),
        LanguageExample("Java", "final class Reactor {\n  private final KineticRateConstant kinetics;\n  private final MixingModel mixing;\n  Reactor(KineticRateConstant k, MixingModel m) { this.kinetics = k; this.mixing = m; }\n}"),
        LanguageExample("TypeScript", "class Reactor {\n  constructor(private kinetics: KineticRateConstant, private mixing: MixingModel) {}\n  outlet(state: ReactorState): ReactorResult { /* delegate to components */ }\n}"),
    ),
    failure_cases=(
        FailureCase("TYPE/CONTRACT FAILURE", "Inject a mixing component without outlet(...).", "The host cannot execute its required collaborator contract."),
        FailureCase("NUMERICAL/MODEL LIMITATION", "Interpret ideal-reactor output as a real plant prediction without validated kinetics or transport data.", "The simplified model is not a validated process design."),
    ),
    misconceptions=(
        "Composition is useful because kinetics and mixing vary independently, not merely because parts can be named.",
        "Component-count comparisons describe implementation structures, not runtime object counts.",
    ),
)


KINETIC_POLYMORPHISM = ScientificConceptSpec(
    id="reaction-rate-dispatch",
    oop_concept="Runtime polymorphism",
    group="Polymorphic Dispatch",
    scientific_domain="Chemical kinetics / biochemistry",
    scientific_system="Zero-, first-, second-order, and Michaelis-Menten rate laws",
    learning_objective="Trace runtime method dispatch to the selected kinetic rate implementation.",
    oop_question="Which rate implementation executes when a caller invokes model.rate(state)?",
    scientific_question="How does substrate concentration change the rate under different kinetic laws?",
    computational_question="What rate and governing equation does the selected runtime model return?",
    governing_equations=(
        "r = k0",
        "r = k1 * [A]",
        "r = k2 * [A]^2",
        "v = Vmax * [S] / (Km + [S])",
    ),
    assumptions=(
        "Rate parameters and concentrations are synthetic teaching inputs.",
        "The rate laws are simplified and apply only under their stated kinetic assumptions.",
        "A positive rate denotes disappearance/consumption rate; d[A]/dt = -r for a consumed reactant.",
    ),
    variables=(
        ScientificVariable("[A], [S]", "reactant / substrate concentration", "mol/L", "state passed to rate(state)"),
        ScientificVariable("r, v", "reaction rate", "mol/(L s)", "positive consumption rate"),
        ScientificVariable("k0, k1, k2", "order-specific rate constants", "mol/(L s), s^-1, L/(mol s)", "selected model parameters"),
        ScientificVariable("Vmax, Km", "Michaelis-Menten parameters", "mol/(L s), mol/L", "saturation rate and substrate scale"),
    ),
    model_mappings=(
        ModelMapping("reaction-state values", "ReactionState"),
        ModelMapping("kinetic law family", "ReactionRateModel implementation"),
        ModelMapping("rate operation", "model.rate(state)"),
        ModelMapping("selected kinetic equation", "runtime override and returned rate"),
    ),
    class_diagram=(
        "ReactionRateModel.rate(ReactionState) -> mol/(L s)",
        "ZeroOrderKinetics / FirstOrderKinetics / SecondOrderKinetics / MichaelisMentenKinetics implement contract",
    ),
    execution_trace=(
        "Caller selects a ReactionRateModel object and substrate state.",
        "Caller invokes model.rate(state) through the shared contract.",
        "Runtime object selects its overriding rate implementation.",
        "Selected equation returns rate with units.",
    ),
    code_examples=(
        LanguageExample("Python", "rate_model: ReactionRateModel = FirstOrderKinetics(k1_s)\nrate = rate_model.rate(ReactionState(substrate_mol_l))"),
        LanguageExample("Java", "ReactionRateModel model = new FirstOrderKinetics(k1);\ndouble rate = model.rate(state); // runtime override"),
        LanguageExample("TypeScript", "const model: ReactionRateModel = new FirstOrderKinetics(k1);\nconst rate = model.rate(state); // runtime dispatch"),
    ),
    failure_cases=(
        FailureCase("TYPE/CONTRACT FAILURE", "Provide a rate model returning a negative or non-finite rate.", "Reject the implementation against the common rate contract."),
        FailureCase("NUMERICAL/MODEL LIMITATION", "Use a rate law outside its concentration, temperature, or mechanism assumptions.", "Report a limitation of the simplified kinetic model."),
    ),
    misconceptions=(
        "Overriding is runtime dispatch; overloading is a distinct compile-time/signature feature in Java and signature-only in TypeScript.",
        "Python has no native signature-based method overloading; use explicit dispatch or separate methods.",
    ),
)


class DomainValidationError(ValueError):
    """Raised when an operation would create a state outside the model domain."""


class NumericalModelError(ArithmeticError):
    """Raised when finite inputs produce a value outside floating-point range."""


class RateContractError(TypeError):
    """Raised when a rate implementation violates its non-negative contract."""


class Solution:
    """A mutable, homogeneous solution with amount and volume as its state.

    This simplified model treats dilution and solute addition as isothermal,
    assumes additive volume for added solute, and excludes chemical reactions.
    """

    __slots__ = ("_solute", "_solute_amount_mol", "_volume_l", "_temperature_k")

    def __init__(
        self,
        solute: ChemicalSpecies,
        concentration_mol_l: float,
        volume_l: float,
        temperature_k: float,
    ) -> None:
        if not isinstance(solute, ChemicalSpecies):
            raise DomainValidationError("solute must be a ChemicalSpecies")
        self._require_finite(concentration_mol_l, "concentration_mol_l")
        self._require_finite(volume_l, "volume_l")
        self._require_finite(temperature_k, "temperature_k")
        if concentration_mol_l < 0:
            raise DomainValidationError("concentration_mol_l must be >= 0")
        if volume_l <= 0:
            raise DomainValidationError("volume_l must be > 0")
        if temperature_k <= 0:
            raise DomainValidationError("temperature_k must be > 0 K")
        amount_mol = concentration_mol_l * volume_l
        if not math.isfinite(amount_mol):
            raise NumericalModelError("concentration_mol_l * volume_l exceeds floating-point range")
        self._solute = solute
        self._solute_amount_mol = amount_mol
        self._volume_l = volume_l
        self._temperature_k = temperature_k

    @staticmethod
    def _require_finite(value: float, name: str) -> None:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise DomainValidationError(f"{name} must be a finite number")
        if not math.isfinite(value):
            raise DomainValidationError(f"{name} must be a finite number")

    @property
    def solute(self) -> ChemicalSpecies:
        return self._solute

    @property
    def solute_amount_mol(self) -> float:
        return self._solute_amount_mol

    @property
    def volume_l(self) -> float:
        return self._volume_l

    @property
    def temperature_k(self) -> float:
        return self._temperature_k

    @property
    def concentration_mol_l(self) -> float:
        return self._solute_amount_mol / self._volume_l

    def dilute(self, final_volume_l: float) -> None:
        self._require_finite(final_volume_l, "final_volume_l")
        if final_volume_l <= self._volume_l:
            raise DomainValidationError("final_volume_l must exceed current volume_l")
        self._volume_l = final_volume_l

    def add_solute(self, amount_mol: float) -> None:
        self._require_finite(amount_mol, "amount_mol")
        if amount_mol <= 0:
            raise DomainValidationError("amount_mol must be > 0")
        next_amount = self._solute_amount_mol + amount_mol
        if not math.isfinite(next_amount) or not math.isfinite(next_amount / self._volume_l):
            raise NumericalModelError("resulting amount or concentration exceeds floating-point range")
        self._solute_amount_mol = next_amount

    def remove_volume(self, volume_l: float) -> None:
        self._require_finite(volume_l, "volume_l")
        if volume_l <= 0 or volume_l >= self._volume_l:
            raise DomainValidationError("removed volume_l must be > 0 and < current volume_l")
        removed_amount = self.concentration_mol_l * volume_l
        next_amount = self._solute_amount_mol - removed_amount
        next_volume = self._volume_l - volume_l
        if not math.isfinite(next_amount) or not math.isfinite(next_volume):
            raise NumericalModelError("aliquot calculation exceeds floating-point range")
        self._solute_amount_mol = max(0.0, next_amount)
        self._volume_l = next_volume

    def snapshot(self) -> tuple[float, float, float, float]:
        """Return amount (mol), volume (L), concentration (mol/L), and T (K)."""
        return (
            self._solute_amount_mol,
            self._volume_l,
            self.concentration_mol_l,
            self._temperature_k,
        )


def _finite(value: float, name: str) -> None:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise DomainValidationError(f"{name} must be a finite number")


def _nonnegative(value: float, name: str) -> None:
    _finite(value, name)
    if value < 0:
        raise DomainValidationError(f"{name} must be >= 0")


def _positive(value: float, name: str) -> None:
    _finite(value, name)
    if value <= 0:
        raise DomainValidationError(f"{name} must be > 0")


@dataclass(frozen=True)
class AnalyticalSample:
    analyte: ChemicalSpecies
    concentration_mol_l: float

    def __post_init__(self) -> None:
        if not isinstance(self.analyte, ChemicalSpecies):
            raise DomainValidationError("analyte must be a ChemicalSpecies")
        _nonnegative(self.concentration_mol_l, "concentration_mol_l")


@dataclass(frozen=True)
class Measurement:
    value: float
    units: str
    detector_name: str
    equation: str

    def __post_init__(self) -> None:
        _finite(self.value, "measurement value")
        if not self.units or not self.detector_name or not self.equation:
            raise DomainValidationError("measurement units, detector name, and equation are required")


class Detector(ABC):
    """Measurement contract used by AnalysisPipeline."""

    @abstractmethod
    def measure(self, sample: AnalyticalSample) -> Measurement: ...


@dataclass(frozen=True)
class AbsorbanceDetector(Detector):
    epsilon_l_mol_cm: float
    path_length_cm: float

    def __post_init__(self) -> None:
        _positive(self.epsilon_l_mol_cm, "epsilon_l_mol_cm")
        _positive(self.path_length_cm, "path_length_cm")

    def measure(self, sample: AnalyticalSample) -> Measurement:
        if not isinstance(sample, AnalyticalSample):
            raise TypeError("sample must be an AnalyticalSample")
        absorbance = self.epsilon_l_mol_cm * self.path_length_cm * sample.concentration_mol_l
        if not math.isfinite(absorbance):
            raise NumericalModelError("Beer-Lambert calculation exceeds floating-point range")
        return Measurement(
            absorbance,
            "dimensionless absorbance",
            type(self).__name__,
            "A = epsilon * b * c",
        )


@dataclass(frozen=True)
class FluorescenceDetector(Detector):
    sensitivity_rfu_l_mol: float

    def __post_init__(self) -> None:
        _positive(self.sensitivity_rfu_l_mol, "sensitivity_rfu_l_mol")

    def measure(self, sample: AnalyticalSample) -> Measurement:
        if not isinstance(sample, AnalyticalSample):
            raise TypeError("sample must be an AnalyticalSample")
        signal = self.sensitivity_rfu_l_mol * sample.concentration_mol_l
        if not math.isfinite(signal):
            raise NumericalModelError("fluorescence calculation exceeds floating-point range")
        return Measurement(signal, "RFU", type(self).__name__, "F = S_F * c")


@dataclass(frozen=True)
class ElectrochemicalSensor(Detector):
    slope_microamp_l_mol: float
    offset_microamp: float

    def __post_init__(self) -> None:
        _positive(self.slope_microamp_l_mol, "slope_microamp_l_mol")
        _finite(self.offset_microamp, "offset_microamp")

    def measure(self, sample: AnalyticalSample) -> Measurement:
        if not isinstance(sample, AnalyticalSample):
            raise TypeError("sample must be an AnalyticalSample")
        current = self.slope_microamp_l_mol * sample.concentration_mol_l + self.offset_microamp
        if not math.isfinite(current):
            raise NumericalModelError("electrochemical calibration exceeds floating-point range")
        return Measurement(current, "microA", type(self).__name__, "I = S_I * c + I_0")


class AnalysisPipeline:
    def __init__(self, detector: Detector) -> None:
        if not isinstance(detector, Detector):
            raise TypeError("detector must implement Detector")
        self._detector = detector

    @property
    def detector(self) -> Detector:
        return self._detector

    def analyze(self, sample: AnalyticalSample) -> Measurement:
        return self._detector.measure(sample)


class EnzymeRateModel(ABC):
    """Behavioral contract for steady-state enzyme rate implementations."""

    def __init__(self, vmax_umol_l_s: float, km_mol_l: float) -> None:
        _positive(vmax_umol_l_s, "vmax_umol_l_s")
        _positive(km_mol_l, "km_mol_l")
        self.vmax_umol_l_s = vmax_umol_l_s
        self.km_mol_l = km_mol_l

    @abstractmethod
    def rate(self, substrate_mol_l: float) -> float: ...


class MichaelisMentenEnzyme(EnzymeRateModel):
    def rate(self, substrate_mol_l: float) -> float:
        _nonnegative(substrate_mol_l, "substrate_mol_l")
        rate = self.vmax_umol_l_s * substrate_mol_l / (self.km_mol_l + substrate_mol_l)
        if not math.isfinite(rate):
            raise NumericalModelError("Michaelis-Menten rate exceeds floating-point range")
        return rate


class CompetitiveInhibitionEnzyme(EnzymeRateModel):
    def __init__(
        self,
        vmax_umol_l_s: float,
        km_mol_l: float,
        inhibitor_mol_l: float,
        ki_mol_l: float,
    ) -> None:
        super().__init__(vmax_umol_l_s, km_mol_l)
        _nonnegative(inhibitor_mol_l, "inhibitor_mol_l")
        _positive(ki_mol_l, "ki_mol_l")
        self.inhibitor_mol_l = inhibitor_mol_l
        self.ki_mol_l = ki_mol_l

    def rate(self, substrate_mol_l: float) -> float:
        _nonnegative(substrate_mol_l, "substrate_mol_l")
        apparent_km = self.km_mol_l * (1 + self.inhibitor_mol_l / self.ki_mol_l)
        rate = self.vmax_umol_l_s * substrate_mol_l / (apparent_km + substrate_mol_l)
        if not math.isfinite(rate):
            raise NumericalModelError("competitive-inhibition rate exceeds floating-point range")
        return rate


class ContractBreakingEnzyme(MichaelisMentenEnzyme):
    """Deliberately invalid subtype used only to test substitutability."""

    def rate(self, substrate_mol_l: float) -> float:
        return -super().rate(substrate_mol_l)


@dataclass(frozen=True)
class EnzymeContractCheck:
    holds: bool
    rates_umol_l_s: tuple[float, ...]
    failures: tuple[str, ...]


def check_enzyme_contract(
    enzyme: EnzymeRateModel,
    substrate_values_mol_l: tuple[float, ...] = (0.0, 0.01, 0.05, 0.2),
) -> EnzymeContractCheck:
    if not isinstance(enzyme, EnzymeRateModel):
        raise TypeError("enzyme must implement EnzymeRateModel")
    rates = tuple(enzyme.rate(substrate) for substrate in substrate_values_mol_l)
    failures: list[str] = []
    if not rates or substrate_values_mol_l[0] != 0 or rates[0] != 0:
        failures.append("rate(0 mol/L) must equal 0 microMol/(L s)")
    if any(not math.isfinite(rate) or rate < 0 or rate > enzyme.vmax_umol_l_s for rate in rates):
        failures.append("rate must be finite and within [0, Vmax]")
    if any(right < left for left, right in zip(rates, rates[1:])):
        failures.append("rate must not decrease as substrate increases")
    return EnzymeContractCheck(not failures, rates, tuple(failures))


GAS_CONSTANT_J_MOL_K = 8.31446261815324


class FirstOrderKinetics(ABC):
    @abstractmethod
    def rate_constant_s_inv(self, temperature_k: float) -> float: ...


@dataclass(frozen=True)
class ConstantFirstOrderKinetics(FirstOrderKinetics):
    k_s_inv: float

    def __post_init__(self) -> None:
        _positive(self.k_s_inv, "k_s_inv")

    def rate_constant_s_inv(self, temperature_k: float) -> float:
        _positive(temperature_k, "temperature_k")
        return self.k_s_inv


@dataclass(frozen=True)
class ArrheniusFirstOrderKinetics(FirstOrderKinetics):
    pre_exponential_s_inv: float
    activation_energy_j_mol: float

    def __post_init__(self) -> None:
        _positive(self.pre_exponential_s_inv, "pre_exponential_s_inv")
        _nonnegative(self.activation_energy_j_mol, "activation_energy_j_mol")

    def rate_constant_s_inv(self, temperature_k: float) -> float:
        _positive(temperature_k, "temperature_k")
        exponent = -self.activation_energy_j_mol / (GAS_CONSTANT_J_MOL_K * temperature_k)
        result = self.pre_exponential_s_inv * math.exp(exponent)
        if not math.isfinite(result):
            raise NumericalModelError("Arrhenius calculation exceeds floating-point range")
        return result


class MixingModel(ABC):
    @abstractmethod
    def outlet_concentration_mol_l(
        self, inlet_mol_l: float, k_s_inv: float, residence_time_s: float
    ) -> float: ...

    @property
    @abstractmethod
    def equation(self) -> str: ...


@dataclass(frozen=True)
class CSTRMixing(MixingModel):
    def outlet_concentration_mol_l(
        self, inlet_mol_l: float, k_s_inv: float, residence_time_s: float
    ) -> float:
        return inlet_mol_l / (1 + k_s_inv * residence_time_s)

    @property
    def equation(self) -> str:
        return "Cout = Cin / (1 + k*tau)"


@dataclass(frozen=True)
class PlugFlowMixing(MixingModel):
    def outlet_concentration_mol_l(
        self, inlet_mol_l: float, k_s_inv: float, residence_time_s: float
    ) -> float:
        return inlet_mol_l * math.exp(-k_s_inv * residence_time_s)

    @property
    def equation(self) -> str:
        return "Cout = Cin * exp(-k*tau)"


@dataclass(frozen=True)
class ReactorResult:
    inlet_mol_l: float
    outlet_mol_l: float
    rate_constant_s_inv: float
    residence_time_s: float
    temperature_k: float
    conversion_fraction: float
    kinetic_model: str
    mixing_model: str
    equation: str


class Reactor:
    """Reactor host assembled from kinetic and mixing collaborators."""

    def __init__(self, kinetics: FirstOrderKinetics, mixing: MixingModel) -> None:
        if not isinstance(kinetics, FirstOrderKinetics):
            raise TypeError("kinetics must implement FirstOrderKinetics")
        if not isinstance(mixing, MixingModel):
            raise TypeError("mixing must implement MixingModel")
        self.kinetics = kinetics
        self.mixing = mixing

    def outlet(
        self, inlet_mol_l: float, residence_time_s: float, temperature_k: float
    ) -> ReactorResult:
        _nonnegative(inlet_mol_l, "inlet_mol_l")
        _positive(residence_time_s, "residence_time_s")
        _positive(temperature_k, "temperature_k")
        k = self.kinetics.rate_constant_s_inv(temperature_k)
        concentration = self.mixing.outlet_concentration_mol_l(
            inlet_mol_l, k, residence_time_s
        )
        if not math.isfinite(concentration) or concentration < 0:
            raise NumericalModelError("reactor balance produced an invalid concentration")
        conversion = 0.0 if inlet_mol_l == 0 else 1 - concentration / inlet_mol_l
        return ReactorResult(
            inlet_mol_l,
            concentration,
            k,
            residence_time_s,
            temperature_k,
            conversion,
            type(self.kinetics).__name__,
            type(self.mixing).__name__,
            self.mixing.equation,
        )


@dataclass(frozen=True)
class ReactionState:
    substrate_mol_l: float

    def __post_init__(self) -> None:
        _nonnegative(self.substrate_mol_l, "substrate_mol_l")


class ReactionRateModel(ABC):
    @abstractmethod
    def rate(self, state: ReactionState) -> float: ...

    @property
    @abstractmethod
    def equation(self) -> str: ...


@dataclass(frozen=True)
class ZeroOrderKinetics(ReactionRateModel):
    k0_mol_l_s: float

    def __post_init__(self) -> None:
        _nonnegative(self.k0_mol_l_s, "k0_mol_l_s")

    def rate(self, state: ReactionState) -> float:
        return self.k0_mol_l_s

    @property
    def equation(self) -> str:
        return "r = k0"


@dataclass(frozen=True)
class FirstOrderReaction(ReactionRateModel):
    k1_s_inv: float

    def __post_init__(self) -> None:
        _nonnegative(self.k1_s_inv, "k1_s_inv")

    def rate(self, state: ReactionState) -> float:
        return self.k1_s_inv * state.substrate_mol_l

    @property
    def equation(self) -> str:
        return "r = k1 * [A]"


@dataclass(frozen=True)
class SecondOrderKinetics(ReactionRateModel):
    k2_l_mol_s: float

    def __post_init__(self) -> None:
        _nonnegative(self.k2_l_mol_s, "k2_l_mol_s")

    def rate(self, state: ReactionState) -> float:
        return self.k2_l_mol_s * state.substrate_mol_l**2

    @property
    def equation(self) -> str:
        return "r = k2 * [A]^2"


@dataclass(frozen=True)
class MichaelisMentenKinetics(ReactionRateModel):
    vmax_mol_l_s: float
    km_mol_l: float

    def __post_init__(self) -> None:
        _positive(self.vmax_mol_l_s, "vmax_mol_l_s")
        _positive(self.km_mol_l, "km_mol_l")

    def rate(self, state: ReactionState) -> float:
        return self.vmax_mol_l_s * state.substrate_mol_l / (
            self.km_mol_l + state.substrate_mol_l
        )

    @property
    def equation(self) -> str:
        return "v = Vmax * [S] / (Km + [S])"


def dispatch_reaction_rate(model: ReactionRateModel, state: ReactionState) -> float:
    if not isinstance(model, ReactionRateModel):
        raise TypeError("model must implement ReactionRateModel")
    rate = model.rate(state)
    if not math.isfinite(rate):
        raise NumericalModelError("rate model returned a non-finite rate")
    if rate < 0:
        raise RateContractError("rate model violated its non-negative rate contract")
    return rate


class ContractBreakingReactionRateModel(ReactionRateModel):
    """Deliberately invalid kinetic model used only to test the contract."""

    def rate(self, state: ReactionState) -> float:
        return -abs(state.substrate_mol_l)

    @property
    def equation(self) -> str:
        return "r = -[A]  (intentionally invalid)"
