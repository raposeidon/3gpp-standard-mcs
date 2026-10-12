"""10-ietf-rfc/README.md 를 만든다."""
import json
import re

from common import HERE, RFC_MCX as MCX, ROOT

DEST = ROOT / "10-ietf-rfc"

PLAN = json.loads((HERE / "rfc_plan.json").read_text(encoding="utf-8"))
REFS = json.loads((HERE / "rfc_refs.json").read_text(encoding="utf-8"))
BY = {int(k): v for k, v in REFS["by_rfc"].items()}

AREA_TITLE = [
    ("sip", "SIP 코어·확장", "24.379 · 24.281 · 24.282 의 시그널링 기반."),
    ("sip-events", "SIP 이벤트·프레즌스", "affiliation, conference state, 필터."),
    ("sdp", "SDP", "오퍼/앤서와 미디어 기술. 대역폭 시그널링의 기반이다."),
    ("rtp", "RTP · RTCP · 페이로드", "미디어 플레인 전송과 코덱 페이로드."),
    ("srtp", "SRTP", "미디어 보호. 33.180 의 키 유도가 여기로 연결된다."),
    ("key-mgmt", "키 관리 (MIKEY-SAKKE)",
     "GMK · PCK · CSK · SPK · MuSiK 분배의 기반. 33.180 §7 · §9 가 이 RFC 들을 참조한다."),
    ("msrp", "MSRP", "MCData SDS · FD 의 미디어 플레인 (24.582)."),
    ("xcap", "XCAP · XML 문서 형식", "그룹 관리(24.481)와 설정 관리(24.484)."),
    ("oauth", "OAuth 2.0 · JWT", "신원 관리(24.482)와 33.180 의 토큰 처리."),
    ("http", "HTTP · URI", "CSC 인터페이스의 전송."),
    ("ice", "ICE", "NAT 통과."),
    ("eap", "EAP", "인증 프레임워크."),
    ("mime", "MIME · 인코딩", "SIP 바디와 MCData 페이로드의 표현."),
    ("misc", "그 밖의 기반 규격", "ABNF · UUID · 시각 · 주소 표기 등."),
]

# 이 집합을 만들기 전에 손으로 고른 기존 큐레이션 목록
CURATED = {
    5246, 5280, 6066, 7469, 8446,
    3261, 3326, 3428, 3515, 3841, 4412, 5373, 5626, 7315, 7989, 8101,
    3265, 3856, 3863, 3903, 4662, 6665,
    4474, 8224,
    3550, 3551, 4733, 4771, 5576, 5761, 6184, 7587, 7656, 7742, 7798,
    4566, 8866,
    5245, 5389, 5766, 5768, 8445, 8489, 8656,
    3830, 6507, 6508, 6509,
    6749, 6750, 7009, 7515, 7516, 7519, 7636, 7662,
    3748, 4186, 4187, 5448,
}


def cites(n):
    specs = [s for s in BY.get(n, []) if s in MCX]
    extra = [s for s in BY.get(n, []) if s not in MCX]
    out = " · ".join(specs)
    if extra:
        out += f" (+{' · '.join(extra)})"
    return out


def main():
    got = {p["rfc"] for p in PLAN}
    L = []
    L.append("# MCX 구현에 필요한 IETF RFC - 최소 집합\n")
    L.append(f"손으로 고른 목록이 아니다. **보유한 MCX 본체 규격 {len(MCX)}건의 References 절에서 "
             "실제로 인용된 RFC** 를 모아 영역별로 나눈 것이다. "
             f"모두 {len(PLAN)}종이며 본문은 `rfc<번호>.txt` 로 들어 있다.\n")
    L.append("근거로 삼은 규격: " + " · ".join(MCX) + "\n")
    L.append("- **26.114 (MTSI) 와 24.229 (IMS) 는 뺐다.** MCX 전용이 아니고 인용 폭이 "
             "넓어 최소 집합의 뜻이 사라진다 - 24.229 한 건이 RFC 247종을 언급한다. "
             "IMS 기반까지 훑어야 하면 그 두 규격의 References 절을 직접 본다.")
    L.append("- **23.283 과 29.380 은 RFC 를 인용하지 않는다.** "
             "3GPP 규격만 참조하므로 누락이 아니다.")
    L.append("- 3GPP 는 특정 판을 규범 참조하므로 **인용된 판 그대로** 받아 두었다. "
             "폐기·갱신된 것은 표의 비고에 적었고, 구현할 때 어느 쪽을 따를지는 "
             "인용한 3GPP 규격의 판을 기준으로 정한다.\n")
    L.append("출처: <https://www.rfc-editor.org/rfc/>\n")

    L.append("## 3GPP 규격과 RFC 의 관계\n")
    L.append("RFC 가 프로토콜 본체를 정의하고 3GPP 규격이 그것을 **프로파일링**한다. "
             "다만 권고나 제안이 아니라 **규범 참조**다 - 각 TS 의 References 절 "
             "머리말이 \"The following documents contain provisions which, through "
             "reference in this text, constitute provisions of the present document\" "
             "라고 밝힌다. 인용된 RFC 의 조항이 그 3GPP 규격의 조항이 된다는 뜻이며, "
             "RFC 만 구현해도 3GPP 적합이 아니고 3GPP 규격만 읽어도 구현이 되지 않는다.\n")
    L.append("- **어디서 무엇을 보는가** - 메시지 문법과 상태 기계는 RFC 이고, "
             "어떤 필드를 어떤 값으로 언제 보내는지는 3GPP 다. 예를 들어 24.379 는 "
             "SIP INVITE 의 Alert-Info 를 `<file:///dev/null>` 로 두라고 정하는데, "
             "그 값이 무엇을 뜻하는지는 24.379 에만 있고 RFC 3261 에는 헤더 문법만 있다.")
    L.append("- **판이 고정되는 참조가 있다** - `[29] IETF RFC 4412 (February 2006)` "
             "처럼 날짜가 붙은 specific reference 는 후속 개정이 적용되지 않는다. "
             "날짜가 없으면 최신판이다. 이 폴더가 인용된 판 그대로 받아 둔 이유다.")
    L.append("- **방향이 반대인 것도 있다** - RFC 8101 은 3GPP 가 정의한 MCPTT 의 "
             "요구를 채우려고 SIP Resource-Priority 네임스페이스를 IANA 에 등록한 "
             "문서다 (Informational, 2017). RFC 4964 (P-Answer-State) 도 같은 경위다.")
    L.append("- **대응 RFC 가 없는 부분도 있다** - 24.380 의 floor control 은 RTCP "
             "위에 3GPP 가 직접 정의한 프로토콜이라 IETF 대응물이 없다. 24.380 이 "
             "RFC 를 8종만 인용하고 29.380 이 한 건도 인용하지 않는 이유다.\n")

    for key, title, desc in AREA_TITLE:
        rows = sorted([p for p in PLAN if p["area"] == key],
                      key=lambda x: x["rfc"])
        if not rows:
            continue
        L.append(f"## {title} (`{key}`, {len(rows)}종)\n")
        if desc:
            L.append(desc + "\n")
        L.append("| RFC | 제목 | 인용 규격 | 비고 |")
        L.append("| --- | --- | --- | --- |")
        for p in rows:
            note = []
            if p["obsoleted_by"]:
                note.append(f"**폐기** - 후속 {p['obsoleted_by']}")
            if p["updated_by"]:
                note.append(f"갱신 {p['updated_by']}")
            st = p.get("status", "")
            if st and st not in ("PROPOSED STANDARD", "INTERNET STANDARD",
                                 "DRAFT STANDARD"):
                note.append(st.title())
            L.append(f"| [RFC {p['rfc']}]({key}/rfc{p['rfc']}.txt) "
                     f"| {p['title']} | {cites(p['rfc'])} | {' / '.join(note)} |")
        L.append("")

    L.append("## 기존 큐레이션 목록과의 차이\n")
    L.append("이 집합을 만들기 전에 손으로 골라 두었던 "
             f"{len(CURATED)}종과 대조한 결과다.\n")
    only_new = sorted(got - CURATED)
    only_old = sorted(CURATED - got)
    L.append(f"**새로 들어온 {len(only_new)}종** - 기존 목록에 없었지만 MCX 본체가 "
             "실제로 인용한다.\n")
    L.append("```")
    for i in range(0, len(only_new), 10):
        L.append(" ".join(f"RFC{n}" for n in only_new[i:i + 10]))
    L.append("```\n")
    L.append(f"**빠진 {len(only_old)}종** - 기존 목록에는 있으나 MCX 본체 {len(MCX)}건은 "
             "인용하지 않는다. 대부분 24.229 · 26.114 · 33.402 · 24.302 쪽에서 오는 "
             "IMS·접속 기반이라 이 최소 집합의 대상이 아니다.\n")
    L.append("```")
    for i in range(0, len(only_old), 10):
        L.append(" ".join(f"RFC{n}" for n in only_old[i:i + 10]))
    L.append("```\n")
    L.append("## 갱신\n")
    L.append("```")
    L.append("python _tools/rfc_refs.py   # 로컬 원문의 References 절 -> rfc_refs.json")
    L.append("python _tools/fetch_rfc.py --plan   # 영역 배치 미리보기")
    L.append("python _tools/fetch_rfc.py          # 내려받기")
    L.append("```\n")
    L.append("`_tools/rfc-index.txt` (RFC Editor 공식 색인) 를 함께 읽는다. "
             "제목·폐기·갱신 정보는 거기서 읽는다.\n")

    out = DEST / "README.md"
    out.write_text("\n".join(L), encoding="utf-8")
    print(f"{out} 작성 ({out.stat().st_size:,} B) / 신규 {len(only_new)} · "
          f"미인용 {len(only_old)}")


if __name__ == "__main__":
    main()
