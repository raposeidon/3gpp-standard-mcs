"""로컬에 받아 둔 MCX 규격의 References 절에서 인용된 IETF RFC 를 모은다."""
import json
import re
import zipfile
from collections import defaultdict

from common import HERE, PARA, RFC_SPECS, load_specs, main_doc, para_text, spec_dir

RFC = re.compile(r"RFC\s*(\d{3,5})", re.I)


def full_text(path):
    if path.suffix.lower() == ".docx":
        with zipfile.ZipFile(path) as z:
            xml = z.read("word/document.xml").decode("utf-8", "replace")
        paras = []
        for para in PARA.split(xml):
            s = para_text(para).strip()
            if s:
                paras.append(s)
        return "\n".join(paras)
    raw = path.read_bytes()
    hits = re.findall(rb"[\x20-\x7e]{8,}", raw)
    return "\n".join(h.decode("cp1252", "replace") for h in hits)


def refs_section(txt):
    """2 References 절만 잘라 낸다. 못 찾으면 앞쪽 일부를 쓴다."""
    m = re.search(r"\n2\s*\t?\s*References?\s*\n", txt, re.I)
    if not m:
        m = re.search(r"\n\s*2\s+References?\s*\n", txt, re.I)
    if not m:
        return txt[:120000]
    start = m.end()
    m2 = re.search(r"\n\s*3\s*\t?\s*(Definitions|Abbreviations)", txt[start:], re.I)
    end = start + (m2.start() if m2 else 150000)
    return txt[start:end]


def main():
    by_rfc = defaultdict(set)
    per_spec = {}
    for e in load_specs():
        spec = e["spec"]
        if spec not in RFC_SPECS:
            continue
        doc, _ = main_doc(spec_dir(e), spec)
        if not doc:
            continue
        sec = refs_section(full_text(doc))
        nums = {int(n) for n in RFC.findall(sec)}
        per_spec[spec] = sorted(nums)
        for n in nums:
            by_rfc[n].add(spec)
    out = {str(n): sorted(v) for n, v in sorted(by_rfc.items())}
    (HERE / "rfc_refs.json").write_text(
        json.dumps({"by_rfc": out, "per_spec": per_spec},
                   ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"규격 {len(per_spec)}건에서 RFC {len(by_rfc)}종 인용")
    for spec in RFC_SPECS:
        if spec in per_spec:
            print(f"  {spec}: {len(per_spec[spec])}종")
    print("\n=== 2개 이상 규격이 인용 ===")
    multi = [(n, v) for n, v in sorted(by_rfc.items()) if len(v) >= 2]
    print(f"{len(multi)}종: " + " ".join(f"RFC{n}" for n, _ in multi))
    print("\n=== 1개 규격만 인용 ===")
    single = [(n, v) for n, v in sorted(by_rfc.items()) if len(v) == 1]
    print(f"{len(single)}종: " + " ".join(f"RFC{n}" for n, _ in single))


if __name__ == "__main__":
    main()
