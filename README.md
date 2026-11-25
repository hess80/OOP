# OOP Visual Study Guide & Architecture Workbench

A runnable study guide for object-oriented design. The PDF uses the deterministic Python model in `src/oop_guide/models.py`. The offline web app mirrors its core lessons and adds an interactive Materials Lab:

| Output | What it is | How to open |
| --- | --- | --- |
| `web/index.html` | Self-contained interactive workbench with concept cards, case studies, the **Break It / Invariant Lab**, the synthetic **Materials Lab**, and scientific OOP workbenches | Open the file directly in any modern browser (no server or network needed) |
| `dist/oop_visual_study_guide.pdf` | Deterministic multi-page PDF on warm graph paper, with vector diagrams and deterministic check tables | Open in any PDF viewer; rebuild with the command below |

---

## The four structure groups

Every concept belongs to exactly one group:

| # | Group | Concepts | Question it answers |
| --- | --- | --- | --- |
| 1 | **Object Lifecycle & State** | `Class`, `Object`, `Constructor` / initialization, `Encapsulation` | How state comes into existence and stays valid |
| 2 | **Contracts & Abstraction** | `Abstraction`, `Interface` | What a caller may rely on, separated from how it is done |
| 3 | **Code Reuse & Structure** | `Inheritance`, `Composition` | Specialization (is-a) versus assembly from parts (has-a) |
| 4 | **Polymorphic Dispatch** | `Polymorphism` | Which implementation runs: runtime type or call signature |

Framing used throughout the copy, diagrams and UI:

- **Objects** encapsulate state and behavior behind a defined interaction boundary. They maintain their invariants only because every state change goes through controlled operations. The language itself guarantees nothing about domain rules.
- **Constructors / initialization** establish initial state, bind required dependencies, and validate invariants before any other code can use the object. Languages differ here: Java/C# constructors, C++ member-initializer lists, Python `__init__` (after `__new__`), and Rust/Go factory functions.
- **Encapsulation** means access control in service of invariant protection. **Abstraction** means exposing essential capabilities while hiding implementation details. The guide keeps the two separate.
- **Inheritance** models specialization and *behavioral substitutability* (Liskov); code reuse is a side effect. **Composition** means "has-a": behavior is assembled from collaborating, swappable components.
- **Polymorphism** has two forms:
  - *Runtime subtype dispatch*: an overriding method is chosen by the receiver's runtime type.
  - *Overload resolution*: a method is chosen from the call's parameter signature and declared types, and never from the runtime object type. Python and JavaScript have no signature overloading.

### Key figures

- **Figure 4.1 – Dynamic dispatch:** `Shape` → `draw()` → `Circle`, `Square`, `Triangle` via `dispatches to` arrows. The figure deliberately shows no area or perimeter text.
- **Figure 4.2 – Overload resolution:** `translate(1.0, 2.0)` `matches` `translate(float x, float y)`, and `translate(1.0, 2.0, 3.0)` `matches` `translate(float x, float y, float z)`. The selection depends on the call signature, not the runtime object type.
- **Exact geometry** lives in the deterministic checks and the lab:
  - `Circle r=1.5 → area ≈ 7.0686`
  - `Square s=3 → area = 9, perimeter = 12`
  - `Triangle b=4, h=3.5 → area = 7`

### Production failure & behavioral case studies

1. **Liskov substitution:** `Rectangle` promises independent width/height mutation. `Square` keeps its `width == height` invariant, so a client gets area 16 instead of 20.
2. **Fragile base classes / deep hierarchies:** a one-line base edit ripples down several levels.
3. **Diamond inheritance conflicts:** ambiguous method resolution and shared-state initialization.
4. **Combinatorial subclass explosion vs. composition:** 3 × 2 × 2 = 12 subclasses versus 3 + 2 + 2 = 7 components.
5. **Anemic encapsulation:** getters/setters everywhere let callers write `fuel_kg = -50`.
6. **Concrete implementation coupling:** callers type against `ChemicalEngine` instead of the `Propulsion` interface.

---

## Diagram rules: two layers

Every diagram, in both the PDF and the web workbench, is drawn in two passes:

- **Layer 1 – visual/vector structure:** boxes, encapsulation boundaries, arrow shafts, arrowheads and label pills. Pure vector geometry, no raster images.
- **Layer 2 – deterministic text:** box titles in a sans-serif display face, method signatures in monospace, and explicit semantic arrow labels. Layer 2 is drawn on top of Layer 1, so text is never occluded.

Every arrow carries one of these labels:
`instantiates`, `checks`, `updates`, `delegates to`, `implements`, `specializes`, `contains`, `dispatches to`, `matches`.

### Typography & palette

- **Headings:** graphic sans-serif/display, uppercase and letter-spaced. Handwriting or script fonts are never used.
- **Code and signatures:** monospace.
- **Fonts in the PDF:** only the standard Helvetica and Courier families. All PDF text is ≥ 9 pt (enforced at render time and in tests).

| Role | Hex |
| --- | --- |
| Paper | `#F7F3E8` |
| Grid | `#E6DFC8` |
| Navy (structure) | `#162B4D` |
| Rust (traps, failures) | `#9E3B24` |
| Teal (contracts, fixes) | `#1C5D58` |

---

## Repository layout

```
.
├── README.md
├── pyproject.toml                 # Python 3.11+, reportlab, pytest (dev extra)
├── src/oop_guide/
│   ├── __init__.py                # package exports + __version__
│   ├── models.py                  # ConceptSpec, GroupSpec, CaseStudySpec, InvariantLabState + deterministic helpers
│   ├── science.py                 # typed scientific schemas and chemistry, detector, enzyme, reactor, and kinetics models
│   └── pdf_builder.py             # deterministic PDF generator
├── tests/test_models_and_pdf.py   # unit + integration tests
├── web/index.html                 # interactive workbench (no external resources)
└── dist/oop_visual_study_guide.pdf  # generated guide
```

---

## Setup

Requires Python 3.11 or newer.

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -e ".[dev]"            # installs reportlab + pytest
```

## Run the tests

```bash
pytest
```

The tests cover:

- **Catalog:** the four groups, nine concepts and six case studies.
- **Fuel invariants:** `burn(dt)` and `refuel(kg)` bounds; a rejected operation leaves state unchanged.
- **Scientific Solution model:** dilution material balance, solute addition, homogeneous aliquot removal, constructor/operation validation, independent instances, and the typed workbench schema.
- **Geometry and Liskov:** the geometry math, and the `Rectangle` vs. `Square` contract check.
- **Composition:** subclass-explosion counts versus composed-component counts.
- **Dispatch:** overload resolution by signature, and the figure layout bounds and arrow labels.
- **PDF output:**
  - a valid `%PDF` header and non-empty output;
  - typography (allowed fonts, ≥ 9 pt);
  - byte-identical rebuilds;
  - no leaked font or prompt strings.
- **Web workbench:** it must mirror the Python catalog and must not use external resources.

## Build the PDF

```bash
oop-guide-pdf                                  # after pip install -e .
# or, without installing:
PYTHONPATH=src python -m oop_guide.pdf_builder
# custom output path:
PYTHONPATH=src python -m oop_guide.pdf_builder --output /tmp/guide.pdf
```

The output is written to `dist/oop_visual_study_guide.pdf`, relative to the current directory. The builder uses ReportLab's invariant mode, so the same inputs always produce the same bytes.

## Open the interactive workbench

Open `web/index.html` directly in a browser (double-click it, or run `xdg-open web/index.html` / `open web/index.html`). You can also serve it:

```bash
python -m http.server 8000 -d web   # then visit http://localhost:8000/
```

### Break It / Invariant Lab

- **Propellant tank:** `burn(dt)` and `refuel(kg)` enforce `0 <= fuel_kg <= capacity_kg`, and rejected operations leave state unchanged. *Break it* writes `tank._fuel_kg = -50` directly, which shows what happens when encapsulation is bypassed.
- **Liskov:** run Rectangle-client code (`set_width(w); set_height(h); expect area == w*h`) against `Rectangle` or `Square`. The expected (dashed) and actual shapes are drawn side by side.
- **Composition:** swap the engine, guidance and comms components. The selected engine is bound into the propellant tank, so its burn rate changes the max burn time. Variant counters compare the inheritance product with the composition sum.
- **Dispatch:**
  - Pick a declared type and a runtime type to see which `draw()` override runs (runtime type) versus which `describe()` overload is chosen (declared type).
  - Animate the `for s in shapes` loop.
  - Resolve `translate(...)` overloads by argument count.

The original Invariant Lab follows the examples in `oop_guide.models`. `test_web_workbench_mirrors_catalog` checks catalog names, arrow labels, and palette.

### Materials Lab and your session guide

Choose **Materials Lab**, or open an experiment from a concept card. Each of the nine lessons runs code and shows both the OOP relationship and the resulting particle chambers.

1. **Lifecycle & State:** create distinct sample instances, try out-of-range starting amounts, and change one sample through a guarded operation.
2. **Contracts & Abstraction:** run `inspect(sample)` without managing its internals, then swap instruments that implement the same reading contract.
3. **Reuse & Structure:** check each material subtype against the base `Sample` contract, then mix a material, filter, and instrument without creating new subclasses.
4. **Polymorphic Dispatch:** call `glyph()` on different material types. Compare the runtime-selected silhouettes with signature-based `translate(...)` overloading in the Invariant Lab.

Try **Composition** with 12 units, **Fine mesh**, and **Sample scale**. Switching from salt crystals to dye particles changes the number of units that pass from 0 to 12. The rules and units are illustrative. Each run starts with fresh samples; the session notebook keeps the results so you can compare runs.

Select **Print / Save session as PDF** and choose your browser's PDF destination to export the notebook. The export includes parameters, diagrams, and accepted or rejected results for every Materials Lab run. The notebook stays in the current tab and is not saved across reloads. The checked-in PDF remains a separate, reproducible reference and includes a Materials Lab worksheet.

### Scientific Solution / Dilution Workbench

Choose **Solution Workbench**, or open it from the Encapsulation concept. The first scientific reference lesson models homogeneous aqueous sodium chloride solutions with `C = n / V`. It exposes `dilute(final_volume)`, `add_solute(amount)`, and `remove_volume(volume)`; the state inspector and execution trace show the object transition and material-balance calculation. Default values are pedagogical, not experimental measurements. The assumptions exclude reactions, precipitation, ion pairing, activity corrections, volume change on solute addition, and temperature change.

The workbench also compares two independent `Solution` objects containing the same `ChemicalSpecies`, provides Python, Java, and TypeScript examples, and distinguishes domain validation, type/contract, software-design, and numerical/model failures.

### Scientific OOP Workbenches · Groups 2–4

- **Detector contract:** `AnalysisPipeline` calls `Detector.measure(sample)` while absorbance, fluorescence, and electrochemical implementations apply distinct simplified calibration equations. Calibration inputs are explicitly labeled synthetic.
- **Biochemical inheritance:** Michaelis-Menten and competitive-inhibition rate objects are tested against a shared behavioral contract; a deliberately broken subtype demonstrates why biological taxonomy alone does not establish substitutability.
- **Reactor composition:** a reactor composes first-order constant/Arrhenius kinetics with ideal CSTR/plug-flow balances. Users can swap either collaborator and compare equations, concentration results, and response curves.
- **Kinetic dispatch:** one `rate(state)` call dispatches at runtime to zero-, first-, second-order, or simplified Michaelis-Menten kinetics. The workbench distinguishes overriding from language-specific overloading.

Each panel links the OOP model, scientific equation and units, object/method execution trace, state or result, assumptions, and Python/Java/TypeScript code. The scientific schema and deterministic Python reference implementations live in `src/oop_guide/science.py`; the inline browser models have Node.js behavior tests when Node is available. The project remains offline and adds no visualization dependencies; its information-bearing diagrams and plots use SVG.

The notebook layout, group inspector, and dark code/trap panels adapt the [uploaded HTML template](https://github.com/hess80/OOP/blob/0fba08790346b024264af66f431db324d39dc6ab/oop_visual_study_guide_architecture_workbench.html). The [uploaded PDF](https://github.com/hess80/OOP/blob/0fba08790346b024264af66f431db324d39dc6ab/OOP%20Visual%20Assets%20%26%20Study%20Guide.pdf) inspired the lesson-specific visual metaphors: guarded chambers, instrument contracts, modular parts, and dispatch silhouettes. The workbench redraws these as SVG rather than depending on external images or fonts.
