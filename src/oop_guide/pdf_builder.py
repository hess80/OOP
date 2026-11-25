"""Deterministic multi-page PDF generator for the OOP Visual Study Guide.

Two-layer diagram rule
----------------------
* Layer 1 - visual/vector structure: boxes, boundaries, arrow shafts, arrow
  heads and label pills are drawn as pure vector geometry first.
* Layer 2 - deterministic text/signatures: titles, monospace signatures and
  semantic arrow labels are drawn afterwards, on top of the geometry, from
  data defined in this module and in :mod:`oop_guide.models`.

Typography rule: graphic sans-serif/display (Helvetica family) and monospace
(Courier family) only - never script/handwriting faces - and never below 9 pt.

Run ``python -m oop_guide.pdf_builder`` to write
``dist/oop_visual_study_guide.pdf``.
"""

from __future__ import annotations

import argparse
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Sequence

from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import letter
from reportlab.lib.utils import simpleSplit
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfgen.canvas import Canvas

from . import __version__
from .models import (
    CASE_STUDIES,
    ENGINES,
    GROUPS,
    SEMANTIC_ARROW_LABELS,
    TRAIT_DIMENSIONS,
    Circle,
    InvariantLabState,
    InvariantViolation,
    Rectangle,
    Square,
    SquareShape,
    Triangle,
    check_rectangle_contract,
    composition_component_count,
    concept_by_key,
    resolve_describe_overload,
    resolve_translate,
    runtime_draw_target,
    subclass_explosion_count,
)

DEFAULT_OUTPUT = Path("dist") / "oop_visual_study_guide.pdf"

PAPER = HexColor("#F7F3E8")
GRID = HexColor("#E6DFC8")
NAVY = HexColor("#162B4D")
RUST = HexColor("#9E3B24")
TEAL = HexColor("#1C5D58")
CARD = HexColor("#FFFDF7")

DISPLAY = "Helvetica-Bold"
SANS = "Helvetica"
SANS_OBLIQUE = "Helvetica-Oblique"
MONO = "Courier"
MONO_BOLD = "Courier-Bold"
ALLOWED_FONTS = frozenset({DISPLAY, SANS, SANS_OBLIQUE, MONO, MONO_BOLD})
MIN_FONT_SIZE = 9.0

PAGE_W, PAGE_H = letter
MARGIN = 40.0
CONTENT_W = PAGE_W - 2 * MARGIN
TOP_Y = PAGE_H - 112.0
BOTTOM_Y = 58.0

TITLE_BAND = 20.0
SIG_LINE = 12.0
LABEL_SIZE = 9.0
SIG_SIZE = 9.0


# ---------------------------------------------------------------------------
# Diagram data (Layer 1 geometry + Layer 2 text are both derived from these)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Node:
    key: str
    x: float
    top: float
    w: float
    title: str
    signatures: tuple[str, ...] = ()
    color: object = NAVY

    @property
    def h(self) -> float:
        return TITLE_BAND + SIG_LINE * len(self.signatures) + (6 if self.signatures else 0)

    @property
    def y(self) -> float:
        return self.top - self.h

    @property
    def center(self) -> tuple[float, float]:
        return self.x + self.w / 2, self.y + self.h / 2

    def boundary_point(self, toward: tuple[float, float]) -> tuple[float, float]:
        cx, cy = self.center
        dx, dy = toward[0] - cx, toward[1] - cy
        if dx == 0 and dy == 0:
            return cx, cy
        tx = (self.w / 2) / abs(dx) if dx else math.inf
        ty = (self.h / 2) / abs(dy) if dy else math.inf
        t = min(tx, ty)
        return cx + dx * t, cy + dy * t


@dataclass(frozen=True)
class Edge:
    src: str
    dst: str
    label: str
    color: object = NAVY
    dashed: bool = False
    label_at: float = 0.5


@dataclass(frozen=True)
class Boundary:
    x: float
    y: float
    w: float
    h: float
    label: str
    color: object = TEAL


@dataclass(frozen=True)
class Figure:
    number: str
    title: str
    height: float
    nodes: tuple[Node, ...]
    edges: tuple[Edge, ...]
    caption: str
    boundaries: tuple[Boundary, ...] = ()

    def layout_problems(self, width: float = CONTENT_W - 12) -> list[str]:
        """Boxes and boundaries that fall outside the figure frame."""
        problems = []
        boxes = [(n.key, n.x, n.y, n.w, n.h) for n in self.nodes]
        boxes += [(bd.label, bd.x, bd.y, bd.w, bd.h) for bd in self.boundaries]
        for key, x, y, w, h in boxes:
            if x < 0 or y < 0 or x + w > width or y + h > self.height - 6:
                problems.append(f"figure {self.number}: {key} outside frame")
        return problems

    def node(self, key: str) -> Node:
        for node in self.nodes:
            if node.key == key:
                return node
        raise KeyError(key)


def figure_lifecycle() -> Figure:
    return Figure(
        "1.1", "Object lifecycle: instantiate, check, update", 280,
        nodes=(
            Node("class", 10, 245, 165, "Class FuelTank",
                 ("_fuel_kg: float", "_capacity_kg: float")),
            Node("ctor", 10, 105, 190, "Constructor",
                 ("__init__(engine, cap, fuel)",), TEAL),
            Node("object", 282, 245, 170, "Object tank_a",
                 ("_fuel_kg = 600.0", "_capacity_kg = 1000.0")),
            Node("burn", 238, 152, 112, "Operation", ("burn(dt: float)",), TEAL),
            Node("refuel", 382, 152, 128, "Operation", ("refuel(kg: float)",), TEAL),
            Node("invariant", 282, 62, 170, "Invariant",
                 ("0 <= fuel <= capacity",), RUST),
        ),
        edges=(
            Edge("class", "object", "instantiates"),
            Edge("burn", "object", "updates", TEAL),
            Edge("refuel", "object", "updates", TEAL),
            Edge("burn", "invariant", "checks", RUST),
            Edge("refuel", "invariant", "checks", RUST),
            Edge("ctor", "invariant", "checks", RUST, label_at=0.35),
        ),
        boundaries=(Boundary(224, 12, 292, 248, "ENCAPSULATION BOUNDARY"),),
        caption="Only burn() and refuel() cross the boundary; each checks the "
                "invariant before it updates state.",
    )


def figure_contracts() -> Figure:
    return Figure(
        "2.1", "Abstraction through an interface contract", 190,
        nodes=(
            Node("nav", 10, 160, 130, "Navigator", ("plan_burn(dv)",)),
            Node("prop", 240, 170, 210, "<<interface>> Propulsion",
                 ("thrust(dt: float) -> float",), TEAL),
            Node("chem", 140, 62, 170, "ChemicalEngine", ("rate = 25.0 kg/s",)),
            Node("ion", 345, 62, 170, "IonThruster", ("rate = 0.5 kg/s",)),
        ),
        edges=(
            Edge("nav", "prop", "delegates to"),
            Edge("chem", "prop", "implements", TEAL, dashed=True),
            Edge("ion", "prop", "implements", TEAL, dashed=True),
        ),
        caption="The caller sees thrust(); burn-rate maths stay hidden behind "
                "the contract.",
    )


def figure_reuse() -> Figure:
    return Figure(
        "3.1", "Inheritance (is-a) vs. composition (has-a)", 220,
        nodes=(
            Node("rect", 10, 205, 210, "Rectangle",
                 ("set_width(w: float)", "set_height(h: float)", "area() -> float")),
            Node("square", 10, 84, 210, "Square",
                 ("invariant: width == height", "set_w(5); set_h(4) -> 16"), RUST),
            Node("craft", 280, 205, 200, "Spacecraft",
                 ("thrust() / navigate() / send()",), TEAL),
            Node("engine", 236, 72, 86, "Engine", ("thrust()",)),
            Node("guidance", 330, 72, 86, "Guidance", ("heading()",)),
            Node("comms", 424, 72, 86, "Comms", ("send(msg)",)),
        ),
        edges=(
            Edge("square", "rect", "specializes", RUST),
            Edge("craft", "engine", "contains", TEAL, label_at=0.55),
            Edge("craft", "guidance", "contains", TEAL, label_at=0.55),
            Edge("craft", "comms", "contains", TEAL, label_at=0.55),
        ),
        caption="Square specializes Rectangle yet breaks substitutability "
                "(16 != 20). Spacecraft assembles swappable parts instead.",
    )


def figure_dispatch() -> Figure:
    return Figure(
        "4.1", "Dynamic dispatch through Shape.draw()", 190,
        nodes=(
            Node("shape", 180, 175, 180, "<<abstract>> Shape", ("draw()",)),
            Node("circle", 40, 62, 130, "Circle", ("draw()",), TEAL),
            Node("square", 205, 62, 130, "Square", ("draw()",), TEAL),
            Node("triangle", 370, 62, 130, "Triangle", ("draw()",), TEAL),
        ),
        edges=(
            Edge("shape", "circle", "dispatches to"),
            Edge("shape", "square", "dispatches to"),
            Edge("shape", "triangle", "dispatches to"),
        ),
        caption="s.draw() runs the override chosen by the runtime type of s.",
    )


def figure_overload() -> Figure:
    return Figure(
        "4.2", "Overload resolution by call signature", 150,
        nodes=(
            Node("call2", 10, 128, 175, "Call site", ("translate(1.0, 2.0)",)),
            Node("call3", 10, 56, 175, "Call site", ("translate(1.0, 2.0, 3.0)",)),
            Node("sig2", 280, 128, 232, "Overload",
                 (resolve_translate(1.0, 2.0),), TEAL),
            Node("sig3", 280, 56, 232, "Overload",
                 (resolve_translate(1.0, 2.0, 3.0),), TEAL),
        ),
        edges=(
            Edge("call2", "sig2", "matches"),
            Edge("call3", "sig3", "matches"),
        ),
        caption="Overload resolution depends on the call signature, not on the "
                "runtime object type.",
    )


GROUP_FIGURES = {
    "lifecycle": (figure_lifecycle,),
    "contracts": (figure_contracts,),
    "reuse": (figure_reuse,),
    "dispatch": (figure_dispatch, figure_overload),
}


# ---------------------------------------------------------------------------
# Document renderer
# ---------------------------------------------------------------------------


@dataclass
class BuildReport:
    path: Path
    pages: int
    fonts_used: set[str] = field(default_factory=set)
    min_font_size: float = math.inf
    arrow_labels: list[str] = field(default_factory=list)
    texts: list[str] = field(default_factory=list)
    figures: list[str] = field(default_factory=list)


class GuideDocument:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.c = Canvas(str(path), pagesize=letter, invariant=1, pageCompression=0)
        self.c.setTitle("OOP Visual Study Guide")
        self.c.setAuthor("oop_guide")
        self.c.setSubject("Four-group OOP framework")
        self.c.setCreator(f"oop_guide {__version__}")
        self.report = BuildReport(path=path, pages=0)
        self.page_no = 0
        self.y = TOP_Y
        self.section_title = ""

    # -- primitives ---------------------------------------------------------

    def text(self, x: float, y: float, s: str, font: str = SANS,
             size: float = 10.0, color: object = NAVY, align: str = "left",
             char_space: float = 0.0) -> None:
        if font not in ALLOWED_FONTS:
            raise ValueError(f"font {font} is not an allowed display/sans/mono face")
        if size < MIN_FONT_SIZE:
            raise ValueError(f"text below {MIN_FONT_SIZE} pt: {size}")
        width = stringWidth(s, font, size) + char_space * max(len(s) - 1, 0)
        if align == "center":
            x -= width / 2
        elif align == "right":
            x -= width
        obj = self.c.beginText(x, y)
        obj.setFont(font, size)
        obj.setCharSpace(char_space)
        obj.setFillColor(color)
        obj.textOut(s)
        self.c.drawText(obj)
        self.report.fonts_used.add(font)
        self.report.min_font_size = min(self.report.min_font_size, size)
        self.report.texts.append(s)

    def para(self, x: float, y: float, width: float, s: str, font: str = SANS,
             size: float = 9.5, leading: float = 12.5, color: object = NAVY) -> float:
        for line in simpleSplit(s, font, size, width):
            self.text(x, y, line, font, size, color)
            y -= leading
        return y

    def para_height(self, width: float, s: str, font: str = SANS,
                    size: float = 9.5, leading: float = 12.5) -> float:
        return len(simpleSplit(s, font, size, width)) * leading

    # -- page furniture -----------------------------------------------------

    def background(self) -> None:
        c = self.c
        c.setFillColor(PAPER)
        c.rect(0, 0, PAGE_W, PAGE_H, stroke=0, fill=1)
        c.setStrokeColor(GRID)
        step = 12.0
        for i in range(int(PAGE_W // step) + 1):
            c.setLineWidth(0.9 if i % 5 == 0 else 0.4)
            c.line(i * step, 0, i * step, PAGE_H)
        for j in range(int(PAGE_H // step) + 1):
            c.setLineWidth(0.9 if j % 5 == 0 else 0.4)
            c.line(0, j * step, PAGE_W, j * step)

    def start_page(self, kicker: str, title: str, subtitle: str = "") -> None:
        if self.page_no:
            self.c.showPage()
        self.page_no += 1
        self.section_title = title
        self.background()
        c = self.c
        c.setFillColor(NAVY)
        c.rect(MARGIN, PAGE_H - 52, 6, 30, stroke=0, fill=1)
        self.text(MARGIN + 14, PAGE_H - 34, kicker.upper(), DISPLAY, 9, RUST,
                  char_space=1.6)
        self.text(MARGIN + 14, PAGE_H - 56, title.upper(), DISPLAY, 19, NAVY,
                  char_space=0.8)
        if subtitle:
            self.text(MARGIN + 14, PAGE_H - 74, subtitle, SANS_OBLIQUE, 10, TEAL)
        c.setStrokeColor(NAVY)
        c.setLineWidth(1.6)
        c.line(MARGIN, PAGE_H - 88, PAGE_W - MARGIN, PAGE_H - 88)
        c.setLineWidth(0.6)
        c.line(MARGIN, 44, PAGE_W - MARGIN, 44)
        self.text(MARGIN, 30, "OOP VISUAL STUDY GUIDE", DISPLAY, 9, NAVY,
                  char_space=1.2)
        self.text(PAGE_W - MARGIN, 30, f"PAGE {self.page_no}", DISPLAY, 9, RUST,
                  align="right", char_space=1.2)
        self.y = TOP_Y
        self.report.pages = self.page_no

    def ensure(self, height: float) -> None:
        if self.y - height < BOTTOM_Y:
            self.start_page("continued", self.section_title)

    def heading(self, s: str, color: object = NAVY, size: float = 12.5) -> None:
        self.ensure(size + 8)
        self.text(MARGIN, self.y, s.upper(), DISPLAY, size, color, char_space=0.6)
        self.y -= size + 6

    # -- diagrams -----------------------------------------------------------

    def figure(self, fig: Figure) -> None:
        problems = fig.layout_problems()
        if problems:
            raise ValueError("; ".join(problems))
        caption_h = self.para_height(CONTENT_W, fig.caption, SANS_OBLIQUE, 9.5)
        self.ensure(fig.height + 24 + caption_h)
        self.text(MARGIN, self.y, f"FIGURE {fig.number}", DISPLAY, 10, RUST,
                  char_space=1.0)
        self.text(MARGIN + 74, self.y, fig.title, DISPLAY, 10, NAVY)
        top = self.y - 8
        x0, y0 = MARGIN + 6, top - fig.height
        c = self.c
        c.saveState()
        c.setStrokeColor(NAVY)
        c.setLineWidth(0.8)
        c.setFillColor(PAPER)
        c.roundRect(MARGIN, y0, CONTENT_W, fig.height, 6, stroke=1, fill=0)
        c.translate(x0, y0)
        pills = self._layer1(fig)
        self._layer2(fig, pills)
        c.restoreState()
        self.y = y0 - 14
        self.y = self.para(MARGIN, self.y, CONTENT_W, fig.caption, SANS_OBLIQUE,
                           9.5, color=TEAL) - 8
        self.report.figures.append(fig.number)

    def _layer1(self, fig: Figure) -> list[tuple[float, float, str, object]]:
        """Pure vector structure: boundaries, boxes, shafts, heads, pills."""
        c = self.c
        for b in fig.boundaries:
            c.setStrokeColor(b.color)
            c.setLineWidth(1.2)
            c.setDash(5, 3)
            c.roundRect(b.x, b.y, b.w, b.h, 8, stroke=1, fill=0)
            c.setDash()
        for n in fig.nodes:
            c.setStrokeColor(n.color)
            c.setLineWidth(1.4)
            c.setFillColor(CARD)
            c.roundRect(n.x, n.y, n.w, n.h, 4, stroke=1, fill=1)
            c.setFillColor(n.color)
            c.rect(n.x, n.top - TITLE_BAND, n.w, TITLE_BAND, stroke=0, fill=1)
        pills = []
        for e in fig.edges:
            if e.label not in SEMANTIC_ARROW_LABELS:
                raise ValueError(f"unknown arrow label {e.label!r}")
            src, dst = fig.node(e.src), fig.node(e.dst)
            start = src.boundary_point(dst.center)
            end = dst.boundary_point(src.center)
            c.setStrokeColor(e.color)
            c.setFillColor(e.color)
            c.setLineWidth(1.3)
            if e.dashed:
                c.setDash(4, 3)
            c.line(*start, *end)
            c.setDash()
            ang = math.atan2(end[1] - start[1], end[0] - start[0])
            size, spread = 8.0, 0.42
            p = c.beginPath()
            p.moveTo(*end)
            p.lineTo(end[0] - size * math.cos(ang - spread),
                     end[1] - size * math.sin(ang - spread))
            p.lineTo(end[0] - size * math.cos(ang + spread),
                     end[1] - size * math.sin(ang + spread))
            p.close()
            c.drawPath(p, stroke=0, fill=1)
            mx = start[0] + (end[0] - start[0]) * e.label_at
            my = start[1] + (end[1] - start[1]) * e.label_at
            w = stringWidth(e.label, SANS_OBLIQUE, LABEL_SIZE) + 8
            c.setFillColor(PAPER)
            c.setStrokeColor(e.color)
            c.setLineWidth(0.6)
            c.roundRect(mx - w / 2, my - 6.5, w, 13, 3, stroke=1, fill=1)
            pills.append((mx, my, e.label, e.color))
        return pills

    def _layer2(self, fig: Figure, pills: Sequence[tuple[float, float, str, object]]) -> None:
        """Deterministic text: titles, monospace signatures, arrow labels."""
        for b in fig.boundaries:
            self.text(b.x + b.w - 6, b.y + b.h + 4, b.label, DISPLAY, 9, b.color,
                      align="right", char_space=1.0)
        for n in fig.nodes:
            self.text(n.x + n.w / 2, n.top - 14, n.title, DISPLAY, 10, CARD,
                      align="center")
            for i, sig in enumerate(n.signatures):
                self.text(n.x + 6, n.top - TITLE_BAND - 12 - i * SIG_LINE, sig,
                          MONO, SIG_SIZE, NAVY)
        for mx, my, label, color in pills:
            self.text(mx, my - 3, label, SANS_OBLIQUE, LABEL_SIZE, color,
                      align="center")
            self.report.arrow_labels.append(label)

    # -- content blocks -----------------------------------------------------

    def concept_block(self, key: str) -> None:
        concept = concept_by_key(key)
        code_lines = concept.code.split("\n")
        narrative_h = self.para_height(CONTENT_W - 12, concept.narrative)
        trap_h = self.para_height(CONTENT_W - 24, concept.trap)
        total = 20 + narrative_h + 10 + len(code_lines) * 11 + 12 + trap_h + 14
        self.ensure(total)
        self.heading(concept.name, NAVY, 12.5)
        self.y = self.para(MARGIN, self.y, CONTENT_W - 12, concept.narrative) - 2
        code_top = self.y + 8
        code_h = len(code_lines) * 11 + 6
        c = self.c
        c.setFillColor(CARD)
        c.setStrokeColor(TEAL)
        c.setLineWidth(0.6)
        c.rect(MARGIN, code_top - code_h, CONTENT_W, code_h, stroke=1, fill=1)
        c.setFillColor(TEAL)
        c.rect(MARGIN, code_top - code_h, 4, code_h, stroke=0, fill=1)
        y = code_top - 11
        for line in code_lines:
            self.text(MARGIN + 12, y, line, MONO, 9, NAVY)
            y -= 11
        self.y = code_top - code_h - 14
        c.setFillColor(RUST)
        c.rect(MARGIN, self.y - trap_h + 10, 4, trap_h, stroke=0, fill=1)
        self.y = self.para(MARGIN + 12, self.y, CONTENT_W - 24, concept.trap,
                           SANS, 9.5, color=RUST) - 10

    def table(self, header: Sequence[str], rows: Sequence[Sequence[str]],
              widths: Sequence[float]) -> None:
        row_h = 15.0
        self.ensure(row_h * 2)
        c = self.c

        def draw_row(cells: Sequence[str], font: str, fill: object, color: object) -> None:
            c.setFillColor(fill)
            c.setStrokeColor(GRID)
            c.setLineWidth(0.6)
            c.rect(MARGIN, self.y - 4, CONTENT_W, row_h, stroke=1, fill=1)
            x = MARGIN + 6
            for cell, width in zip(cells, widths):
                self.text(x, self.y, cell, font, 9, color)
                x += width

        draw_row(header, DISPLAY, NAVY, CARD)
        self.y -= row_h
        for row in rows:
            self.ensure(row_h)
            draw_row(row, MONO, CARD, RUST if "REJECTED" in row[-1] or
                     "FAILS" in row[-1] else NAVY)
            self.y -= row_h
        self.y -= 10

    def save(self) -> BuildReport:
        self.c.save()
        return self.report


# ---------------------------------------------------------------------------
# Pages
# ---------------------------------------------------------------------------


def _cover(doc: GuideDocument) -> None:
    doc.start_page("Architecture workbench", "OOP Visual Study Guide",
                   "Four structure groups, two-layer diagrams, production failures")
    doc.y = doc.para(MARGIN, doc.y, CONTENT_W,
                     "Every concept in this guide is placed in one of four "
                     "structure groups. Every diagram is built in two layers: "
                     "Layer 1 is pure vector structure, Layer 2 is deterministic "
                     "text and monospace signatures. Every number is computed "
                     "by oop_guide.models, never typed by hand.", size=10.5,
                     leading=14) - 10
    c = doc.c
    box_w, box_h, gap = (CONTENT_W - 16) / 2, 132.0, 16.0
    colors = (NAVY, TEAL, RUST, NAVY)
    top = doc.y
    for i, group in enumerate(GROUPS):
        col, row = i % 2, i // 2
        x = MARGIN + col * (box_w + gap)
        y = top - (row + 1) * box_h - row * gap
        c.setFillColor(CARD)
        c.setStrokeColor(colors[i])
        c.setLineWidth(1.6)
        c.roundRect(x, y, box_w, box_h, 6, stroke=1, fill=1)
        c.setFillColor(colors[i])
        c.rect(x, y + box_h - 34, box_w, 34, stroke=0, fill=1)
    for i, group in enumerate(GROUPS):
        col, row = i % 2, i // 2
        x = MARGIN + col * (box_w + gap)
        y = top - (row + 1) * box_h - row * gap
        doc.text(x + 10, y + box_h - 22, f"{group.number:02d}", DISPLAY, 16, PAPER)
        doc.text(x + 40, y + box_h - 21, group.title.upper(), DISPLAY, 10.5, PAPER,
                 char_space=0.4)
        ty = doc.para(x + 10, y + box_h - 52, box_w - 20, group.summary,
                      SANS_OBLIQUE, 9.5, 12, TEAL) - 4
        for key in group.concept_keys:
            doc.text(x + 14, ty, f"- {concept_by_key(key).name}", MONO_BOLD, 9.5,
                     NAVY)
            ty -= 12
    doc.y = top - 2 * box_h - gap - 26

    doc.heading("Diagram layer rules")
    rules = (
        ("LAYER 1", "Visual/vector structure: boxes, boundaries, arrow shafts, "
                    "arrow heads, label pills. No text."),
        ("LAYER 2", "Deterministic text: display titles, monospace signatures and "
                    "semantic arrow labels drawn over Layer 1."),
        ("ARROWS", "Every arrow carries one explicit label: "
                   + ", ".join(SEMANTIC_ARROW_LABELS) + "."),
        ("TYPE", "Graphic sans-serif/display headings and monospace signatures "
                 "only; no handwriting or script faces; nothing below 9 pt."),
    )
    for tag, body in rules:
        doc.text(MARGIN, doc.y, tag, DISPLAY, 9.5, RUST, char_space=1.0)
        doc.y = doc.para(MARGIN + 70, doc.y, CONTENT_W - 70, body) - 4
    doc.y -= 6
    doc.heading("Palette")
    swatches = (("PAPER", "#F7F3E8", PAPER), ("GRID", "#E6DFC8", GRID),
                ("NAVY", "#162B4D", NAVY), ("RUST", "#9E3B24", RUST),
                ("TEAL", "#1C5D58", TEAL))
    sw = CONTENT_W / len(swatches)
    for i, (_name, _hex, color) in enumerate(swatches):
        c.setFillColor(color)
        c.setStrokeColor(NAVY)
        c.setLineWidth(0.8)
        c.rect(MARGIN + i * sw, doc.y - 22, sw - 10, 26, stroke=1, fill=1)
    for i, (name, hexcode, _color) in enumerate(swatches):
        doc.text(MARGIN + i * sw, doc.y - 36, f"{name} {hexcode}", MONO_BOLD, 9, NAVY)


def _group_pages(doc: GuideDocument) -> None:
    for group in GROUPS:
        doc.start_page(f"Group {group.number} of 4", group.title, group.summary)
        for make in GROUP_FIGURES[group.key]:
            doc.figure(make())
        for key in group.concept_keys:
            doc.concept_block(key)


def deterministic_check_rows() -> dict[str, list[tuple[str, ...]]]:
    """All computed values printed on the checks page."""
    circle, square, triangle = Circle(1.5), SquareShape(3.0), Triangle(4.0, 3.5)
    geometry = [
        ("Circle r=1.5", f"{circle.area():.4f}", f"{circle.perimeter():.4f}"),
        ("Square s=3", f"{square.area():g}", f"{square.perimeter():g}"),
        ("Triangle b=4, h=3.5", f"{triangle.area():g}", "n/a (sides unknown)"),
    ]

    fuel: list[tuple[str, ...]] = []
    state = InvariantLabState(fuel_kg=600.0)
    for op, arg in (("burn", 4.0), ("refuel", 200.0), ("refuel", 400.0),
                    ("burn", 30.0), ("burn", -1.0), ("burn", 28.0)):
        before = state.fuel_kg
        try:
            state = getattr(state, op)(arg)
            outcome = f"OK -> {state.fuel_kg:g} kg"
        except InvariantViolation:
            outcome = "REJECTED (state unchanged)"
        fuel.append((f"{op}({arg:g})", f"{before:g} kg", outcome))

    lsp = []
    for shape in (Rectangle(1.0, 1.0), Square(1.0)):
        result = check_rectangle_contract(shape)
        lsp.append((result.type_name, "set_width(5); set_height(4)",
                    f"{result.actual_area:g} (expected {result.expected_area:g})",
                    "HOLDS" if result.holds else "FAILS"))

    sizes = [len(v) for v in TRAIT_DIMENSIONS.values()]
    explosion = [(" x ".join(map(str, sizes)), str(subclass_explosion_count(sizes)),
                  " + ".join(map(str, sizes)), str(composition_component_count(sizes)))]

    dispatch = [
        ("translate(1.0, 2.0)", "call signature", resolve_translate(1.0, 2.0)),
        ("translate(1.0, 2.0, 3.0)", "call signature",
         resolve_translate(1.0, 2.0, 3.0)),
        ("describe(s), s: Shape = Circle", "static type Shape",
         resolve_describe_overload("Shape")),
        ("s.draw(), s: Shape = Circle", "runtime type Circle",
         runtime_draw_target("Circle")),
    ]
    engines = [(e.name, f"{e.burn_rate_kg_s:g} kg/s",
                f"{InvariantLabState(600.0).swap_engine(e).max_burn_seconds():g} s")
               for e in ENGINES]
    return {"geometry": geometry, "fuel": fuel, "lsp": lsp,
            "explosion": explosion, "dispatch": dispatch, "engines": engines}


def _checks_page(doc: GuideDocument) -> None:
    doc.start_page("Deterministic checks", "Invariant Lab results",
                   "Computed by oop_guide.models at build time")
    rows = deterministic_check_rows()
    doc.heading("Geometry (kept out of Figure 4.1)")
    doc.table(("Shape", "Area", "Perimeter"), rows["geometry"], (180, 150, 200))
    doc.heading("Propellant bounds: 0 <= fuel <= 1000 kg, 25 kg/s")
    doc.table(("Operation", "Before", "Outcome"), rows["fuel"], (150, 110, 270))
    doc.heading("Liskov contract: Rectangle vs. Square")
    doc.table(("Type", "Client calls", "Area", "Contract"), rows["lsp"],
              (90, 190, 160, 90))
    doc.heading("Subclass explosion vs. composition")
    doc.table(("Trait sizes", "Subclasses", "Components", "Classes"),
              rows["explosion"], (130, 130, 130, 140))
    doc.heading("Component swap: max burn from 600 kg")
    doc.table(("Engine", "Rate", "Max burn"), rows["engines"], (180, 150, 200))
    doc.heading("Runtime dispatch vs. signature overloading")
    doc.table(("Call", "Selected by", "Target"), rows["dispatch"], (195, 135, 200))


def _materials_page(doc: GuideDocument) -> None:
    doc.start_page("Practice worksheet", "Materials Lab",
                   "Run the experiments in the web workbench and save your own guide")
    doc.y = doc.para(MARGIN, doc.y, CONTENT_W,
                     "Open web/index.html and choose Materials Lab. Follow the four groups "
                     "below, using salt crystals, quartz grains, and dye particles. The "
                     "amounts, masses, and filter rules are illustrative, not measurements.") - 12
    exercises = (
        ("1. Object Lifecycle & State",
         "Create two salt samples at 12 units. Apply a change of -4 to A: A becomes 8 "
         "and B stays at 12. Try starting at 25 or subtracting 13 from a fresh 12-unit "
         "sample. The constructor rejects the first; the guarded operation rejects the second."),
        ("2. Contracts & Abstraction",
         "Keep inspect(sample) fixed and compare Open channel with Fine mesh. Then swap "
         "the Particle counter for the Sample scale. Both implement the reading contract, "
         "but report different quantities."),
        ("3. Code Reuse & Structure",
         "Check each material subtype against the same Sample contract at 0 and 12 units. "
         "Then compare salt and dye with Fine mesh and Sample scale: the mesh passes dye "
         "but blocks salt. Swap the filter without creating a new Sample subclass."),
        ("4. Polymorphic Dispatch",
         "Call sample.glyph() on each material. The runtime class selects a crystal, "
         "grain, or dot. Contrast this with the two translate signatures in Figure 4.2."),
    )
    for heading, instructions in exercises:
        doc.heading(heading)
        doc.y = doc.para(MARGIN, doc.y, CONTENT_W, instructions) - 12
    doc.heading("Take your guide with you")
    doc.y = doc.para(MARGIN, doc.y, CONTENT_W,
                     "In the Materials Lab, choose Print / Save session as PDF and select "
                     "the PDF destination in your browser. The guide records each run's "
                     "parameters, result, and diagrams, including rejected runs.")


def _case_pages(doc: GuideDocument) -> None:
    doc.start_page("Production failures", "Case studies",
                   "Behavioral failures and their structural fixes")
    c = doc.c
    inner = CONTENT_W - 100
    for case in CASE_STUDIES:
        parts = (("SYMPTOM", case.symptom, RUST), ("ROOT CAUSE", case.root_cause, NAVY),
                 ("FIX", case.fix, TEAL))
        body_h = sum(doc.para_height(inner, text) + 4 for _, text, _ in parts)
        card_h = 44 + body_h + 16
        doc.ensure(card_h + 10)
        top = doc.y + 12
        c.setFillColor(CARD)
        c.setStrokeColor(NAVY)
        c.setLineWidth(1.0)
        c.roundRect(MARGIN, top - card_h, CONTENT_W, card_h, 5, stroke=1, fill=1)
        c.setFillColor(RUST)
        c.rect(MARGIN, top - card_h, 5, card_h, stroke=0, fill=1)
        doc.text(MARGIN + 14, top - 18, case.title.upper(), DISPLAY, 10.5, NAVY,
                 char_space=0.4)
        related = ", ".join(concept_by_key(k).name for k in case.related_concepts)
        y = top - 48
        for tag, body, color in parts:
            doc.text(MARGIN + 14, y, tag, DISPLAY, 9, color, char_space=0.8)
            y = doc.para(MARGIN + 92, y, inner, body) - 4
        doc.text(MARGIN + 14, top - 32, f"related: {related}", MONO, 9, TEAL)
        doc.y = top - card_h - 22


def build_pdf(output: Path | str = DEFAULT_OUTPUT) -> BuildReport:
    """Build the study guide PDF and return a report of what was drawn."""
    path = Path(output)
    path.parent.mkdir(parents=True, exist_ok=True)
    doc = GuideDocument(path)
    _cover(doc)
    _group_pages(doc)
    _checks_page(doc)
    _materials_page(doc)
    _case_pages(doc)
    return doc.save()


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("-o", "--output", default=str(DEFAULT_OUTPUT),
                        help=f"output path (default: {DEFAULT_OUTPUT})")
    args = parser.parse_args(argv)
    report = build_pdf(args.output)
    print(f"Wrote {report.path} ({report.pages} pages, "
          f"{report.path.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
