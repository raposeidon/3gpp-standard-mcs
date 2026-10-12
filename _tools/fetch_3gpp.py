"""specs.json 의 규격마다 3GPP 아카이브에서 최신 zip 을 받아 서비스 폴더에 푼다.

사용: python fetch_3gpp.py [규격번호 ...] [--dry-run]
규격번호를 주면 그것만 받는다. 받은 zip 은 메모리에서 풀고 디스크에 남기지 않는다.
같은 판의 본문이 이미 풀려 있으면 받지 않는다. 이전 실행이 남긴 아카이브 zip 은 지운다.
"""
import concurrent.futures as cf
import io
import re
import sys
import zipfile

from common import (ROOT, archive_dir_url, doc_code, fetch, load_specs, main_doc, spec_dir,
                    stem_of, ver_key, zip_url)


def latest_code(spec):
    """디렉토리 목록에서 최신 버전 코드를 고른다."""
    url = archive_dir_url(spec)
    html = fetch(url).decode("utf-8", "replace")
    pat = re.compile(rf"\b{re.escape(stem_of(spec))}-([0-9a-zA-Z]{{2,4}})\.zip\b")
    cands = {m.group(1).lower() for m in pat.finditer(html)}
    if not cands:
        raise RuntimeError(f"zip 없음: {url}")
    # 버전 문자열은 자릿수가 같아야 비교가 성립한다. 가장 긴 길이만 남긴다.
    maxlen = max(len(c) for c in cands)
    return max((c for c in cands if len(c) == maxlen), key=ver_key)


def leftover_zips(out_dir, spec, members):
    """이전 실행이 받아 둔 아카이브 zip 을 고른다.

    이름이 <번호>-<버전>.zip 이고 안에 본문(doc · docx)이 든 것만 해당한다. 방금 푼
    아카이브에 같은 이름의 파일이 들어 있었으면 그것은 동봉 파일이므로 남긴다.
    """
    pat = re.compile(rf"{re.escape(stem_of(spec))}-[0-9a-z]{{2,4}}\.zip", re.I)
    out = []
    for p in sorted(out_dir.iterdir()):
        if not p.is_file() or not pat.fullmatch(p.name) or p.name in members:
            continue
        try:
            with zipfile.ZipFile(p) as z:
                if any(n.lower().endswith((".doc", ".docx")) for n in z.namelist()):
                    out.append(p)
        except zipfile.BadZipFile:
            continue
    return out


def older_docs(out_dir, spec, code):
    return sorted(p.name for p in out_dir.iterdir()
                  if (c := doc_code(p.name, spec)) and c != code)


def handle(e, dry):
    spec = e["spec"]
    try:
        code = latest_code(spec)
    except Exception as exc:  # noqa: BLE001
        return (spec, "LIST-FAIL", str(exc)[:120], 0)
    name, url = zip_url(spec, code)
    out_dir = spec_dir(e)
    _, have = main_doc(out_dir, spec)
    if dry:
        state = "있음" if have == code else (f"새 판, 로컬 {have}" if have else "새로 받음")
        return (spec, "DRY", f"{name} ({state})", 0)
    out_dir.mkdir(parents=True, exist_ok=True)
    members, size = set(), 0
    if have == code:
        status = "SKIP"
    else:
        try:
            data = fetch(url, timeout=600)
        except Exception as exc:  # noqa: BLE001
            return (spec, "DL-FAIL", str(exc)[:120], 0)
        size = len(data)
        try:
            with zipfile.ZipFile(io.BytesIO(data)) as zf:
                members = set(zf.namelist())
                zf.extractall(out_dir)
        except Exception as exc:  # noqa: BLE001
            return (spec, "UNZIP-FAIL", f"{name}: {str(exc)[:80]}", size)
        status = "GET"
    notes = []
    removed = leftover_zips(out_dir, spec, members)
    for p in removed:
        p.unlink()
    if removed:
        notes.append(f"남은 zip 삭제: {', '.join(p.name for p in removed)}")
    older = older_docs(out_dir, spec, code)
    if older:
        notes.append(f"이전 판 본문 남음: {', '.join(older)}")
    if e.get("attach_from"):
        try:
            got, n = attach_from(e, out_dir)
        except Exception as exc:  # noqa: BLE001
            return (spec, "ATTACH-FAIL", f"{e['attach_from']}: {str(exc)[:100]}", size)
        size += n
        if got:
            notes.append(f"동봉 파일 {len(got)}개를 {e['attach_from']} zip 에서 가져옴")
    return (spec, status, " / ".join([name] + notes), size)


def attach_from(e, out_dir):
    """최신 zip 에 동봉 파일이 빠진 규격은 specs.json 의 attach_from 판 zip 에서 채운다.

    24.483 k10 zip 처럼 본문은 "XML 로 동봉한다" 고 적으면서 zip 에는 docx 만 든 판이
    있다. 폴더에 본문 · 변환본 말고 아무 파일도 없을 때만 받으며, 그 판의 본문은 풀지 않는다.
    """
    spec = e["spec"]
    def is_doc(n):
        return doc_code(n.rsplit("/", 1)[-1], spec) is not None
    present = [p for p in out_dir.iterdir()
               if p.is_file() and p.suffix.lower() != ".md" and not is_doc(p.name)]
    if present:
        return [], 0
    _, url = zip_url(spec, e["attach_from"])
    data = fetch(url, timeout=600)
    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        names = [n for n in zf.namelist() if not n.endswith("/") and not is_doc(n)]
        for n in names:
            zf.extract(n, out_dir)
    return names, len(data)


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    dry = "--dry-run" in sys.argv
    specs = [e for e in load_specs() if not args or e["spec"] in args]
    print(f"대상 {len(specs)}건 -> {ROOT}")
    results = []
    with cf.ThreadPoolExecutor(max_workers=4) as ex:
        for r in ex.map(lambda e: handle(e, dry), specs):
            results.append(r)
            print(f"[{len(results):2d}/{len(specs)}] {r[1]:10s} {r[0]:12s} "
                  f"{r[3] / 1e6:7.1f}MB  {r[2]}", flush=True)

    print("\n===== 요약 =====")
    for st in ("GET", "SKIP", "DRY", "LIST-FAIL", "DL-FAIL", "UNZIP-FAIL", "ATTACH-FAIL"):
        rows = [r for r in results if r[1] == st]
        if rows:
            print(f"{st}: {len(rows)}건")
            if st.endswith("FAIL"):
                for r in rows:
                    print(f"   - {r[0]}: {r[2]}")
    print(f"받은 용량(zip): {sum(r[3] for r in results) / 1e6:.1f} MB")


if __name__ == "__main__":
    main()
