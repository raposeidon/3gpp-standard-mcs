"""specs.json 과 로컬에 받아 둔 본문으로 README.md 를 만든다.

원문은 저장소에 없으므로 fetch_3gpp.py 로 받은 뒤 돌린다. 받지 않은 규격은
아카이브 디렉토리 링크와 함께 "미수집" 으로 표에 남는다.
"""
import datetime
import json

from common import (HERE, RFC_MCX, ROOT, archive_dir_url, cover, doc_code, load_min_release,
                    load_release, load_specs, main_doc, spec_dir, zip_url)
from fetch_rfc import EXTRA_RFCS

SECTIONS = [
    ("00-common", "공통 기반 (MCS Common)",
     "네 서비스가 함께 쓰는 요구사항·아키텍처와 CSC 인터페이스 규격이다."),
    ("01-mcptt", "MCPTT", "Push To Talk. Stage 1 · 2 · 3 과 미디어 플레인·코덱이 모두 있다."),
    ("02-mcvideo", "MCVideo", "비디오. 구조는 MCPTT 와 같고 미디어 플레인이 transmission control 이다."),
    ("03-mcdata", "MCData", "SDS · FD · OSM. 미디어 플레인은 MSRP 기반이다."),
    ("04-mcloc", "MCLoc (Rel-19 신규)",
     "Rel-19 에서 독립한 위치 관리 서비스. 전용 규격은 24.283 하나뿐이고 "
     "요구사항·아키텍처는 22.280 · 23.280 의 위치 관리 절에 들어 있다."),
    ("05-security", "보안", "KMS · MIKEY-SAKKE · GMK/PCK/CSK/SPK/MuSiK · SRTP 키 유도."),
    ("06-sip-ims", "SIP · IMS 기반",
     "모든 Stage 3 규격이 \"according to 24.229\" 로 되돌아가는 상위 규격이다."),
    ("07-media-codec", "미디어 · 코덱", "MCX 코덱 규격이 참조하는 미디어 핸들링과 코덱 본체."),
    ("07-media-codec/amr-wb", "AMR-WB 계열", None),
    ("07-media-codec/evs", "EVS 계열", None),
    ("08-interworking", "LMR 연동", "기존 무전(TETRA 등)과의 연동. 실제 현장 경로다."),
    ("09-conformance", "적합성 시험",
     "규격 본문이 모호한 지점을 시험 케이스가 한 가지 동작으로 못 박아 둔 경우가 많아 "
     "IOT 해석 다툼에서 먼저 찾아볼 자료다."),
    ("09-conformance/_draft-empty", "적합성 시험 - 본문 없는 판", None),
]


def extras(d, doc, spec):
    """규격 폴더에서 본문 · 변환본을 뺀 동봉 파일을 요약한다.

    fetch_3gpp 가 남겨 두는 이전 판 본문은 장별 조각이 아니므로 따로 센다.
    """
    olds = {p.stem for p in d.iterdir()
            if p.is_file() and p != doc and doc_code(p.name, spec)}
    skip = {doc.name, doc.stem + ".md"} | {s + ".md" for s in olds}
    names = [p.name for p in sorted(d.iterdir()) if p.is_file() and p.name not in skip]
    older = [n for n in names if doc_code(n, spec)]
    names = [n for n in names if n not in older]
    if not names and not older:
        return "", []
    zips = [n for n in names if n.lower().endswith(".zip")]
    xsd = [n for n in names if n.lower().endswith(".xsd")]
    xml = [n for n in names if n.lower().endswith(".xml")]
    yml = [n for n in names if n.lower().endswith((".yaml", ".yml"))]
    parts = [n for n in names if n.lower().endswith((".doc", ".docx"))]
    bits = []
    for lst, label in ((zips, "zip"), (xsd, "XSD"), (xml, "XML"), (yml, "OpenAPI")):
        if lst:
            bits.append(f"{label} {len(lst)}종" if len(lst) > 1 else lst[0])
    if parts:
        bits.append(f"본문 조각 {len(parts)}건")
    if older:
        bits.append(f"이전 판 본문 {len(older)}건")
    rest = len(names) - len(zips) - len(xsd) - len(xml) - len(yml) - len(parts)
    if rest:
        bits.append(f"기타 {rest}건")
    return "동봉: " + " · ".join(bits), parts


def collect():
    rows = []
    for e in load_specs():
        d = spec_dir(e)
        doc, code = main_doc(d, e["spec"], e, load_release())
        r = {"e": e, "doc": doc, "code": code, "meta": None, "parts": [],
             "md": bool(doc) and (d / f"{doc.stem}.md").exists()}
        if doc:
            r["meta"] = cover(doc)
            r["extras"], r["parts"] = extras(d, doc, e["spec"])
        rows.append(r)
    return rows


def table(rows):
    out = ["| 원문 (zip) | 표준 | 공식 명칭 | 버전 | 비고 |",
           "| --- | --- | --- | --- | --- |"]
    for r in sorted(rows, key=lambda x: x["e"]["spec"]):
        e, m = r["e"], r["meta"]
        kind = e["kind"].upper()
        if m is None:
            out.append(f"| [미수집]({archive_dir_url(e['spec'])}) | {kind} {e['spec']} "
                       f"| | | fetch 전 |")
            continue
        notes = [e.get("note", "")]
        if m["ver"] == "0.0.1":
            notes.append("본문 없음 - 착수만 된 판")
        if r["doc"].suffix.lower() == ".doc":
            notes.append(".doc 원문 (임시 docx 로 바꿔 md 변환)" if r["md"]
                         else "**.doc 원문 그대로 (md 변환 안 함)**")
        if r["parts"] and e.get("parts"):
            notes.append(f"**본문이 장별 조각으로 나뉨 - "
                         f"{' · '.join('Annex ' + p.upper() for p in e['parts'])} 조각만 md 변환(`parts`)**")
        elif r["parts"]:
            notes.append(f"**본문이 장별 조각으로 나뉨 - 조각 {len(r['parts'])}건은 md 변환 안 함**")
        notes.append(r["extras"])
        name, url = zip_url(e["spec"], r["code"])
        out.append(f"| [{name}]({url}) | {(m['kind'] or kind)} {e['spec']} | {e.get('title') or m['title']} | "
                   f"v{m['ver']} (Rel-{m['release']}, {m['date']}) | "
                   f"{' / '.join(n for n in notes if n)} |")
    return "\n".join(out)


def main():
    rows = collect()
    by_sec = {}
    for r in rows:
        by_sec.setdefault(r["e"]["dir"], []).append(r)
    got = [r for r in rows if r["doc"]]
    docs = sorted(r["e"]["spec"] for r in got
                  if r["doc"].suffix.lower() == ".doc" and not r["md"])
    parts = sorted(r["e"]["spec"] for r in got if r["parts"])
    today = datetime.date.today().isoformat()
    n_rfc = len(json.loads((HERE / "rfc_plan.json").read_text(encoding="utf-8")))

    L = []
    L.append("# 3GPP MCX 표준 수집 · Markdown 변환 도구\n")
    L.append("Mission Critical 계열 3GPP 규격을 **3GPP 아카이브에서 받아 서비스별 폴더에 풀고 "
             "Markdown 으로 변환**하는 스크립트와 그 대상 목록이다. **판 선택 규칙**: "
             "`_tools/specs.json` 항목에 `\"version\"` 이 있으면 그 판, 없으면 "
             "**규격마다 그 시점의 최신 판**이다. 다만 `_tools/release.json` 의 `min_release`"
             f"(Rel-{load_min_release()}) 미만 판은 받지 않는다. 그래서 그 릴리스부터 최신 릴리스까지 "
             "섞이며, 이는 의도한 것이다.\n")
    L.append("**3GPP · ITU-T 원문과 그 변환본(md)은 이 저장소에 없다.** 두 기관 모두 서면 허가 "
             "없는 복제를 금지하므로, 스크립트를 돌려 각자 로컬에 받는다. IETF RFC 는 IETF Trust "
             "Legal Provisions 가 수정 없는 전문 배포를 허용하므로 `10-ietf-rfc/` 에 원문 그대로 "
             "넣어 두었다. `11-openid/` 의 OpenID Connect Core 1.0 도 OpenID Foundation 이 구현 "
             "목적의 복제 · 배포를 허락하므로 원문 그대로 넣었다. ETSI 원문과 변환본은 3GPP 와 "
             "같은 이유로 저장소에 없다.\n")
    L.append(f"- 대상: 3GPP {len(rows)}건 (`_tools/specs.json`) + ITU-T 2건 + ETSI 1건 + "
             f"IETF RFC {n_rfc}종(본체 인용 {n_rfc - len(EXTRA_RFCS)} + 근거 {len(EXTRA_RFCS)})")
    L.append(f"- 아래 표의 버전: {today} 에 로컬에 받아 둔 판 기준 "
             f"({len(got)}/{len(rows)}건). 다시 받으면 더 새 판이 나올 수 있다 (`version` 으로 고정한 규격 제외).")
    L.append("- 출처: <https://www.3gpp.org/ftp/Specs/archive/> · <https://www.itu.int/rec/> · "
             "<https://www.etsi.org/deliver/>\n")

    L.append("## 사용법\n")
    L.append("Python 3 표준 라이브러리만 쓴다. 저장소 루트에서 돌린다. 구형 .doc 본문을 "
             "변환할 때만 LibreOffice 나 Word(Windows) 가 있으면 쓴다 (아래 제약 참조). "
             "그린 PNG 를 줄이는 데 Pillow 를 쓰며, 없으면 `convert_md.py` 가 pip 로 설치한다.\n")
    L.append("```")
    L.append("python _tools/fetch_3gpp.py --dry-run   # 받을 판과 지금 변환본 비교 (받지 않음)")
    L.append("python _tools/fetch_3gpp.py             # 최신(또는 고정) 판 zip 을 받아 서비스 폴더에 풀기 (zip 은 남기지 않음)")
    L.append("python _tools/convert_md.py             # 본문 docx -> md (이미 변환한 것은 건너뜀)")
    L.append("python _tools/gen_readme.py             # 이 README 재생성")
    L.append("```\n")
    L.append("규격번호를 인자로 주면 그것만 처리한다 (`python _tools/convert_md.py 24.380`). "
             "`convert_md.py --force` 는 이미 변환한 것도 다시 만든다. 이미 변환한 규격에 PNG 를 "
             "붙이려면 `--force` 로 한 번 다시 돌린다. 대상 규격을 늘리거나 "
             "옮길 때는 `_tools/specs.json` 만 고친다 - 받기 · 변환 · README 가 모두 이 목록을 읽는다. "
             "최신 zip 에 동봉 파일이 빠진 판은 그 항목에 `\"attach_from\": \"k00\"` 처럼 "
             "동봉 파일을 가져올 판을 적는다 (폴더에 동봉 파일이 없을 때만 그 판 zip 을 받는다).\n")
    L.append("판을 고정할 때: `specs.json` 그 항목에 `\"version\": \"k20\"` 처럼 판 코드를 적는다. "
             "고정한 판이 아카이브에 없으면 받지 않고 오류로 남긴다. 고정한 판은 `min_release` "
             "미만이어도 받는다. 판 코드 첫 자리가 0 ~ 2 인 승인 전 초안(`_draft-empty/` 의 v0.0.1 등)은 "
             "릴리스를 나타내지 않아 하한을 적용하지 않는다. 고정하지 않은 규격에 `min_release` 이상 판이 없으면 `BELOW-MIN` "
             "으로 건너뛴다. 모든 규격을 특정 릴리스 판 "
             "우선으로 받으려면 `release.json` 의 `target_release` 에 릴리스 번호를 적고(기본 "
             "`null` - 최신), 한 번만 그렇게 받으려면 `--release=N` 을 준다.\n")
    L.append("클론한 뒤 `git config core.hooksPath _tools/hooks` 를 한 번 실행한다. "
             "`.gitignore` 가 제외하는 파일(원문 · 변환본)이 `git add -f` 로 스테이징되면 "
             "pre-commit 훅이 커밋을 거부한다.\n")

    L.append("## 폴더 구조\n")
    L.append("저장소에는 `10-ietf-rfc/` · `11-openid/` · `_tools/` 만 들어 있다. 나머지는 스크립트가 원문을 "
             "받아 채우는 자리다. `.gitignore` 는 허용 목록 방식이라 `specs.json` 에 새 서비스 "
             "폴더가 생겨도 추적되지 않는다.\n")
    L.append("```")
    L.append("00-common        MCS 공통 (요구사항 · 아키텍처 · CSC 인터페이스)")
    L.append("01-mcptt         MCPTT")
    L.append("02-mcvideo       MCVideo")
    L.append("03-mcdata        MCData")
    L.append("04-mcloc         MCLoc (Rel-19 신규)")
    L.append("05-security      보안")
    L.append("06-sip-ims       SIP · IMS 기반")
    L.append("07-media-codec   미디어 · 코덱")
    L.append("   amr-wb/       AMR-WB 계열")
    L.append("   evs/          EVS 계열")
    L.append("   itu-t/        ITU-T 권고 (AVC · HEVC, 수동으로 받는다)")
    L.append("08-interworking  LMR 연동")
    L.append("09-conformance   적합성 시험")
    L.append("   _draft-empty/ 본문 없는 v0.0.1 판")
    L.append("   etsi-ts-103.564/ ETSI Plugtests 시나리오 (PDF 에서 변환, 수동으로 받는다)")
    L.append("10-ietf-rfc      IETF RFC 최소 집합 (영역별, 저장소에 포함)")
    L.append("11-openid        IETF 가 아닌 근거 문서 - OpenID Connect Core 1.0 (저장소에 포함)")
    L.append("_tools           수집 · 변환 · 생성 스크립트 (저장소에 포함)")
    L.append("```\n")
    L.append("규격 하나는 `<서비스>/<ts|tr>-<번호>/` 에 들어간다. 아카이브 zip 은 메모리에서 "
             "풀고 남기지 않으므로 폴더에는 본문(`24380-k00.docx` 등)과 동봉 파일이 남고, 그 옆에 "
             "변환본 `24380-k00.md` 와 그림 폴더 `media/` 가 생긴다. 같은 판의 본문이 이미 있으면 "
             "다시 받지 않는다.\n")

    L.append("## Markdown 변환의 제약\n")
    L.append("`convert_md.py` 는 docx 의 XML 을 직접 읽어 3GPP 스타일 이름(Heading · B1 ~ B5 · PL · "
             "NO · TH · TOC 등)으로 구조를 구분한다. 외부 변환기를 쓰지 않는 대신 다음 제약이 있다.\n")
    L.append("- **.doc 본문은 LibreOffice 나 Word 가 있을 때만 변환된다.** 구형 Word 바이너리(OLE)라 "
             "표준 라이브러리로 읽을 수 없어, `convert_md.py` 가 `soffice` 를 찾으면 그것으로, "
             "없으면 Windows 의 Word 로 임시 docx 를 만들어 변환한다. 둘 다 없으면 원문 그대로 "
             f"둔다. 지금 변환되지 않은 것은 {len(docs)}건이다"
             + (": " + " · ".join(docs) if docs else "") + ".")
    if parts:
        L.append(f"- **본문이 장별 파일로 나뉜 규격은 표지 docx 만 변환된다.** {' · '.join(parts)} "
                 "가 해당하며, 나머지 조각(대부분 .doc)은 원문 그대로 남는다. `specs.json` 항목에 "
                 "`\"parts\": [\"a\"]` 처럼 파트 표지를 적으면 그 조각도 `<조각 이름>.md` 로 변환한다 "
                 "(26.445 는 코덱 알고리즘 본문의 수식 그림이 수천 개라 Annex A 만 적었다).")
    L.append("- **EMF · WMF 그림은 PNG 를 함께 만든다.** 3GPP 그림은 대부분 EMF · WMF 라 Markdown "
             "뷰어가 그리지 못한다. `media/` 에 원본을 빼낸 뒤 Windows 는 GDI+ 로, 그 밖에는 "
             "Inkscape 가 있으면 그것으로 PNG 를 만들어 md 가 PNG 를 가리키게 한다. 그린 PNG 는 "
             "Pillow 로 32색 팔레트로 줄인다(선 그림이라 눈으로 차이가 없고 크기가 약 40% 가 된다). "
             "둘 다 없거나 그리기에 실패한 그림은 원본 링크로 남는다 (`--no-png` 로 이 단계를 끌 수 있다). "
             "PNG 도 원문에서 나온 것이라 저장소에 올리지 않는다.")
    L.append("- **표의 병합 셀은 펼친다.** Markdown 표에 병합이 없어 가로 병합은 빈 칸으로, 세로 "
             "병합은 첫 행에만 내용을 둔다. 한 칸짜리 표(코드 · 그림 상자)는 표로 만들지 않고 "
             "내용을 본문으로 푼다.")
    L.append("- **글머리 계층은 들여쓰지 않는다.** 3GPP 본문에는 `1)` · `a)` · `-` 같은 표지 문자가 "
             "들어 있어 그대로 남기며, Markdown 에서 4칸 들여쓰기가 코드 블록으로 바뀌는 것을 "
             "막으려고 `-` 글머리만 목록으로 만든다.")
    L.append("- **수식은 텍스트만 남는다.** Office Math 는 기호 문자열로 풀리고 구조(분수 · 첨자)는 "
             "사라진다. 코덱 규격(26.445 등)을 수식 근거로 볼 때는 원문을 연다.")
    L.append("- **목차와 숨김 텍스트는 버린다.** 목차는 쪽 번호만 남고, 변경 추적의 삭제분도 뺀다.\n")

    for key, title, desc in SECTIONS:
        sec = by_sec.get(key, [])
        if not sec:
            continue
        L.append(f"## {title}\n")
        if desc:
            L.append(desc + "\n")
        L.append(table(sec) + "\n")

    L.append("## ETSI 규격 (`09-conformance/etsi-ts-103.564`)\n")
    L.append("ETSI TS 103 564 는 MCX Plugtests(여러 벤더 장비를 실제로 붙여 보는 행사)의 시나리오 모음이다. "
             "동작 근거가 아니라 상호운용 시험 목록으로 쓴다. 3GPP 아카이브에 없어 `fetch_3gpp.py` 가 "
             "받지 않으므로 아래 주소에서 PDF 를 받고, 원문이 PDF 라 `convert_md.py` 가 아니라 "
             "`_tools/convert_etsi_pdf.py`(pdfplumber - `python -m pip install pdfplumber`)로 변환한다.\n")
    L.append("```")
    L.append("python _tools/convert_etsi_pdf.py <받은 PDF>   # -> 09-conformance/etsi-ts-103.564/<PDF 이름>.md")
    L.append("```\n")
    L.append("- 글꼴로 구조를 나눈다. Helvetica 11pt 이상은 절 제목, Courier 는 메시지 예시 코드 블록, "
             "선으로 그은 표 중 Helvetica 9pt 가 60% 이상인 것은 Markdown 표다. 규칙 전체는 도구 머리 "
             "주석에 있다.")
    L.append("- **그림은 넣지 않는다.** 시퀀스 그림의 글자가 2 ~ 3pt 라 텍스트로 읽을 수 없어 버리고 "
             "`> [그림 생략 - 원문 PDF p.N]` 한 줄을 남긴다. 쪽을 넘는 표는 쪽마다 따로 표가 되고, "
             "목차는 버린다.\n")
    L.append("| 원문 (PDF) | 표준 | 공식 명칭 | 버전 | 비고 |")
    L.append("| --- | --- | --- | --- | --- |")
    L.append("| [ts_103564v010601p.pdf](https://www.etsi.org/deliver/etsi_ts/103500_103599/103564/"
             "01.06.01_60/ts_103564v010601p.pdf) | ETSI TS 103 564 | Plugtests scenarios for Mission "
             "Critical Services | V1.6.1 (2024-04) | PDF 원문 (그림은 넣지 않고 쪽 번호만 남긴다) |\n")

    L.append("## ITU-T 권고 (`07-media-codec/itu-t`)\n")
    L.append("HEVC · AVC 는 3GPP 규격이 아니라 ITU-T 권고다. 3GPP 아카이브에 없으므로 "
             "`fetch_3gpp.py` 가 받지 않는다. 26.281 (MCVideo 코덱) 과 26.114 (MTSI 미디어 "
             "핸들링) 가 이 둘을 참조하므로 참조 사슬의 끝에 해당한다. ITU 사이트에서 무료로 받을 "
             "수 있지만 재배포는 허용되지 않는다. 로컬 파일명은 `H.264-V16-202606_AVC.pdf` 처럼 "
             "판과 승인월을 붙인다.\n")
    L.append("| 원문 | 권고 | 공식 명칭 | 판 |")
    L.append("| --- | --- | --- | --- |")
    L.append("| [T-REC-H.264](https://www.itu.int/rec/T-REC-H.264) "
             "| ITU-T H.264 | Advanced video coding for generic audiovisual services "
             "| V16 (2026-06) |")
    L.append("| [T-REC-H.265](https://www.itu.int/rec/T-REC-H.265) "
             "| ITU-T H.265 | High efficiency video coding | V11 (2026-01) |\n")
    L.append("H.266 (VVC) 는 받지 않는다. 26.281 이 H.264 Constrained Baseline 을 필수로, "
             "H.265 를 선택으로 규정하고 VVC 는 대상이 아니기 때문이다.\n")

    L.append("## IETF RFC (`10-ietf-rfc`)\n")
    L.append(f"MCX 본체 규격 {len(RFC_MCX)}건의 References 절에서 실제로 인용된 RFC "
             f"{n_rfc - len(EXTRA_RFCS)}종과, MCX 클라이언트 구현이 근거로 쓰지만 본체가 인용하지 않는 "
             f"RFC {len(EXTRA_RFCS)}종(코덱 페이로드 · SDP 대역폭 · SIP Digest · ARIA SRTP - "
             "`fetch_rfc.py` 의 `EXTRA_RFCS`)을 영역별로 받아 두었다. 목록과 인용 규격 대응은 "
             "[10-ietf-rfc/README.md](10-ietf-rfc/README.md) 에 있다. "
             "26.114 (MTSI) 와 24.229 (IMS) 는 인용 폭이 넓어 그 집합에서 뺐다.\n")

    L.append("## 읽을 때 주의할 점\n")
    L.append("- **릴리스가 규격마다 다르다.** 한 절의 동작을 다른 규격과 대조할 때 "
             "두 문서의 Release 가 같은지 먼저 확인한다.")
    L.append("- **`_draft-empty/` 6건은 본문이 없다.** 제목만 있고 시험 케이스가 들어 있지 않다. "
             "검색 결과에 섞여 나와 실제 시험 규격으로 오인되는 것을 막으려고 분리해 두었다.")
    L.append("- **보안 규격은 33.180 을 본다.** Rel-13 에서 멈춘 TS 33.179(내용이 33.180 으로 이관)와 "
             "TR 33.879(MCPTT 보안 설계 배경)는 최소 릴리스 미만이라 대상에서 뺐다.")
    L.append("- **MCX IWF 프로토콜은 29.379 · 29.380 · 29.582 셋이다.** "
             "29.387 · 29.388 · 29.389 는 V2X, 29.579 는 SMS 연동으로 "
             "번호만 이웃일 뿐이다.")
    L.append("- **위치 관리는 두 군데에 있다.** Rel-19 부터 MCLoc(24.283)이 독립했지만 "
             "서비스별 위치 보고 절(24.379 §13 등)도 그대로 남아 있다.")
    L.append("- **ANSI-C 참조 소스와 TTCN-3 번들은 zip 인 채로 남는다.** `fetch_3gpp.py` 는 "
             "아카이브 zip 을 한 번만 풀고 그 안의 zip 은 풀지 않는다.\n")

    out = ROOT / "README.md"
    out.write_text("\n".join(L), encoding="utf-8", newline="\n")
    missing = [r["e"]["spec"] for r in rows if not r["doc"]]
    print(f"{out} 작성 ({out.stat().st_size:,} B) / 미수집 {len(missing)}건"
          + (": " + " ".join(missing) if missing else ""))


if __name__ == "__main__":
    main()
