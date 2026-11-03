# Construye el documento del trabajo de grado desde content.py, con estilos, márgenes y página de plantilla.docx.
# Uso: python reports/documento/build/build.py  (requiere python-docx)
import copy, re, sys
import docx
from docx.enum.section import WD_ORIENT, WD_SECTION
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
from docx.shared import Pt, Emu, Twips

from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from content import C, TITLE

doc = docx.Document(str(HERE / "plantilla.docx"))
body = doc.element.body
final_sectpr = body.sectPr
for el in list(body):
    if el is not final_sectpr:
        body.remove(el)

TOKEN = re.compile(r"(\*\*.+?\*\*|\*.+?\*)")


def add_runs(par, text, size=None):
    for part in TOKEN.split(text):
        if not part:
            continue
        if part.startswith("**"):
            r = par.add_run(part[2:-2])
            r.bold = True
        elif part.startswith("*"):
            r = par.add_run(part[1:-1])
            r.italic = True
        else:
            r = par.add_run(part)
        if size:
            r.font.size = Pt(size)
    return par


def para(text, style="Normal", align=None, size=None):
    par = doc.add_paragraph(style=style)
    add_runs(par, text, size)
    if align is not None:
        par.alignment = align
    return par


# numeración simple para objetivos (sin depender de definiciones de numeración del original)
def numbered(items):
    for i, t in enumerate(items, 1):
        par = doc.add_paragraph(style="Normal")
        par.paragraph_format.left_indent = Emu(274320)
        par.paragraph_format.first_line_indent = Emu(-274320)
        add_runs(par, f"OE{i}.\t{t}")


def set_cell_border(cell, **kw):
    tcPr = cell._tc.get_or_add_tcPr()
    borders = tcPr.find(qn("w:tcBorders"))
    if borders is None:
        borders = OxmlElement("w:tcBorders")
        tcPr.append(borders)
    for edge, val in kw.items():
        el = OxmlElement(f"w:{edge}")
        for k, v in val.items():
            el.set(qn(f"w:{k}"), str(v))
        borders.append(el)


def set_landscape(section, landscape):
    w, h = section.page_width, section.page_height
    if landscape and w < h or (not landscape and w > h):
        section.page_width, section.page_height = h, w
    section.orientation = WD_ORIENT.LANDSCAPE if landscape else WD_ORIENT.PORTRAIT


def add_table(spec):
    if spec["landscape"]:
        sec = doc.add_section(WD_SECTION.NEW_PAGE)
        set_landscape(sec, True)
    cap = doc.add_paragraph(style="Normal")
    m = re.match(r"(Tabla [A-Z]?\d+\.)\s*(.*)", spec["caption"])
    r = cap.add_run(m.group(1) + " ")
    r.bold = True
    r = cap.add_run(m.group(2))
    r.italic = True
    cap.paragraph_format.keep_with_next = True
    headers, rows, widths, fs = spec["headers"], spec["rows"], spec["widths"], spec["font"]
    t = doc.add_table(rows=1 + len(rows), cols=len(headers))
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    t.autofit = False
    # bordes horizontales tipo APA: superior, bajo encabezado e inferior; líneas finas entre filas
    tblPr = t._tbl.tblPr
    lay = OxmlElement("w:tblLayout")
    lay.set(qn("w:type"), "fixed")
    tblPr.append(lay)
    for i, row in enumerate([headers] + rows):
        for j, val in enumerate(row):
            cell = t.cell(i, j)
            cell.width = Twips(widths[j])
            cp = cell.paragraphs[0]
            cp.paragraph_format.space_after = Pt(1)
            cp.paragraph_format.space_before = Pt(1)
            cp.paragraph_format.line_spacing = 1.0
            run = cp.add_run(str(val))
            run.font.size = Pt(fs)
            if i == 0:
                run.bold = True
            b = {}
            if i == 0:
                b["top"] = {"val": "single", "sz": 8, "color": "000000"}
                b["bottom"] = {"val": "single", "sz": 6, "color": "000000"}
            elif i == len(rows):
                b["bottom"] = {"val": "single", "sz": 8, "color": "000000"}
            else:
                b["bottom"] = {"val": "single", "sz": 2, "color": "BFBFBF"}
            set_cell_border(cell, **b)
        if i == 0:
            trPr = t.rows[0]._tr.get_or_add_trPr()
            h = OxmlElement("w:tblHeader")
            h.set(qn("w:val"), "true")
            trPr.append(h)
    # anchos de columna en la grilla
    grid = t._tbl.tblGrid
    for j, gc in enumerate(grid.findall(qn("w:gridCol"))):
        gc.set(qn("w:w"), str(widths[j]))
    if spec.get("note"):
        n = doc.add_paragraph(style="Normal")
        r = n.add_run("Nota. ")
        r.italic = True
        r.font.size = Pt(9)
        r = n.add_run(spec["note"])
        r.font.size = Pt(9)
    else:
        doc.add_paragraph(style="Normal").paragraph_format.space_after = Pt(2)
    if spec["landscape"]:
        sec = doc.add_section(WD_SECTION.NEW_PAGE)
        set_landscape(sec, False)


# portada
doc.add_paragraph(TITLE, style="Title")
for kind, val in C:
    if kind == "subtitle":
        para(val)
    elif kind == "meta":
        para(val)
    elif kind == "h1":
        doc.add_paragraph(val, style="Heading 1")
    elif kind == "h2":
        doc.add_paragraph(val, style="Heading 2")
    elif kind == "h3":
        doc.add_paragraph(val, style="Heading 3")
    elif kind == "p":
        para(val)
    elif kind == "bullets":
        for it in val:
            para(it, style="List Bullet")
    elif kind == "numbered":
        numbered(val)
    elif kind == "table":
        add_table(val)
    elif kind == "ref":
        par = para(val)
        par.paragraph_format.left_indent = Emu(274320)
        par.paragraph_format.first_line_indent = Emu(-274320)
    elif kind == "image":
        from docx.shared import Inches

        img = HERE.parents[2] / val["path"]
        doc.add_paragraph(style="Normal").add_run().add_picture(str(img), width=Inches(val.get("width", 6.5)))
        cap = doc.add_paragraph(style="Normal")
        r = cap.add_run(val["caption"].split(".")[0] + ". ")
        r.bold = True
        r = cap.add_run(".".join(val["caption"].split(".")[1:]).strip())
        r.italic = True
    elif kind == "pagebreak":
        doc.add_paragraph().add_run().add_break(WD_BREAK.PAGE)

out = str(HERE.parent / "Perfilamiento funcional de jugadores - revisado v3.docx")
props = doc.core_properties
props.author = props.last_modified_by = "Eduar Felipe Riaño Torres"
props.comments = ""
doc.save(out)
print("ok", out)
