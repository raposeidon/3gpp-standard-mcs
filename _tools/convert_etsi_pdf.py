"""ETSI 규격 PDF 를 Markdown 으로 바꾼다 - 3GPP 원문(docx)이 아닌 ETSI TS 103 564 용.

사용: python _tools/convert_etsi_pdf.py <PDF> [출력 md]
  예: python _tools/convert_etsi_pdf.py D:/somewhere/ts_103564v010601p.pdf
  출력 md 를 주지 않으면 09-conformance/etsi-ts-<번호>/<PDF 이름>.md 에 쓴다.
  PDF 는 ETSI 배포 주소(https://www.etsi.org/deliver/...)에서 받고 저장소에 넣지 않는다
  (.gitignore 허용 목록에 09-conformance 가 없다).

pdfplumber(MIT, pdfminer.six 기반)가 필요하다 - 없으면 `python -m pip install pdfplumber`.
2026-10-21 변환은 pdfplumber 0.11.10 · pdfminer.six 20260107 · Python 3.14 로 했다.

ETSI 규격 PDF 는 글꼴로 구조를 나눈다. 이 도구는 그 글꼴만 보고 Markdown 으로 옮긴다.
  Helvetica 11pt 이상      절 제목 - 절 번호의 깊이가 헤딩 단계 (Annex 는 1단계)
  Helvetica-Bold 9 · Helvetica 10   표 · 그림 제목, 「Message Details」 같은 소제목 -> 굵게
  Courier                  메시지 예시 -> 코드 블록 (x 위치로 들여쓰기 복원)
  Times-Roman              본문 (글머리 • 는 "- " 로)
  그림                     6pt 미만 · 8.5pt 미만 Helvetica · 본문에 없는 글꼴의 글자와 이미지 -> 버리고 쪽마다
                           "[그림 생략 - 원문 PDF p.N]" 한 줄 (그림은 넣지 않는다)
  선으로 그은 표           Helvetica 9pt 가 60% 이상인 것만 Markdown 표 (칸 안 줄바꿈은 <br>,
                           쪽을 넘는 표는 쪽마다 따로). Test Sequence 처럼 가로선 없이 단계 여럿이
                           한 칸에 든 행은 단계 번호의 높이로 행을 나눈다
쪽 머리(쪽 번호 · 규격 번호)와 꼬리(ETSI), 목차 쪽은 버린다.
"""
import hashlib
import io
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent  # 저장소 루트

TINY = 6.0          # pt. 이보다 작은 글자는 그림 안의 글자다 (ETSI 시퀀스 그림은 2 ~ 3pt)
HEADING_MIN = 11.0  # pt. Helvetica 이 크기 이상이 절 제목
CLAUSE = re.compile(r"^(Annex [A-Z]\b|[A-Z](?:\.\d+)+|\d+(?:\.\d+)*)(?=\s)")
BODY_FONTS = ("Times", "Courier", "Helvetica", "Arial", "Symbol", "Wingdings")
UNNUMBERED = ("Foreword", "Intellectual Property Rights", "Modal verbs terminology", "History",
              "Contents")
CHAR_MAP = {"\uf0b7": "•", "\uf0a7": "▪", "\uf0e0": "→", "\uf0de": "⇒", "\ufb01": "fi",
            "\ufb02": "fl", "\u00a0": " "}


def clean(s):
    for a, b in CHAR_MAP.items():
        s = s.replace(a, b)
    return s


def dominant_font(chars):
    count = {}
    for c in chars:
        key = (c["fontname"], round(c["size"], 1))
        count[key] = count.get(key, 0) + 1
    return max(count, key=count.get) if count else ("", 0.0)


def is_heading_font(font):
    name, size = font
    return name.split("+")[-1] == "Helvetica" and size >= HEADING_MIN


def heading_level(text):
    m = CLAUSE.match(text)
    if not m:
        return 1
    num = m.group(1)
    if num.startswith("Annex"):
        return 1
    return min(6, num.count(".") + 1)


def md_cell(text):
    if text is None:
        return ""
    text = clean(text).strip()
    return re.sub(r"\s*\n\s*", "<br>", text).replace("|", "\\|")


def md_table(rows):
    width = max(len(r) for r in rows)
    rows = [[md_cell(c) for c in r] + [""] * (width - len(r)) for r in rows]
    out = ["| " + " | ".join(rows[0]) + " |", "|" + " --- |" * width]
    out += ["| " + " | ".join(r) + " |" for r in rows[1:]]
    return out


def base_font(c):
    return c["fontname"].split("+")[-1]


def is_table_char(c):
    """ETSI 표 글꼴(TAL · TAH 스타일)은 Helvetica 9pt 다."""
    return base_font(c).startswith(("Helvetica", "Arial")) and 8.5 <= c["size"] <= 9.5


def is_figure_char(c):
    """그림 안의 글자 - 6pt 미만, 본문에 쓰지 않는 글꼴, 8.5pt 미만 Helvetica (그림 상자 글자)."""
    name = base_font(c)
    if c["size"] < TINY or not name.startswith(BODY_FONTS):
        return True
    return name.startswith(("Helvetica", "Arial")) and c["size"] < 8.5


def in_box(obj, box):
    x0, top, x1, bottom = box
    cx, cy = (obj["x0"] + obj["x1"]) / 2, (obj["top"] + obj["bottom"]) / 2
    return x0 <= cx <= x1 and top <= cy <= bottom


def in_any(obj, boxes):
    return any(in_box(obj, b) for b in boxes)


def real_tables(page):
    """선으로 그은 표 중 표 글꼴이 대부분인 것만 - 그림의 상자 · 테두리를 표로 잡지 않게."""
    found = []
    for t in page.find_tables():
        inside = [c for c in page.chars if in_box(c, t.bbox)]
        if inside and sum(1 for c in inside if is_table_char(c)) >= 0.6 * len(inside):
            found.append(t)
    return found


def cell_lines(page, bbox):
    if bbox is None:
        return []
    crop = page.crop(bbox, strict=False)
    return [(ln["top"], clean(ln["text"]).strip()) for ln in crop.extract_text_lines()]


STEP = re.compile(r"\d+[a-z]?")


def table_rows(page, table):
    """칸별 글자. 가로선 없이 여러 단계가 한 칸에 든 Test Sequence 는 단계 번호의 높이로 행을 나눈다."""
    out = []
    for row in table.rows:
        cells = [cell_lines(page, b) for b in row.cells]
        steps = next((col for col in cells
                      if len(col) >= 2 and all(STEP.fullmatch(s) for _, s in col)), None)
        if steps is None:
            out.append(["\n".join(s for _, s in col) for col in cells])
            continue
        tops = [tp for tp, _ in steps]
        for k in range(len(tops)):
            lo = tops[k] - 2 if k else float("-inf")
            hi = tops[k + 1] - 2 if k + 1 < len(tops) else float("inf")
            out.append(["\n".join(s for tp, s in col if lo <= tp < hi) for col in cells])
    return out


def page_blocks(page, pno):
    """(top, kind, payload) 목록 - kind 는 line · table · figure."""
    tables = real_tables(page)
    boxes = [t.bbox for t in tables]
    blocks = [(t.bbox[1], "table", table_rows(page, t)) for t in tables]
    figure = [c for c in page.chars if is_figure_char(c) and not in_any(c, boxes)] + page.images
    if figure:
        blocks.append((min(c["top"] for c in figure), "figure", pno))
    body = page.filter(lambda o: o.get("object_type") != "char"
                       or not (is_figure_char(o) or in_any(o, boxes)))
    for ln in body.extract_text_lines(return_chars=True):
        font = dominant_font(ln["chars"])
        text = clean(ln["text"]).rstrip()
        bottom_margin = page.height - 40
        if pno > 1 and ln["top"] < 55 and "ETSI TS" in text:          # 쪽 머리 (표지 제외)
            continue
        if ln["top"] > bottom_margin and text == "ETSI":              # 쪽 꼬리
            continue
        blocks.append((ln["top"], "line", (text, font, ln["x0"], ln["top"], ln["bottom"])))
    blocks.sort(key=lambda b: (b[0], b[1] != "table"))
    return blocks


class Writer:
    def __init__(self):
        self.out = []
        self.mode = None          # None · "code" · "heading"
        self.last_bottom = None
        self.last_size = None
        self.code_left = None

    def blank(self):
        if self.out and self.out[-1] != "":
            self.out.append("")

    def close_code(self):
        if self.mode == "code":
            self.out.append("```")
            self.out.append("")
        self.mode = None

    def emit_line(self, text, font, x0, top, bottom):
        name, size = font
        base = name.split("+")[-1]
        gap = None if self.last_bottom is None else top - self.last_bottom
        if base.startswith("Courier"):
            if self.mode != "code":
                self.close_code()
                self.blank()
                self.out.append("```")
                self.mode = "code"
                self.code_left = x0
            indent = max(0, round((x0 - min(self.code_left, x0)) / (size * 0.6)))
            self.out.append(" " * indent + text.replace("```", "'''"))
        elif is_heading_font(font):
            cont = (self.mode == "heading" and gap is not None and gap < size * 0.8
                    and not CLAUSE.match(text))
            if cont:
                self.out[-1] += ("" if self.out[-1].endswith("-") else " ") + text
            else:
                self.close_code()
                self.blank()
                if CLAUSE.match(text) or text in UNNUMBERED:
                    self.out.append("#" * heading_level(text) + " " + text)
                else:
                    self.out.append("**" + text + "**")
                self.mode = "heading"
        else:
            self.close_code()
            if self.mode == "heading":
                self.blank()
            self.mode = None
            if gap is not None and gap > size * 0.9:
                self.blank()
            if base.startswith("Helvetica"):
                text = "**" + text + "**"
            elif text[:1] in "•▪":
                text = "- " + text[1:].lstrip()
            elif text[:1] in "#>":
                text = "\\" + text
            self.out.append(text)
        self.last_bottom, self.last_size = bottom, size

    def emit_table(self, rows):
        self.close_code()
        self.blank()
        self.out += md_table(rows)
        self.out.append("")
        self.mode, self.last_bottom = None, None

    def emit_figure(self, pno):
        self.close_code()
        self.blank()
        self.out.append(f"> [그림 생략 - 원문 PDF p.{pno}]")
        self.out.append("")
        self.mode, self.last_bottom = None, None


def front_matter(pdf, pdf_path, first_text):
    m = re.search(r"ETSI\s+(TS|TR|EN|ES)\s+(\d{3})\s+(\d{3})\s+V(\d+)\.(\d+)\.(\d+)\s+"
                  r"\((\d{4}-\d{2})\)", first_text)
    if not m:
        raise SystemExit("첫 쪽에서 'ETSI TS nnn nnn Vx.y.z (yyyy-mm)' 를 찾지 못했다")
    kind, a, b, v1, v2, v3, date = m.groups()
    num = a + b
    title = (pdf.metadata.get("Title") or "").split(" - ")[-1].replace("TM", "").strip()
    folder = f"{kind.lower()}_{num[:3]}{num[3:]}"
    rng = f"{num[:4]}00_{num[:4]}99"
    ver = f"{int(v1):02d}.{int(v2):02d}.{int(v3):02d}_60"
    url = f"https://www.etsi.org/deliver/etsi_{kind.lower()}/{rng}/{num}/{ver}/{pdf_path.name}"
    digest = hashlib.sha256(pdf_path.read_bytes()).hexdigest()
    lines = ["---", f'spec: "ETSI {kind} {a} {b}"', f'title: "{title}"',
             f'version: "{v1}.{v2}.{v3}"', f'date: "{date}"', f'source: "{url}"',
             f'converted_from: "{pdf_path.name}"', f'sha256: "{digest}"', "---", ""]
    return lines, f"etsi-{kind.lower()}-{a}.{b}", folder


def convert(pdf_path, out_path=None):
    import pdfplumber  # noqa: PLC0415 - 사용법 출력은 pdfplumber 없이도 되게

    with pdfplumber.open(pdf_path) as pdf:
        first = clean(pdf.pages[0].extract_text() or "")
        head, folder, _ = front_matter(pdf, pdf_path, first)
        if out_path is None:
            out_path = ROOT / "09-conformance" / folder / (pdf_path.stem + ".md")
        w = Writer()
        w.out += head
        in_toc = False
        for pno, page in enumerate(pdf.pages, 1):
            blocks = page_blocks(page, pno)
            texts = [b[2][0] for b in blocks if b[1] == "line"]
            if "Contents" in texts[:2]:
                in_toc = True
            if in_toc:
                if "Intellectual Property Rights" not in texts:
                    continue
                in_toc = False
                cut = texts.index("Intellectual Property Rights")
                blocks = [b for b in blocks if b[1] != "line" or b[2][0] in texts[cut:]]
            for _, kind, payload in blocks:
                if kind == "line":
                    w.emit_line(*payload)
                elif kind == "table":
                    w.emit_table(payload)
                else:
                    w.emit_figure(payload)
            w.last_bottom = None
            page.flush_cache()
        w.close_code()
    text = "\n".join(w.out).rstrip() + "\n"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_bytes(text.encode("utf-8"))
    return out_path, len(pdf.pages)


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    pdf_path = Path(sys.argv[1]).resolve()
    out = Path(sys.argv[2]).resolve() if len(sys.argv) > 2 else None
    out, pages = convert(pdf_path, out)
    print(f"{out} 작성 ({out.stat().st_size:,} B, {pages}쪽)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
