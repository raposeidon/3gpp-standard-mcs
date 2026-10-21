"""MCX 본체 규격이 인용한 RFC 와 MCX 클라이언트 구현이 근거로 쓰는 RFC(EXTRA_RFCS)를 영역별로 내려받고
배치 결과를 rfc_plan.json 에 남긴다. 표준이 아닌 근거 문서(EXTRA_DOCS)도 함께 받는다.

사용: python fetch_rfc.py [--plan]   (--plan 은 영역 배치만 보여 주고 받지 않는다)
README 는 gen_rfc_readme.py 가 rfc_plan.json 으로 만든다.
"""
import concurrent.futures as cf
import json
import re
import sys

from common import HERE, RFC_MCX, ROOT, fetch

DEST = ROOT / "10-ietf-rfc"

# MCX 본체 규격(RFC_MCX)이 직접 인용하지 않지만 MCX 클라이언트 구현이 근거로 쓰는 RFC (2026-10-19).
# 26 계열(코덱 · SDP) 과 국방 변형이 인용한다. 번호 → 쓰는 곳
EXTRA_RFCS = {
    3556: "b=RS · b=RR (24.229 §6.1.1 이 인용)",
    3890: "b=TIAS (26.114 준용)",
    4585: "AVPF (26.114 준용)",
    7587: "Opus 페이로드",
    7616: "HTTP Digest - SIP Digest 응답 계산, 33.203 Annex N 이 인용",
    7741: "VP8 페이로드",
    7798: "H.265 페이로드",
    8269: "ARIA SRTP - 국방 변형",
    9628: "VP9 페이로드",
}

# IETF 가 아닌 근거 문서. (저장 경로, URL, 쓰는 곳). OpenID Foundation 사양은 구현 목적의 복제 · 배포를 허락한다
EXTRA_DOCS = [
    ("11-openid/openid-connect-core-1_0.txt", "https://openid.net/specs/openid-connect-core-1_0.txt",
     "OpenID Connect Core 1.0 - 33.180 §5.1 · Annex B 가 인용"),
]

AREAS = [
    ("msrp", r"MSRP|Message Session Relay"),
    ("xcap", r"XCAP|XML Configuration Access|Resource Lists|Common Policy"
             r"|Presence Authorization|XML Patch|Partial Notification"),
    ("srtp", r"Secure Real-time Transport|SRTP"),
    ("key-mgmt", r"MIKEY|SAKKE|ECCSI|Identity-Based|Key Wrap|Elliptic Curve"
                 r"|Suite B|Multimedia Internet KEYing|Ticket"),
    ("oauth", r"OAuth|JSON Web|Assertion Framework|Token Introspection"
              r"|Code Exchange|Token Revocation"),
    ("ice", r"\bSTUN\b|\bTURN\b|Interactive Connectivity|\bNAT\b|Network Address Translat"),
    ("eap", r"\bEAP\b|Extensible Authentication"),
    ("sdp", r"Session Description Protocol|\bSDP\b|Offer/Answer"),
    ("sip-events", r"Event (Package|Notification)|Presence|PUBLISH"
                   r"|Subscri|Notification"),
    ("sip-security", r"Authenticated Identity|Identity Management"),
    ("sip", r"Session Initiation Protocol|\bSIP\b"),
    ("rtp", r"\bRTP\b|\bRTCP\b|Payload Format|Codec|Real-time Transport"
            r"|Header Compression|ROHC|Video Coding|Speech"),
    ("http", r"\bHTTP\b|Hypertext|Uniform Resource"),
    ("mime", r"\bMIME\b|Media Type|Internet Mail Extensions|Base64|Base 16"
             r"|Content-ID|Message Body"),
]


def parse_index(path, wanted):
    """rfc-index.txt 에서 필요한 번호의 제목·상태·폐기 정보를 뽑는다."""
    txt = path.read_text(encoding="utf-8", errors="replace")
    # 항목은 줄 머리의 번호로 시작하고 이어지는 줄은 들여 쓴다. 번호는 0 을 채우지 않는다 (768).
    blocks = re.split(r"\n(?=\d{1,5} )", txt)
    out = {}
    for b in blocks:
        m = re.match(r"(\d{1,5}) (.*)", b, re.S)
        if not m:
            continue
        num = int(m.group(1))
        if num not in wanted:
            continue
        body = re.sub(r"\s+", " ", m.group(2)).strip()
        title = body.split(". ")[0].strip()
        obs = re.search(r"Obsoleted by ([^)]+)\)", body)
        upd = re.search(r"Updated by ([^)]+)\)", body)
        st = re.search(r"\(Status: ([^)]+)\)", body)
        out[num] = {"title": title,
                    "obsoleted_by": obs.group(1).strip() if obs else "",
                    "updated_by": upd.group(1).strip() if upd else "",
                    "status": st.group(1).strip() if st else ""}
    return out


def area_of(title):
    for name, pat in AREAS:
        if re.search(pat, title, re.I):
            return name
    return "misc"


def main():
    refs = json.loads((HERE / "rfc_refs.json").read_text(encoding="utf-8"))
    by_rfc = {int(k): v for k, v in refs["by_rfc"].items()}
    wanted = sorted({n for n, specs in by_rfc.items()
                     if any(s in RFC_MCX for s in specs)} | set(EXTRA_RFCS))
    meta = parse_index(HERE / "rfc-index.txt", set(wanted))
    missing = [n for n in wanted if n not in meta]
    if missing:
        print("색인에 없음:", missing)

    plan = []
    for n in wanted:
        m = meta.get(n, {"title": "", "obsoleted_by": "", "updated_by": "",
                         "status": ""})
        plan.append((n, area_of(m["title"]), m))

    if "--plan" in sys.argv:
        for area, _ in AREAS + [("misc", "")]:
            rows = [p for p in plan if p[1] == area]
            if rows:
                print(f"\n## {area} ({len(rows)})")
                for n, _, m in rows:
                    print(f"  RFC{n:<5} {m['title'][:78]}")
        return

    def one(item):
        n, area, m = item
        d = DEST / area
        d.mkdir(parents=True, exist_ok=True)
        out = d / f"rfc{n}.txt"
        if out.exists() and out.stat().st_size > 2000:
            return n, "SKIP"
        try:
            out.write_bytes(fetch(f"https://www.rfc-editor.org/rfc/rfc{n}.txt"))
            return n, "GET"
        except Exception as exc:  # noqa: BLE001
            return n, f"FAIL {exc}"

    done = []
    with cf.ThreadPoolExecutor(max_workers=6) as ex:
        for n, st in ex.map(one, plan):
            done.append((n, st))
    for rel, url, _ in EXTRA_DOCS:
        out = ROOT / rel
        if out.exists() and out.stat().st_size > 2000:
            done.append((rel, "SKIP"))
            continue
        out.parent.mkdir(parents=True, exist_ok=True)
        try:
            out.write_bytes(fetch(url))
            done.append((rel, "GET"))
        except Exception as exc:  # noqa: BLE001
            done.append((rel, f"FAIL {exc}"))
    bad = [x for x in done if x[1].startswith("FAIL")]
    print(f"RFC {len(done)}건 처리, 실패 {len(bad)}건")
    for n, st in bad:
        print("  ", n, st)

    (HERE / "rfc_plan.json").write_text(
        json.dumps([{"rfc": n, "area": a, **m} for n, a, m in plan],
                   ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
