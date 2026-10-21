"""규격 목록 · 폴더 배치 · 본문 선택 · 표지 추출 · 내려받기를 스크립트들이 함께 쓴다."""
import json
import re
import time
import urllib.request
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
ARCHIVE = "https://www.3gpp.org/ftp/Specs/archive"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36")

# RFC 인용을 모을 MCX 본체 규격. 코덱 본체 · 시험 규격은 제외한다.
RFC_SPECS = ["24.379", "24.380", "24.281", "24.581", "24.282", "24.582",
             "24.283", "24.481", "24.482", "24.483", "24.484", "24.229",
             "33.180", "26.179", "26.281", "26.114",
             "23.283", "29.379", "29.380", "29.582"]
# 10-ietf-rfc 최소 집합의 근거 규격. 26.114(MTSI) · 24.229(IMS) 는 MCX 전용이 아니라
# 인용 폭이 넓어 빼고, 23.283 · 29.380 은 RFC 를 인용하지 않아 뺀다.
RFC_MCX = [s for s in RFC_SPECS if s not in ("24.229", "26.114", "23.283", "29.380")]


def fetch(url, retries=3, timeout=120):
    last = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read()
        except Exception as exc:  # noqa: BLE001
            last = exc
            time.sleep(2 * (attempt + 1))
    raise last


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


# ---- 판 선택 (release.json) ------------------------------------------------------
# 판 코드의 첫 자리가 릴리스다 (base36: 9 = Rel-9, a = Rel-10 … k = Rel-20, l = Rel-21).
# 규칙: specs.json 항목의 "version" 이 있으면 그 판, 없으면 target_release 판 중 최신,
# 그 릴리스 판이 없으면 전체 최신. min_release 미만 판은 고르지 않는다 (version 고정은 예외).
# 받기(fetch) · 변환(convert) · 목록(gen_readme)이 같은 규칙을 쓴다.

def release_of(code):
    """판 코드 → 릴리스 번호. k20 → 20, j10 → 19."""
    return int(code[0], 36)


def load_release():
    """release.json 의 target_release. 명령줄 --release=N 이 있으면 그것, --latest 면 None."""
    import sys
    for a in sys.argv[1:]:
        if a == "--latest":
            return None
        if a.startswith("--release="):
            return int(a.split("=", 1)[1])
    return json.loads((HERE / "release.json").read_text(encoding="utf-8")).get("target_release")


def load_min_release():
    """release.json 의 min_release. 없거나 null 이면 하한이 없다. 명령줄로 덮지 않는다."""
    return json.loads((HERE / "release.json").read_text(encoding="utf-8")).get("min_release")


def pick_code(codes, entry=None, release=None):
    """판 코드 목록에서 받을 · 쓸 판을 고른다. 고정 판이 목록에 없거나,
    고정하지 않았는데 min_release 이상 판이 없으면 None.

    codes   : 아카이브 목록 또는 로컬 본문에서 모은 판 코드들
    entry   : specs.json 항목 ("version" 이 있으면 그 판으로 고정)
    release : 목표 릴리스 (None 이면 전체 최신)
    """
    codes = {c.lower() for c in codes}
    if not codes:
        return None
    pinned = (entry or {}).get("version")
    if pinned:
        return pinned.lower() if pinned.lower() in codes else None
    # 판 문자열은 자릿수가 같아야 비교가 성립한다. 가장 긴 길이만 남긴다.
    maxlen = max(len(c) for c in codes)
    codes = [c for c in codes if len(c) == maxlen]
    floor = load_min_release()
    if floor is not None:
        # 첫 자리 0 · 1 · 2 는 승인 전 초안(v0.0.1 등)이라 릴리스가 아니다. 하한을 대지 않는다
        codes = [c for c in codes if release_of(c) < 3 or release_of(c) >= floor]
        if not codes:
            return None
    if release is not None:
        same = [c for c in codes if release_of(c) == release]
        if same:
            return max(same, key=ver_key)
    return max(codes, key=ver_key)


def archive_dir_url(spec):
    return f"{ARCHIVE}/{spec[:2]}_series/{spec}/"


def zip_url(spec, code):
    name = f"{stem_of(spec)}-{code}.zip"
    return name, archive_dir_url(spec) + name


def doc_code(name, spec):
    """본문 파일명(<번호>-<버전>.doc/.docx)이면 버전 코드를, 아니면 None 을 돌려준다.

    36.579-9 처럼 파일명에 점이 남은 판본이 있어 점을 지우고 맞춘다.
    장별로 나뉜 조각(26445-j10_1_s05...doc)은 본문으로 보지 않는다.
    """
    stem, _, ext = name.rpartition(".")
    if ext.lower() not in ("doc", "docx"):
        return None
    m = re.fullmatch(rf"{re.escape(stem_of(spec))}-([0-9a-z]{{3}})", stem.replace(".", ""), re.I)
    return m.group(1).lower() if m else None


def main_doc(d, spec, entry=None, release=None):
    """폴더에서 본문을 고른다. 판이 여럿이면 판 선택 규칙(pick_code)으로, 같은 판이면 docx.

    entry · release 를 주지 않으면 규칙 없이 최신 판이다 (예전 동작).
    """
    if not d.is_dir():
        return None, None
    found = {}
    for p in d.iterdir():
        code = doc_code(p.name, spec) if p.is_file() else None
        if not code:
            continue
        if code not in found or p.suffix.lower() == ".docx":
            found[code] = p
    if not found:
        return None, None
    if entry is not None or release is not None:
        code = pick_code(found, entry, release)
    else:
        code = max(found, key=ver_key)
    return (found[code], code) if code in found else (None, None)


# ---- 표지 추출 ----------------------------------------------------------
# docx 는 <w:t> 내용만 이어 붙인다 - 태그를 공백으로 치환하면 Word 가 나눈 run
# 경계에서 낱말이 쪼개져 "c odecs" 같은 깨진 문자열이 나온다.
# doc(OLE 바이너리)는 표지 문자열이 CP1252 로 박혀 있어 ASCII 구간만 긁으면 된다.

# 문단 안의 줄바꿈 · 탭은 공백으로 친다. 빼면 Word 가 .doc 을 docx 로 저장한 표지에서
# "based on<w:br/>Session" 이 "based onSession" 으로 붙는다 (24.229).
WT = re.compile(r"<w:t(?:\s[^>]*)?>(.*?)</w:t>|<w:(?:br|cr|tab)\b[^>]*/>", re.S)
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


def para_text(para):
    return "".join(m.group(1) if m.group(1) is not None else " " for m in WT.finditer(para))


def docx_lines(path):
    with zipfile.ZipFile(path) as z:
        xml = z.read("word/document.xml").decode("utf-8", "replace")
    out = []
    for para in PARA.split(xml)[:300]:
        s = unesc(para_text(para)).strip()
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
