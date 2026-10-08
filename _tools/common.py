"""규격 목록 · 폴더 배치 · 본문 선택 · 표지 추출을 스크립트들이 함께 쓴다."""
import json
import re
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
ARCHIVE = "https://www.3gpp.org/ftp/Specs/archive"


def load_specs():
    """specs.json - 규격번호 · 종류(ts/tr) · 서비스 폴더 · 비고."""
    return json.loads((HERE / "specs.json").read_text(encoding="utf-8"))


def spec_dir(e):
    return ROOT / e["dir"] / f"{e['kind']}-{e['spec']}"


def stem_of(spec):
    """24.379 -> 24379, 36.579-1 -> 36579-1 (아카이브 파일명 앞부분)."""
    return spec.replace(".", "")


def ver_key(v):
    """버전 문자열(예: i80)을 비교 가능한 튜플로. 각 자리는 base36."""
    return tuple(int(c, 36) for c in v)


def archive_dir_url(spec):
    return f"{ARCHIVE}/{spec[:2]}_series/{spec}/"


def zip_url(spec, code):
    name = f"{stem_of(spec)}-{code}.zip"
    return name, archive_dir_url(spec) + name


def main_doc(d, spec):
    """폴더에서 본문(<번호>-<버전>.doc/.docx)을 고른다. 버전이 여럿이면 최신, 같으면 docx.

    36.579-9 처럼 파일명에 점이 남은 판본이 있어 점을 지우고 맞춘다.
    장별로 나뉜 조각(26445-j10_1_s05...doc)은 본문으로 보지 않는다.
    """
    if not d.is_dir():
        return None, None
    pat = re.compile(rf"{re.escape(stem_of(spec))}-([0-9a-z]{{3}})", re.I)
    best = None
    for p in d.iterdir():
        if not p.is_file() or p.suffix.lower() not in (".doc", ".docx"):
            continue
        m = pat.fullmatch(p.stem.replace(".", ""))
        if not m:
            continue
        key = (ver_key(m.group(1).lower()), p.suffix.lower() == ".docx")
        if best is None or key > best[0]:
            best = (key, p, m.group(1).lower())
    return (best[1], best[2]) if best else (None, None)


# ---- 표지 추출 ----------------------------------------------------------
# docx 는 <w:t> 내용만 이어 붙인다 - 태그를 공백으로 치환하면 Word 가 나눈 run
# 경계에서 낱말이 쪼개져 "c odecs" 같은 깨진 문자열이 나온다.
# doc(OLE 바이너리)는 표지 문자열이 CP1252 로 박혀 있어 ASCII 구간만 긁으면 된다.

WT = re.compile(r"<w:t(?:\s[^>]*)?>(.*?)</w:t>", re.S)
PARA = re.compile(r"</w:p>")
HEAD = re.compile(r"3GPP\s+(TS|TR)\s+([\d.]+(?:-\d+)?)\s+V(\d+\.\d+\.\d+)"
                  r"\s*\((\d{4}-\d{2})\)")
TSG = re.compile(r"^Technical Specification Group\b", re.I)
RELLINE = re.compile(r"^\(?\s*Release\s+(\d+)\s*\)?[.;]?$", re.I)
STOP = re.compile(r"^(The present document|This Specification|Specifications and Reports"
                  r"|Keywords|3GPP\b|Postal address)", re.I)


def unesc(s):
    return (s.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
             .replace("&quot;", '"').replace("&apos;", "'"))


def docx_lines(path):
    with zipfile.ZipFile(path) as z:
        xml = z.read("word/document.xml").decode("utf-8", "replace")
    out = []
    for para in PARA.split(xml)[:300]:
        s = unesc("".join(WT.findall(para))).strip()
        if s:
            out.append(s)
        if len(out) > 60:
            break
    return out


def doc_lines(path):
    raw = path.read_bytes()[:400000]
    hits = re.findall(rb"[\x20-\x7e]{12,}", raw)
    return [h.decode("cp1252", "replace").strip() for h in hits][:80]


def parse_cover(lines):
    kind = ver = date = None
    for ln in lines[:12]:
        m = HEAD.search(ln)
        if m:
            kind, _, ver, date = m.groups()
            break
    # 명칭은 "Technical Specification Group ...;" 다음 줄부터 Release 줄 직전까지
    start = next((i for i, ln in enumerate(lines) if TSG.match(ln)), None)
    title, rel = "", None
    if start is not None:
        parts = []
        # 표지가 한 문단으로 뭉친 판본은 TSG 이름 뒤가 곧바로 명칭이다
        head_rest = lines[start].split(";", 1)[1] if ";" in lines[start] else ""
        if head_rest.strip():
            parts.append(head_rest.strip())
        for ln in lines[start + 1:start + 12]:
            m = RELLINE.match(ln)
            if m:
                rel = int(m.group(1))
                break
            if STOP.match(ln) or "EMBED" in ln:
                # 명칭이 시작된 뒤라면 명칭이 끝난 것이다. Release 줄이 없는 판본은
                # 여기서 끊지 않으면 면책 문구까지 명칭에 붙는다 (29.199-09).
                if parts:
                    break
                continue
            parts.append(ln.rstrip())
        title = " ".join(parts)
        # 줄바꿈 없이 붙어 버린 "(Release NN)" 을 떼어 내며 릴리스를 건진다
        m = re.search(r"\(\s*Release\s+(\d+)\s*\)", title, re.I)
        if m:
            rel = rel or int(m.group(1))
            title = title[:m.start()]
        title = re.sub(r"\s+", " ", title).strip(" ;.")
        title = re.sub(r"\s*;\s*", "; ", title)
    if rel is None:
        for ln in lines[:40]:
            m = re.search(r"Release\s+(\d+)", ln)
            if m:
                rel = int(m.group(1))
                break
    if rel is None and ver and int(ver.split(".")[0]) >= 4:
        # Rel-4 부터 판 번호의 첫 자리가 릴리스다. .doc 표지의 "(Release 9)" 는 11자라
        # doc_lines 의 12자 하한에 걸려 빠진다 (29.199-09).
        rel = int(ver.split(".")[0])
    return {"kind": kind, "ver": ver, "date": date, "title": title, "release": rel}


def cover(path):
    lines = docx_lines(path) if path.suffix.lower() == ".docx" else doc_lines(path)
    return parse_cover(lines)
