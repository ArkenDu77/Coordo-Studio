from __future__ import annotations
import copy
import io
import os
import zipfile
from pathlib import Path
from typing import Iterable
from lxml import etree
from .models import DocumentBlock, Suggestion

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
NS = {"w": W}
qn = lambda tag: f"{{{W}}}{tag}"


def _read_docx_bytes(source) -> bytes:
    if isinstance(source, (bytes, bytearray)):
        return bytes(source)
    if hasattr(source, "read"):
        pos = source.tell() if hasattr(source, "tell") else None
        data = source.read()
        if pos is not None:
            source.seek(pos)
        return data
    return Path(source).read_bytes()


def extract_blocks(source) -> tuple[list[DocumentBlock], bytes]:
    data = _read_docx_bytes(source)
    with zipfile.ZipFile(io.BytesIO(data), "r") as zf:
        xml = zf.read("word/document.xml")
    root = etree.fromstring(xml)
    blocks: list[DocumentBlock] = []
    for idx, p in enumerate(root.xpath("//w:body//w:p", namespaces=NS)):
        text = "".join(p.xpath(".//w:t/text()", namespaces=NS))
        if not text.strip():
            continue
        pstyle = p.find("./w:pPr/w:pStyle", namespaces=NS)
        style = pstyle.get(qn("val")) if pstyle is not None else ""
        blocks.append(DocumentBlock(
            id=f"p-{idx}",
            index=idx,
            text=text,
            style=style or "",
            starred=("★" in text or "*" in text[:4]),
        ))
    return blocks, data


def _run_text(run) -> str:
    return "".join(run.xpath(".//w:t/text()", namespaces=NS))


def _ensure_rpr(run):
    rpr = run.find("./w:rPr", namespaces=NS)
    if rpr is None:
        rpr = etree.Element(qn("rPr"))
        run.insert(0, rpr)
    return rpr


def _set_run_style(run, bold=False, strike=False, highlight=None):
    rpr = _ensure_rpr(run)
    if bold and rpr.find("./w:b", namespaces=NS) is None:
        rpr.append(etree.Element(qn("b")))
    if strike and rpr.find("./w:strike", namespaces=NS) is None:
        rpr.append(etree.Element(qn("strike")))
    if highlight:
        old = rpr.find("./w:highlight", namespaces=NS)
        if old is None:
            old = etree.Element(qn("highlight"))
            rpr.append(old)
        old.set(qn("val"), highlight)


def _new_run(text: str, *, bold=False, strike=False, highlight=None):
    r = etree.Element(qn("r"))
    _set_run_style(r, bold=bold, strike=strike, highlight=highlight)
    t = etree.SubElement(r, qn("t"))
    if text.startswith(" ") or text.endswith(" "):
        t.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
    t.text = text
    return r


def _paragraphs(root):
    return root.xpath("//w:body//w:p", namespaces=NS)


def _paragraph_by_block_id(root, block_id: str):
    try:
        idx = int(block_id.split("-")[-1])
    except Exception:
        return None
    ps = _paragraphs(root)
    if 0 <= idx < len(ps):
        return ps[idx]
    return None


def _clone_paragraph_shell(p):
    np = etree.Element(qn("p"), nsmap=p.nsmap)
    ppr = p.find("./w:pPr", namespaces=NS)
    if ppr is not None:
        np.append(copy.deepcopy(ppr))
    return np


def _safe_style_exact_text_in_run(p, exact_text: str, *, strike=False, bold=False, highlight=None) -> bool:
    # Ultra-conservative: only mutate when the complete target is contained in a single run.
    for r in p.xpath("./w:r", namespaces=NS):
        txt = _run_text(r)
        if exact_text and exact_text in txt:
            if txt == exact_text:
                _set_run_style(r, strike=strike, bold=bold, highlight=highlight)
                return True
            # split the run while preserving its original rPr on before/after
            pos = txt.find(exact_text)
            before, after = txt[:pos], txt[pos+len(exact_text):]
            parent = r.getparent()
            insert_at = parent.index(r)
            rpr = r.find("./w:rPr", namespaces=NS)
            def mk_piece(value, special=False):
                rr = etree.Element(qn("r"))
                if rpr is not None:
                    rr.append(copy.deepcopy(rpr))
                if special:
                    _set_run_style(rr, strike=strike, bold=bold, highlight=highlight)
                tt = etree.SubElement(rr, qn("t"))
                if value.startswith(" ") or value.endswith(" "):
                    tt.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
                tt.text = value
                return rr
            pieces = []
            if before: pieces.append(mk_piece(before))
            pieces.append(mk_piece(exact_text, True))
            if after: pieces.append(mk_piece(after))
            parent.remove(r)
            for off, piece in enumerate(pieces):
                parent.insert(insert_at + off, piece)
            return True
    return False


def apply_suggestions(original_docx: bytes, suggestions: Iterable[Suggestion], highlight_color: str = "cyan") -> tuple[bytes, list[str]]:
    src = io.BytesIO(original_docx)
    out = io.BytesIO()
    warnings: list[str] = []
    with zipfile.ZipFile(src, "r") as zin:
        xml = zin.read("word/document.xml")
        root = etree.fromstring(xml)
        # Stable references: capture every original paragraph before any insertion,
        # otherwise insertions would shift numerical indexes and later patches could target the wrong paragraph.
        original_paragraphs = list(_paragraphs(root))
        block_map = {f"p-{i}": p for i, p in enumerate(original_paragraphs)}

        for s in suggestions:
            if s.decision != "accepted" or s.action in ("no_change", "review"):
                continue
            p = block_map.get(s.block_id)
            if p is None:
                warnings.append(f"{s.id}: paragraphe cible introuvable")
                continue
            if s.action in ("insert_after", "insert_before"):
                np = _clone_paragraph_shell(p)
                np.append(_new_run(s.new_text, bold=True, highlight=highlight_color))
                parent = p.getparent()
                ix = parent.index(p) + (1 if s.action == "insert_after" else 0)
                parent.insert(ix, np)
            elif s.action == "strike_text":
                target = s.anchor_text.strip()
                ok = _safe_style_exact_text_in_run(p, target, strike=True, highlight=highlight_color)
                if not ok:
                    warnings.append(f"{s.id}: suppression non appliquée automatiquement (cible répartie sur plusieurs runs)")
            elif s.action == "replace_text":
                # A replacement is safe only if exact text is in a single run.
                target = s.anchor_text.strip()
                found = False
                for r in p.xpath("./w:r", namespaces=NS):
                    txt = _run_text(r)
                    if target and target in txt:
                        if txt != target:
                            warnings.append(f"{s.id}: remplacement non appliqué (cible partielle dans un run)")
                            found = True
                            break
                        for t in r.xpath(".//w:t", namespaces=NS):
                            t.text = s.new_text
                        _set_run_style(r, bold=True, highlight=highlight_color)
                        found = True
                        break
                if not found:
                    warnings.append(f"{s.id}: remplacement non appliqué (cible introuvable)")

        new_xml = etree.tostring(root, xml_declaration=True, encoding="UTF-8", standalone="yes")
        with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zout:
            for item in zin.infolist():
                if item.filename == "word/document.xml":
                    zout.writestr(item, new_xml)
                else:
                    zout.writestr(item, zin.read(item.filename))
    return out.getvalue(), warnings
