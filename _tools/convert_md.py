"""받아 둔 3GPP 본문(docx)을 Markdown 으로 바꾼다.

사용: python convert_md.py [규격번호 ...] [--force]
본문 옆에 <본문 이름>.md 와 media/ 를 만든다. 본문이 .doc(구형 바이너리)인
규격은 표준 라이브러리로 읽을 수 없어 변환하지 않고 원문 그대로 둔다.

3GPP 문서는 스타일이 정형화돼 있어 스타일 이름만으로 구조를 구분한다.
  Heading 1~9 / H6   제목 (Heading 8 · 9 는 Annex 제목이라 1단계로 올린다)
  B1~B5              글머리 (표지 문자 "-" · "a)" 가 본문에 들어 있다)
  PL                 코드 · ASN.1 · XML
  NO · Editor's Note 인용 블록
  TH · TF            표 · 그림 제목
  TOC1~9             목차 (버린다 - 쪽 번호만 남는다)
"""
import posixpath
import re
import sys
import xml.etree.ElementTree as ET
import zipfile

from common import load_specs, main_doc, spec_dir, cover, zip_url

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
R = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
A = "http://schemas.openxmlformats.org/drawingml/2006/main"
V = "urn:schemas-microsoft-com:vml"
M = "http://schemas.openxmlformats.org/officeDocument/2006/math"
PKG = "http://schemas.openxmlformats.org/package/2006/relationships"


def w(tag):
    return f"{{{W}}}{tag}"


# Symbol · Wingdings 글꼴의 기호는 사용자 정의 영역(U+F0xx) 코드로 들어 있어 그대로 두면
# 다른 글꼴에서 깨진다. 글꼴별로 자주 나오는 것만 옮기고, 모르는 코드는 원래 값을 둔다.
SYMBOL = {0xAE: "→", 0xAC: "←", 0xAD: "↑", 0xAF: "↓", 0xDE: "⇒", 0xDC: "⇐",
          0xDB: "⇔", 0xB3: "≥", 0xA3: "≤", 0xB9: "≠", 0xB4: "×", 0xB1: "±",
          0xB7: "•", 0xA5: "∞", 0xD6: "√", 0xE5: "∑", 0xB6: "∂", 0xBB: "≈",
          0x6D: "μ", 0x70: "π", 0x61: "α", 0x62: "β", 0x67: "γ", 0x64: "δ",
          0x44: "Δ", 0x6C: "λ", 0x73: "σ", 0x57: "Ω", 0xC5: "⊕", 0xC4: "⊗",
          0xE0: "◊", 0xB0: "°", 0xCE: "∈", 0xCF: "∉", 0xC7: "∩", 0xC8: "∪",
          0xCC: "⊂", 0xD9: "∧", 0xDA: "∨", 0xD8: "¬", 0xA2: "′", 0xB2: "″", 0xBC: "…"}
# Symbol 글꼴의 영문자 자리는 그리스 문자다 (A -> Α, q -> θ ...)
SYMBOL.update(zip(map(ord, "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"),
                  "ΑΒΧΔΕΦΓΗΙϑΚΛΜΝΟΠΘΡΣΤΥςΩΞΨΖαβχδεφγηιϕκλμνοπθρστυϖωξψζ"))
WINGDINGS = {0xE0: "→", 0xDF: "←", 0xE8: "→", 0xE7: "←", 0xD8: "➢", 0xFC: "✓",
             0xFB: "✗", 0x9F: "•", 0xA7: "▪", 0x6C: "●", 0x6E: "■", 0xF0: "⇒",
             0xF3: "⇔"}


def font_char(font, code):
    """글꼴 이름과 PUA 코드로 실제 문자를 고른다."""
    low = code & 0xFF
    if "wingdings" in (font or "").lower():
        return WINGDINGS.get(low, chr(code))
    if low in SYMBOL:
        return SYMBOL[low]
    # Symbol 글꼴의 숫자 · 문장부호는 ASCII 와 같은 자리에 있다 (영문자 자리는 그리스 문자)
    if 0x20 <= low < 0x7F and not chr(low).isalpha():
        return chr(low)
    return chr(code)

HEADING = re.compile(r"heading (\d)")
BULLET = re.compile(r"b(\d)\+?")
MARKER = re.compile(r"^(-|–|•|\*)\s+")
PUA = re.compile("[\uf000-\uf0ff]")


def kids(el, tag):
    """el 의 직계 tag 자식. sdt · customXml 감싸개는 건너 들어가되 중첩 표 안으로는 들어가지 않는다."""
    for c in el:
        if c.tag == w(tag):
            yield c
        elif c.tag in (w("sdt"), w("sdtContent"), w("customXml")):
            yield from kids(c, tag)


def on(rpr, tag):
    if rpr is None:
        return False
    el = rpr.find(w(tag))
    return el is not None and el.get(w("val"), "true") not in ("0", "false", "none")


class Converter:
    def __init__(self, z, out_dir):
        self.z = z
        self.out_dir = out_dir
        self.media = {}
        self.fields = []        # 열린 필드마다 "code" / "result"
        self.styles = self._styles()
        self.rels = self._rels()

    # ---- 패키지 메타 ----------------------------------------------------
    def _styles(self):
        try:
            root = ET.fromstring(self.z.read("word/styles.xml"))
        except KeyError:
            return {}
        out = {}
        for st in root.iter(w("style")):
            name = st.find(w("name"))
            out[st.get(w("styleId"))] = (name.get(w("val")) if name is not None
                                         else st.get(w("styleId"))).lower()
        return out

    def _rels(self):
        try:
            root = ET.fromstring(self.z.read("word/_rels/document.xml.rels"))
        except KeyError:
            return {}
        return {r.get("Id"): r.get("Target") for r in root.iter(f"{{{PKG}}}Relationship")
                if r.get("TargetMode") != "External"}

    def image(self, rid):
        target = self.rels.get(rid)
        if not target:
            return ""
        if target not in self.media:
            src = posixpath.normpath(posixpath.join("word", target))
            name = posixpath.basename(src)
            try:
                data = self.z.read(src)
            except KeyError:
                return ""
            d = self.out_dir / "media"
            d.mkdir(exist_ok=True)
            (d / name).write_bytes(data)
            self.media[target] = name
        return f"![](media/{self.media[target]})"

    # ---- 인라인 ---------------------------------------------------------
    def visible(self):
        return all(f == "result" for f in self.fields)

    def run(self, r, out):
        rpr = r.find(w("rPr"))
        hidden = on(rpr, "vanish")
        fmt = on(rpr, "b")      # 기울임은 버린다 - 굵게와 겹치면 ** · * 표시가 엉킨다
        fonts = rpr.find(w("rFonts")) if rpr is not None else None
        font = None if fonts is None else (fonts.get(w("ascii")) or fonts.get(w("hAnsi")))
        for c in r:
            tag = c.tag
            if tag == w("fldChar"):
                t = c.get(w("fldCharType"))
                if t == "begin":
                    self.fields.append("code")
                elif t == "separate" and self.fields:
                    self.fields[-1] = "result"
                elif t == "end" and self.fields:
                    self.fields.pop()
                continue
            if hidden or not self.visible():
                continue
            if tag == w("t"):
                text = c.text or ""
                if PUA.search(text):
                    text = PUA.sub(lambda m: font_char(font, ord(m.group(0))), text)
                out.append((text, fmt))
            elif tag == w("tab"):
                out.append(("\t", fmt))
            elif tag in (w("br"), w("cr")):
                if c.get(w("type")) != "page":
                    out.append(("\n", fmt))
            elif tag == w("noBreakHyphen"):
                out.append(("-", fmt))
            elif tag == w("sym"):
                code = int(c.get(w("char"), "3F"), 16)
                if code < 0xF000:
                    code += 0xF000     # w:sym 은 F0 접두 없이 적히기도 한다
                out.append((font_char(c.get(w("font")) or font, code), fmt))
            elif tag in (w("drawing"), w("pict"), w("object")):
                for blip in c.iter(f"{{{A}}}blip"):
                    out.append((self.image(blip.get(f"{{{R}}}embed")), "raw"))
                    break
                else:
                    for im in c.iter(f"{{{V}}}imagedata"):
                        out.append((self.image(im.get(f"{{{R}}}id")), "raw"))
                        break

    def inline(self, el, out):
        for c in el:
            tag = c.tag
            if tag == w("r"):
                self.run(c, out)
            elif tag in (w("pPr"), w("rPr"), w("del"), w("moveFrom")):
                continue
            elif tag in (f"{{{M}}}oMath", f"{{{M}}}oMathPara"):
                if self.visible():
                    out.append(("".join(t.text or "" for t in c.iter(f"{{{M}}}t")), False))
            else:   # hyperlink · ins · smartTag · fldSimple · sdt · customXml
                self.inline(c, out)

    @staticmethod
    def render(segs, fmt_ok=True):
        """(텍스트, 서식) 조각을 이어 붙인다. 같은 서식끼리 먼저 합쳐 ** 가 쪼개지지 않게 한다."""
        merged = []
        for text, fmt in segs:
            if merged and merged[-1][1] == fmt and fmt != "raw":
                merged[-1] = (merged[-1][0] + text, fmt)
            else:
                merged.append((text, fmt))
        out = []
        for text, fmt in merged:
            if fmt == "raw" or not fmt_ok or not text.strip():
                out.append(text)
                continue
            if not fmt:
                out.append(text)
                continue
            core = text.strip()
            lead = text[:len(text) - len(text.lstrip())]
            trail = text[len(text.rstrip()):]
            core = core.replace("*", "\\*")
            out.append(f"{lead}**{core}**{trail}")
        # 공백만 끼고 이어진 굵게 조각은 하나로 합친다: **6.1** **General** -> **6.1 General**
        return re.sub(r"\*\*(\s+)\*\*", r"\1", "".join(out))

    # ---- 블록 -----------------------------------------------------------
    def style(self, p):
        ps = p.find(f"{w('pPr')}/{w('pStyle')}")
        sid = ps.get(w("val")) if ps is not None else "Normal"
        return self.styles.get(sid, sid.lower())

    def para(self, p, blocks, in_cell=False):
        name = self.style(p)
        segs = []
        self.inline(p, segs)
        if name.startswith("toc"):
            return
        if name == "pl":
            text = "".join(t for t, _ in segs).replace("\n", " ")
            blocks.append(("code", text.rstrip()))
            return
        m = HEADING.fullmatch(name)
        level = int(m.group(1)) if m else (6 if name == "h6" else 0)
        if level:
            text = re.sub(r"\s+", " ", "".join(t for t, f in segs if f != "raw")).strip()
            if text:
                blocks.append(("text", "#" * (1 if level >= 8 else min(level, 6)) + " " + text))
            return
        text = self.render(segs, fmt_ok=not name.startswith("z"))
        if name in ("no", "ex", "ew", "nw") or "editor" in name:
            text = re.sub(r"\t+", "\t", re.sub(r"[ \u00a0]+", " ", text))
        else:
            text = re.sub(r"[ \t\u00a0]+", " ", text)
        text = text.strip()
        if not text:
            return
        hard = "<br>" if in_cell else "\\\n"
        text = re.sub(r"[ \t]*\n[ \t]*", hard, text)
        if name in ("th", "tf"):
            text = "**" + text.replace("**", "") + "**"
        elif name == "no" or "editor" in name:
            text = "> " + text.replace("\\\n", "\\\n> ")
        else:
            b = BULLET.fullmatch(name)
            if b:
                mk = MARKER.match(text)
                if mk:
                    text = "  " * (int(b.group(1)) - 1) + "- " + text[mk.end():]
        blocks.append(("text", text))

    def cell_text(self, tc):
        sub = []
        for c in tc:
            if c.tag == w("p"):
                self.para(c, sub, in_cell=True)
            elif c.tag == w("tbl"):
                for row in self.rows(c):
                    sub.append(("text", " ".join(x for x in row if x)))
            elif c.tag == w("sdt"):
                for p in c.iter(w("p")):
                    self.para(p, sub, in_cell=True)
        parts = [t.replace("\t", " ") for _, t in sub if t]
        return "<br>".join(parts).replace("|", "\\|")

    def rows(self, tbl):
        out = []
        for tr in kids(tbl, "tr"):
            row = []
            for tc in kids(tr, "tc"):
                pr = tc.find(w("tcPr"))
                span, cont = 1, False
                if pr is not None:
                    gs = pr.find(w("gridSpan"))
                    if gs is not None:
                        span = int(gs.get(w("val"), "1"))
                    vm = pr.find(w("vMerge"))
                    cont = vm is not None and vm.get(w("val"), "continue") == "continue"
                row.append("" if cont else self.cell_text(tc))
                row.extend([""] * (span - 1))
            out.append(row)
        return out

    def table(self, tbl, blocks):
        rows = self.rows(tbl)
        ncol = max((len(r) for r in rows), default=0)
        if ncol <= 1:
            # 한 칸짜리 표는 코드 · 그림 상자로 쓰인다 - 표로 만들지 않고 내용을 블록으로 푼다
            for tr in kids(tbl, "tr"):
                for tc in kids(tr, "tc"):
                    self.blocks(tc, blocks)
            return
        rows = [r + [""] * (ncol - len(r)) for r in rows]
        lines = ["| " + " | ".join(rows[0]) + " |",
                 "|" + " --- |" * ncol]
        lines += ["| " + " | ".join(r) + " |" for r in rows[1:]]
        blocks.append(("text", "\n".join(lines)))

    def blocks(self, parent, blocks):
        for c in parent:
            if c.tag == w("p"):
                self.para(c, blocks)
            elif c.tag == w("tbl"):
                self.table(c, blocks)
            elif c.tag in (w("sdt"), w("sdtContent"), w("customXml")):
                self.blocks(c, blocks)

    def convert(self):
        body = ET.fromstring(self.z.read("word/document.xml")).find(w("body"))
        blocks = []
        self.blocks(body, blocks)
        out, code = [], []
        for kind, text in blocks + [("end", "")]:
            if kind == "code":
                code.append(text)
                continue
            if code:
                while code and not code[-1].strip():
                    code.pop()
                if code:
                    out.append("```\n" + "\n".join(code) + "\n```")
                code = []
            if kind == "text":
                out.append(text)
        return "\n\n".join(out) + "\n"


def yaml_str(s):
    return '"' + (s or "").replace("\\", "\\\\").replace('"', '\\"') + '"'


def convert_one(e, force):
    d = spec_dir(e)
    doc, code = main_doc(d, e["spec"])
    if doc is None:
        return "MISSING", "본문 없음 (fetch 먼저)"
    if doc.suffix.lower() == ".doc":
        return "DOC", doc.name
    md = d / f"{doc.stem}.md"
    if md.exists() and not force and md.stat().st_mtime >= doc.stat().st_mtime:
        return "SKIP", md.name
    c = cover(doc)
    _, url = zip_url(e["spec"], code)
    with zipfile.ZipFile(doc) as z:
        conv = Converter(z, d)
        body = conv.convert()
    kind = (c["kind"] or e["kind"]).upper()
    head = ["---",
            f"spec: {yaml_str(kind + ' ' + e['spec'])}",
            f"title: {yaml_str(c['title'])}",
            f"version: {yaml_str(c['ver'])}",
            f"release: {c['release'] if c['release'] is not None else 'null'}",
            f"date: {yaml_str(c['date'])}",
            f"source: {yaml_str(url)}",
            f"converted_from: {yaml_str(doc.name)}",
            "---", ""]
    md.write_text("\n".join(head) + body, encoding="utf-8", newline="\n")
    return "MD", f"{md.name} ({md.stat().st_size / 1e6:.1f} MB, 그림 {len(conv.media)})"


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    force = "--force" in sys.argv
    specs = [e for e in load_specs() if not args or e["spec"] in args]
    res = []
    for e in specs:
        try:
            st, msg = convert_one(e, force)
        except Exception as exc:  # noqa: BLE001
            st, msg = "FAIL", f"{type(exc).__name__}: {str(exc)[:100]}"
        res.append((e["spec"], st, msg))
        print(f"{st:7s} {e['spec']:12s} {msg}", flush=True)
    print("\n===== 요약 =====")
    for st in ("MD", "SKIP", "DOC", "MISSING", "FAIL"):
        n = [r for r in res if r[1] == st]
        if n:
            print(f"{st}: {len(n)}건" + (" - " + ", ".join(r[0] for r in n)
                                        if st in ("DOC", "MISSING", "FAIL") else ""))


if __name__ == "__main__":
    main()
