# 3GPP MCX 표준 수집 · Markdown 변환 도구

Mission Critical 계열 3GPP 규격을 **3GPP 아카이브에서 받아 서비스별 폴더에 풀고 Markdown 으로 변환**하는 스크립트와 그 대상 목록이다. 릴리스를 고정하지 않고 **규격마다 그 시점의 최신 버전**을 받으므로 Rel-13 부터 Rel-20 까지 섞인다. 이는 의도한 것이다.

**3GPP · ITU-T 원문과 그 변환본(md)은 이 저장소에 없다.** 두 기관 모두 서면 허가 없는 복제를 금지하므로, 스크립트를 돌려 각자 로컬에 받는다. IETF RFC 는 IETF Trust Legal Provisions 가 수정 없는 전문 배포를 허용하므로 `10-ietf-rfc/` 에 원문 그대로 넣어 두었다.

- 대상: 3GPP 81건 (`_tools/specs.json`) + ITU-T 2건 + IETF RFC 108종
- 아래 표의 버전: 2026-10-12 에 로컬에 받아 둔 판 기준 (81/81건). 다시 받으면 더 새 판이 나올 수 있다.
- 출처: <https://www.3gpp.org/ftp/Specs/archive/> · <https://www.itu.int/rec/>

## 사용법

Python 3 표준 라이브러리만 쓴다. 저장소 루트에서 돌린다. 구형 .doc 본문을 변환할 때만 LibreOffice 나 Word(Windows) 가 있으면 쓴다 (아래 제약 참조).

```
python _tools/fetch_3gpp.py --dry-run   # 받을 버전 미리보기
python _tools/fetch_3gpp.py             # 최신 zip 을 받아 서비스 폴더에 풀기 (zip 은 남기지 않음)
python _tools/convert_md.py             # 본문 docx -> md (이미 변환한 것은 건너뜀)
python _tools/gen_readme.py             # 이 README 재생성
```

규격번호를 인자로 주면 그것만 처리한다 (`python _tools/convert_md.py 24.380`). `convert_md.py --force` 는 이미 변환한 것도 다시 만든다. 대상 규격을 늘리거나 옮길 때는 `_tools/specs.json` 만 고친다 - 받기 · 변환 · README 가 모두 이 목록을 읽는다. 최신 zip 에 동봉 파일이 빠진 판은 그 항목에 `"attach_from": "k00"` 처럼 동봉 파일을 가져올 판을 적는다 (폴더에 동봉 파일이 없을 때만 그 판 zip 을 받는다).

클론한 뒤 `git config core.hooksPath _tools/hooks` 를 한 번 실행한다. `.gitignore` 가 제외하는 파일(원문 · 변환본)이 `git add -f` 로 스테이징되면 pre-commit 훅이 커밋을 거부한다.

## 폴더 구조

저장소에는 `10-ietf-rfc/` 와 `_tools/` 만 들어 있다. 나머지는 스크립트가 원문을 받아 채우는 자리다. `.gitignore` 는 허용 목록 방식이라 `specs.json` 에 새 서비스 폴더가 생겨도 추적되지 않는다.

```
00-common        MCS 공통 (요구사항 · 아키텍처 · CSC 인터페이스)
01-mcptt         MCPTT
02-mcvideo       MCVideo
03-mcdata        MCData
04-mcloc         MCLoc (Rel-19 신규)
05-security      보안
06-sip-ims       SIP · IMS 기반
07-media-codec   미디어 · 코덱
   amr-wb/       AMR-WB 계열
   evs/          EVS 계열
   itu-t/        ITU-T 권고 (AVC · HEVC, 수동으로 받는다)
08-interworking  LMR 연동
09-conformance   적합성 시험
   _draft-empty/ 본문 없는 v0.0.1 판
10-ietf-rfc      IETF RFC 최소 집합 (영역별, 저장소에 포함)
_tools           수집 · 변환 · 생성 스크립트 (저장소에 포함)
```

규격 하나는 `<서비스>/<ts|tr>-<번호>/` 에 들어간다. 아카이브 zip 은 메모리에서 풀고 남기지 않으므로 폴더에는 본문(`24380-k00.docx` 등)과 동봉 파일이 남고, 그 옆에 변환본 `24380-k00.md` 와 그림 폴더 `media/` 가 생긴다. 같은 판의 본문이 이미 있으면 다시 받지 않는다.

## Markdown 변환의 제약

`convert_md.py` 는 docx 의 XML 을 직접 읽어 3GPP 스타일 이름(Heading · B1 ~ B5 · PL · NO · TH · TOC 등)으로 구조를 구분한다. 외부 변환기를 쓰지 않는 대신 다음 제약이 있다.

- **.doc 본문은 LibreOffice 나 Word 가 있을 때만 변환된다.** 구형 Word 바이너리(OLE)라 표준 라이브러리로 읽을 수 없어, `convert_md.py` 가 `soffice` 를 찾으면 그것으로, 없으면 Windows 의 Word 로 임시 docx 를 만들어 변환한다. 둘 다 없으면 원문 그대로 둔다. 지금 변환되지 않은 것은 0건이다.
- **본문이 장별 파일로 나뉜 규격은 표지 docx 만 변환된다.** 26.445 가 해당하며, 나머지 조각(대부분 .doc)은 원문 그대로 남는다.
- **그림은 원래 형식 그대로 `media/` 에 빼낸다.** 3GPP 그림은 대부분 EMF · WMF 라 Markdown 뷰어에 보이지 않는다. 링크만 남으므로 그림이 필요하면 원문을 연다.
- **표의 병합 셀은 펼친다.** Markdown 표에 병합이 없어 가로 병합은 빈 칸으로, 세로 병합은 첫 행에만 내용을 둔다. 한 칸짜리 표(코드 · 그림 상자)는 표로 만들지 않고 내용을 본문으로 푼다.
- **글머리 계층은 들여쓰지 않는다.** 3GPP 본문에는 `1)` · `a)` · `-` 같은 표지 문자가 들어 있어 그대로 남기며, Markdown 에서 4칸 들여쓰기가 코드 블록으로 바뀌는 것을 막으려고 `-` 글머리만 목록으로 만든다.
- **수식은 텍스트만 남는다.** Office Math 는 기호 문자열로 풀리고 구조(분수 · 첨자)는 사라진다. 코덱 규격(26.445 등)을 수식 근거로 볼 때는 원문을 연다.
- **목차와 숨김 텍스트는 버린다.** 목차는 쪽 번호만 남고, 변경 추적의 삭제분도 뺀다.

## 공통 기반 (MCS Common)

네 서비스가 함께 쓰는 요구사항·아키텍처와 CSC 인터페이스 규격이다.

| 원문 (zip) | 표준 | 공식 명칭 | 버전 | 비고 |
| --- | --- | --- | --- | --- |
| [22280-l00.zip](https://www.3gpp.org/ftp/Specs/archive/22_series/22.280/22280-l00.zip) | TS 22.280 | Mission Critical Services Common Requirements (MCCoRe); Stage 1 | v21.0.0 (Rel-21, 2026-09) |  |
| [23280-k51.zip](https://www.3gpp.org/ftp/Specs/archive/23_series/23.280/23280-k51.zip) | TS 23.280 | Common functional architecture to support mission critical services; Stage 2 | v20.5.1 (Rel-20, 2026-10) |  |
| [23289-k30.zip](https://www.3gpp.org/ftp/Specs/archive/23_series/23.289/23289-k30.zip) | TS 23.289 | Mission Critical services over 5G System; Stage 2 | v20.3.0 (Rel-20, 2026-09) |  |
| [24481-j30.zip](https://www.3gpp.org/ftp/Specs/archive/24_series/24.481/24481-j30.zip) | TS 24.481 | Mission Critical Services (MCS) group management; Protocol specification | v19.3.0 (Rel-19, 2026-06) |  |
| [24482-j10.zip](https://www.3gpp.org/ftp/Specs/archive/24_series/24.482/24482-j10.zip) | TS 24.482 | Mission Critical Services (MCS) identity management; Protocol specification | v19.1.0 (Rel-19, 2026-06) |  |
| [24483-k10.zip](https://www.3gpp.org/ftp/Specs/archive/24_series/24.483/24483-k10.zip) | TS 24.483 | Mission Critical Services (MCS) Management Object (MO) | v20.1.0 (Rel-20, 2026-09) | MO DDF XML 은 k00 zip 에서 가져옴 (k10 zip 에 누락, k10 의 CR0192 는 그림만 고쳐 XML 내용은 같다) / 동봉: XML 11종 |
| [24484-k10.zip](https://www.3gpp.org/ftp/Specs/archive/24_series/24.484/24484-k10.zip) | TS 24.484 | Mission Critical Services (MCS) configuration management; Protocol specification | v20.1.0 (Rel-20, 2026-09) |  |

## MCPTT

Push To Talk. Stage 1 · 2 · 3 과 미디어 플레인·코덱이 모두 있다.

| 원문 (zip) | 표준 | 공식 명칭 | 버전 | 비고 |
| --- | --- | --- | --- | --- |
| [22179-l00.zip](https://www.3gpp.org/ftp/Specs/archive/22_series/22.179/22179-l00.zip) | TS 22.179 | Mission Critical Push To Talk (MCPTT); Stage 1 | v21.0.0 (Rel-21, 2026-09) |  |
| [23379-k40.zip](https://www.3gpp.org/ftp/Specs/archive/23_series/23.379/23379-k40.zip) | TS 23.379 | Functional architecture and information flows to support Mission Critical Push To Talk (MCPTT); Stage 2 | v20.4.0 (Rel-20, 2026-09) |  |
| [24379-k10.zip](https://www.3gpp.org/ftp/Specs/archive/24_series/24.379/24379-k10.zip) | TS 24.379 | Mission Critical Push To Talk (MCPTT) call control; Protocol specification | v20.1.0 (Rel-20, 2026-09) |  |
| [24380-k10.zip](https://www.3gpp.org/ftp/Specs/archive/24_series/24.380/24380-k10.zip) | TS 24.380 | Mission Critical Push To Talk (MCPTT) media plane control; Protocol specification | v20.1.0 (Rel-20, 2026-09) |  |
| [26179-j00.zip](https://www.3gpp.org/ftp/Specs/archive/26_series/26.179/26179-j00.zip) | TS 26.179 | Mission Critical Push To Talk (MCPTT); Codecs and media handling | v19.0.0 (Rel-19, 2025-10) |  |
| [26989-j00.zip](https://www.3gpp.org/ftp/Specs/archive/26_series/26.989/26989-j00.zip) | TR 26.989 | Mission Critical Push To Talk (MCPTT); Media, codecs and Multimedia Broadcast/Multicast Service (MBMS) enhancements for MCPTT over LTE | v19.0.0 (Rel-19, 2025-10) | 코덱 선정 근거 TR / .doc 원문 (임시 docx 로 바꿔 md 변환) |

## MCVideo

비디오. 구조는 MCPTT 와 같고 미디어 플레인이 transmission control 이다.

| 원문 (zip) | 표준 | 공식 명칭 | 버전 | 비고 |
| --- | --- | --- | --- | --- |
| [22281-j00.zip](https://www.3gpp.org/ftp/Specs/archive/22_series/22.281/22281-j00.zip) | TS 22.281 | Mission Critical Video services | v19.0.0 (Rel-19, 2025-10) |  |
| [23281-k51.zip](https://www.3gpp.org/ftp/Specs/archive/23_series/23.281/23281-k51.zip) | TS 23.281 | Functional architecture and information flows to support Mission Critical Video (MCVideo); Stage 2 | v20.5.1 (Rel-20, 2026-10) |  |
| [24281-k10.zip](https://www.3gpp.org/ftp/Specs/archive/24_series/24.281/24281-k10.zip) | TS 24.281 | Mission Critical Video (MCVideo) signalling control; Protocol specification | v20.1.0 (Rel-20, 2026-09) |  |
| [24581-j30.zip](https://www.3gpp.org/ftp/Specs/archive/24_series/24.581/24581-j30.zip) | TS 24.581 | Mission Critical Video (MCVideo) media plane control; Protocol specification | v19.3.0 (Rel-19, 2026-09) |  |
| [26281-j00.zip](https://www.3gpp.org/ftp/Specs/archive/26_series/26.281/26281-j00.zip) | TS 26.281 | Mission Critical Video (MCVideo); Codecs and media handling | v19.0.0 (Rel-19, 2025-10) |  |

## MCData

SDS · FD · OSM. 미디어 플레인은 MSRP 기반이다.

| 원문 (zip) | 표준 | 공식 명칭 | 버전 | 비고 |
| --- | --- | --- | --- | --- |
| [22282-j00.zip](https://www.3gpp.org/ftp/Specs/archive/22_series/22.282/22282-j00.zip) | TS 22.282 | Mission Critical Data services | v19.0.0 (Rel-19, 2025-10) |  |
| [23282-k31.zip](https://www.3gpp.org/ftp/Specs/archive/23_series/23.282/23282-k31.zip) | TS 23.282 | Functional architecture and information flows to support Mission Critical Data (MCData); Stage 2 | v20.3.1 (Rel-20, 2026-10) |  |
| [24282-k10.zip](https://www.3gpp.org/ftp/Specs/archive/24_series/24.282/24282-k10.zip) | TS 24.282 | Mission Critical Data (MCData) signalling control; Protocol specification | v20.1.0 (Rel-20, 2026-09) |  |
| [24582-j00.zip](https://www.3gpp.org/ftp/Specs/archive/24_series/24.582/24582-j00.zip) | TS 24.582 | Mission Critical Data (MCData) media plane control; Protocol specification | v19.0.0 (Rel-19, 2025-10) |  |

## MCLoc (Rel-19 신규)

Rel-19 에서 독립한 위치 관리 서비스. 전용 규격은 24.283 하나뿐이고 요구사항·아키텍처는 22.280 · 23.280 의 위치 관리 절에 들어 있다.

| 원문 (zip) | 표준 | 공식 명칭 | 버전 | 비고 |
| --- | --- | --- | --- | --- |
| [23032-j00.zip](https://www.3gpp.org/ftp/Specs/archive/23_series/23.032/23032-j00.zip) | TS 23.032 | Universal Geographical Area Description (GAD) | v19.0.0 (Rel-19, 2025-09) |  |
| [24283-k00.zip](https://www.3gpp.org/ftp/Specs/archive/24_series/24.283/24283-k00.zip) | TS 24.283 | Mission Critical Location Management (MCLoc); Protocol specification | v20.0.0 (Rel-20, 2026-09) | 동봉: OpenAPI 2종 |
| [29572-k10.zip](https://www.3gpp.org/ftp/Specs/archive/29_series/29.572/29572-k10.zip) | TS 29.572 | 5G System; Location Management Services; Stage 3 | v20.1.0 (Rel-20, 2026-09) | 동봉: OpenAPI 3종 |

## 보안

KMS · MIKEY-SAKKE · GMK/PCK/CSK/SPK/MuSiK · SRTP 키 유도.

| 원문 (zip) | 표준 | 공식 명칭 | 버전 | 비고 |
| --- | --- | --- | --- | --- |
| [33180-k10.zip](https://www.3gpp.org/ftp/Specs/archive/33_series/33.180/33180-k10.zip) | TS 33.180 | Security of the Mission Critical (MC) service | v20.1.0 (Rel-20, 2026-09) |  |
| [33220-j10.zip](https://www.3gpp.org/ftp/Specs/archive/33_series/33.220/33220-j10.zip) | TS 33.220 | Generic Authentication Architecture (GAA); Generic Bootstrapping Architecture (GBA) | v19.1.0 (Rel-19, 2026-01) |  |
| [33879-d10.zip](https://www.3gpp.org/ftp/Specs/archive/33_series/33.879/33879-d10.zip) | TR 33.879 | Study on security enhancements for Mission Critical Push To Talk (MCPTT) over LTE | v13.1.0 (Rel-13, 2016-06) | Rel-13 설계 배경 TR / .doc 원문 (임시 docx 로 바꿔 md 변환) |

## SIP · IMS 기반

모든 Stage 3 규격이 "according to 24.229" 로 되돌아가는 상위 규격이다.

| 원문 (zip) | 표준 | 공식 명칭 | 버전 | 비고 |
| --- | --- | --- | --- | --- |
| [23203-k10.zip](https://www.3gpp.org/ftp/Specs/archive/23_series/23.203/23203-k10.zip) | TS 23.203 | Policy and charging control architecture | v20.1.0 (Rel-20, 2026-09) | 2026-09-28 추가 · 표 6.1.7-A QCI 특성표 (QCI 65 · 67 · 69 · 70) |
| [24229-k10.zip](https://www.3gpp.org/ftp/Specs/archive/24_series/24.229/24229-k10.zip) | TS 24.229 | IP multimedia call control protocol based on Session Initiation Protocol (SIP) and Session Description Protocol (SDP) | v20.1.0 (Rel-20, 2026-09) | .doc 원문 (임시 docx 로 바꿔 md 변환) |
| [29213-j30.zip](https://www.3gpp.org/ftp/Specs/archive/29_series/29.213/29213-j30.zip) | TS 29.213 | Policy and Charging Control signalling flows and Quality of Service (QoS) parameter mapping | v19.3.0 (Rel-19, 2025-12) | 2026-09-28 추가 · 표 6.2.1 · 6.3.1 SDP b=AS → MBR 유도, GBR 은 운영자 설정 |
| [31102-k00.zip](https://www.3gpp.org/ftp/Specs/archive/31_series/31.102/31102-k00.zip) | TS 31.102 | Characteristics of the Universal Subscriber Identity Module (USIM) application | v20.0.0 (Rel-20, 2026-09) |  |
| [31103-j10.zip](https://www.3gpp.org/ftp/Specs/archive/31_series/31.103/31103-j10.zip) | TS 31.103 | Characteristics of the IP Multimedia Services Identity Module (ISIM) application | v19.1.0 (Rel-19, 2026-09) |  |

## 미디어 · 코덱

MCX 코덱 규격이 참조하는 미디어 핸들링과 코덱 본체.

| 원문 (zip) | 표준 | 공식 명칭 | 버전 | 비고 |
| --- | --- | --- | --- | --- |
| [26114-k11.zip](https://www.3gpp.org/ftp/Specs/archive/26_series/26.114/26114-k11.zip) | TS 26.114 | IP Multimedia Subsystem (IMS); Multimedia Telephony; Media handling and interaction | v20.1.1 (Rel-20, 2026-09) | 동봉: zip 2종 · TS26114_QoEMetrics.xsd · XML 3종 |
| [26116-j00.zip](https://www.3gpp.org/ftp/Specs/archive/26_series/26.116/26116-j00.zip) | TS 26.116 | Television (TV) over 3GPP services; Video profiles | v19.0.0 (Rel-19, 2025-10) |  |
| [26346-j30.zip](https://www.3gpp.org/ftp/Specs/archive/26_series/26.346/26346-j30.zip) | TS 26.346 | Multimedia Broadcast/Multicast Service (MBMS); Protocols and codecs | v19.3.0 (Rel-19, 2025-12) | 동봉: XSD 40종 |

## AMR-WB 계열

| 원문 (zip) | 표준 | 공식 명칭 | 버전 | 비고 |
| --- | --- | --- | --- | --- |
| [26171-j00.zip](https://www.3gpp.org/ftp/Specs/archive/26_series/26.171/26171-j00.zip) | TS 26.171 | Speech codec speech processing functions; Adaptive Multi-Rate - Wideband (AMR-WB) speech codec; General description | v19.0.0 (Rel-19, 2025-10) |  |
| [26173-j00.zip](https://www.3gpp.org/ftp/Specs/archive/26_series/26.173/26173-j00.zip) | TS 26.173 | ANSI-C code for the Adaptive Multi-Rate - Wideband (AMR-WB) speech codec | v19.0.0 (Rel-19, 2025-10) | 동봉: 26173-i00_ANSI-C_source_code.zip |
| [26190-j00.zip](https://www.3gpp.org/ftp/Specs/archive/26_series/26.190/26190-j00.zip) | TS 26.190 | Speech codec speech processing functions; Adaptive Multi-Rate - Wideband (AMR-WB) speech codec; Transcoding functions | v19.0.0 (Rel-19, 2025-10) |  |
| [26191-j00.zip](https://www.3gpp.org/ftp/Specs/archive/26_series/26.191/26191-j00.zip) | TS 26.191 | Speech codec speech processing functions; Adaptive Multi-Rate - Wideband (AMR-WB) speech codec; Error concealment of erroneous or lost frames | v19.0.0 (Rel-19, 2025-10) |  |
| [26192-j00.zip](https://www.3gpp.org/ftp/Specs/archive/26_series/26.192/26192-j00.zip) | TS 26.192 | Speech codec speech processing functions; Adaptive Multi-Rate - Wideband (AMR-WB) speech codec; Comfort noise aspects | v19.0.0 (Rel-19, 2025-10) |  |
| [26193-j00.zip](https://www.3gpp.org/ftp/Specs/archive/26_series/26.193/26193-j00.zip) | TS 26.193 | Speech codec speech processing functions; Adaptive Multi-Rate - Wideband (AMR-WB) speech codec; Source controlled rate operation | v19.0.0 (Rel-19, 2025-10) |  |
| [26194-j00.zip](https://www.3gpp.org/ftp/Specs/archive/26_series/26.194/26194-j00.zip) | TS 26.194 | Speech codec speech processing functions; Adaptive Multi-Rate - Wideband (AMR-WB) speech codec; Voice Activity Detector (VAD) | v19.0.0 (Rel-19, 2025-10) |  |
| [26204-j00.zip](https://www.3gpp.org/ftp/Specs/archive/26_series/26.204/26204-j00.zip) | TS 26.204 | Speech codec speech processing functions; Adaptive Multi-Rate - Wideband (AMR-WB) speech codec; ANSI-C code | v19.0.0 (Rel-19, 2025-10) | 동봉: 26204-i00_ANSI-C_source_code.zip |

## EVS 계열

| 원문 (zip) | 표준 | 공식 명칭 | 버전 | 비고 |
| --- | --- | --- | --- | --- |
| [26441-j00.zip](https://www.3gpp.org/ftp/Specs/archive/26_series/26.441/26441-j00.zip) | TS 26.441 | Codec for Enhanced Voice Services (EVS); General Overview | v19.0.0 (Rel-19, 2025-10) |  |
| [26442-j00.zip](https://www.3gpp.org/ftp/Specs/archive/26_series/26.442/26442-j00.zip) | TS 26.442 | Codec for Enhanced Voice Services (EVS); ANSI C code (fixed-point) | v19.0.0 (Rel-19, 2025-10) | 동봉: 26442-i00-ANSI-C_source_code.zip |
| [26443-j00.zip](https://www.3gpp.org/ftp/Specs/archive/26_series/26.443/26443-j00.zip) | TS 26.443 | Codec for Enhanced Voice Services (EVS); ANSI C code (floating-point) | v19.0.0 (Rel-19, 2025-10) | 동봉: 26443-i00-ANSI-C_source_code.zip |
| [26444-j01.zip](https://www.3gpp.org/ftp/Specs/archive/26_series/26.444/26444-j01.zip) | TS 26.444 | Codec for Enhanced Voice Services (EVS); Test Sequences | v19.0.1 (Rel-19, 2026-02) | 동봉: 기타 1건 |
| [26445-j10.zip](https://www.3gpp.org/ftp/Specs/archive/26_series/26.445/26445-j10.zip) | TS 26.445 | Codec for Enhanced Voice Services (EVS); Detailed Algorithmic Description | v19.1.0 (Rel-19, 2025-12) | **본문이 장별 조각으로 나뉨 - 조각 10건은 md 변환 안 함** / 동봉: 본문 조각 10건 · 기타 1건 |
| [26446-j00.zip](https://www.3gpp.org/ftp/Specs/archive/26_series/26.446/26446-j00.zip) | TS 26.446 | Codec for Enhanced Voice Services (EVS); Adaptive Multi-Rate - Wideband (AMR-WB) backward compatible functions | v19.0.0 (Rel-19, 2025-10) |  |
| [26447-j00.zip](https://www.3gpp.org/ftp/Specs/archive/26_series/26.447/26447-j00.zip) | TS 26.447 | Codec for Enhanced Voice Services (EVS); Error Concealment of Lost Packets | v19.0.0 (Rel-19, 2025-10) |  |
| [26448-j00.zip](https://www.3gpp.org/ftp/Specs/archive/26_series/26.448/26448-j00.zip) | TS 26.448 | Codec for Enhanced Voice Services (EVS); Jitter Buffer Management | v19.0.0 (Rel-19, 2025-10) |  |
| [26449-j00.zip](https://www.3gpp.org/ftp/Specs/archive/26_series/26.449/26449-j00.zip) | TS 26.449 | Codec for Enhanced Voice Services (EVS); Comfort Noise Generation (CNG) Aspects | v19.0.0 (Rel-19, 2025-10) |  |
| [26450-j00.zip](https://www.3gpp.org/ftp/Specs/archive/26_series/26.450/26450-j00.zip) | TS 26.450 | Codec for Enhanced Voice Services (EVS); Discontinuous Transmission (DTX) | v19.0.0 (Rel-19, 2025-10) |  |
| [26451-j00.zip](https://www.3gpp.org/ftp/Specs/archive/26_series/26.451/26451-j00.zip) | TS 26.451 | Codec for Enhanced Voice Services (EVS); Voice Activity Detection (VAD) | v19.0.0 (Rel-19, 2025-10) |  |
| [26452-j00.zip](https://www.3gpp.org/ftp/Specs/archive/26_series/26.452/26452-j00.zip) | TS 26.452 | Codec for Enhanced Voice Services (EVS); ANSI C code; Alternative fixed-point using updated basic operators | v19.0.0 (Rel-19, 2025-10) | 동봉: 26452-i00_ANSI-C_source_code.zip |
| [26453-j00.zip](https://www.3gpp.org/ftp/Specs/archive/26_series/26.453/26453-j00.zip) | TS 26.453 | Speech codec speech processing functions; Codec for Enhanced Voice Services (EVS); Speech codec frame structure | v19.0.0 (Rel-19, 2025-10) |  |
| [26454-j00.zip](https://www.3gpp.org/ftp/Specs/archive/26_series/26.454/26454-j00.zip) | TS 26.454 | Codec for Enhanced Voice Services (EVS); Interface to Iu, Uu, Nb and Mb | v19.0.0 (Rel-19, 2025-10) |  |

## LMR 연동

기존 무전(TETRA 등)과의 연동. 실제 현장 경로다.

| 원문 (zip) | 표준 | 공식 명칭 | 버전 | 비고 |
| --- | --- | --- | --- | --- |
| [23283-k10.zip](https://www.3gpp.org/ftp/Specs/archive/23_series/23.283/23283-k10.zip) | TS 23.283 | Mission Critical Communication Interworking with Land Mobile Radio Systems; Stage 2 | v20.1.0 (Rel-20, 2026-01) |  |
| [29379-k00.zip](https://www.3gpp.org/ftp/Specs/archive/29_series/29.379/29379-k00.zip) | TS 29.379 | Mission Critical Push To Talk (MCPTT) call control interworking with Land Mobile Radio (LMR) systems; Stage-3 | v20.0.0 (Rel-20, 2026-09) |  |
| [29380-j00.zip](https://www.3gpp.org/ftp/Specs/archive/29_series/29.380/29380-j00.zip) | TS 29.380 | Mission Critical Push To Talk (MCPTT) media plane control interworking with Land Mobile Radio (LMR) systems | v19.0.0 (Rel-19, 2025-10) | .doc 원문 (임시 docx 로 바꿔 md 변환) |
| [29582-j00.zip](https://www.3gpp.org/ftp/Specs/archive/29_series/29.582/29582-j00.zip) | TS 29.582 | Mission Critical Data (MCData) interworking with Land Mobile Radio (LMR) systems; Stage 3 | v19.0.0 (Rel-19, 2025-10) |  |

## 적합성 시험

규격 본문이 모호한 지점을 시험 케이스가 한 가지 동작으로 못 박아 둔 경우가 많아 IOT 해석 다툼에서 먼저 찾아볼 자료다.

| 원문 (zip) | 표준 | 공식 명칭 | 버전 | 비고 |
| --- | --- | --- | --- | --- |
| [36579-1-g80.zip](https://www.3gpp.org/ftp/Specs/archive/36_series/36.579-1/36579-1-g80.zip) | TS 36.579-1 | Mission Critical (MC) services over LTE; Part 1: Common test environment | v16.8.0 (Rel-16, 2025-03) |  |
| [36579-2-g80.zip](https://www.3gpp.org/ftp/Specs/archive/36_series/36.579-2/36579-2-g80.zip) | TS 36.579-2 | Mission Critical (MC) services over LTE; Part 2: Mission Critical Push To Talk (MCPTT) User Equipment (UE) Protocol conformance specification | v16.8.0 (Rel-16, 2025-03) |  |
| [36579-3-f00.zip](https://www.3gpp.org/ftp/Specs/archive/36_series/36.579-3/36579-3-f00.zip) | TS 36.579-3 | Mission Critical (MC) services over LTE; Part 3: Mission Critical Push To Talk (MCPTT) Server Application conformance specification | v15.0.0 (Rel-15, 2024-03) | .doc 원문 (임시 docx 로 바꿔 md 변환) |
| [36579-4-g80.zip](https://www.3gpp.org/ftp/Specs/archive/36_series/36.579-4/36579-4-g80.zip) | TS 36.579-4 | Mission Critical (MC) services over LTE; Part 4: Test Applicability and Implementation Conformance Statement (ICS) proforma specification | v16.8.0 (Rel-16, 2025-03) |  |
| [36579-5-i30.zip](https://www.3gpp.org/ftp/Specs/archive/36_series/36.579-5/36579-5-i30.zip) | TS 36.579-5 | Mission Critical (MC) services over LTE; Part 5: Abstract test suite (ATS) | v18.3.0 (Rel-18, 2025-06) |  |
| [36579-6-g60.zip](https://www.3gpp.org/ftp/Specs/archive/36_series/36.579-6/36579-6-g60.zip) | TS 36.579-6 | Mission Critical (MC) services over LTE; Part 6: Mission Critical Video (MCVideo) User Equipment (UE) Protocol conformance specification | v16.6.0 (Rel-16, 2025-03) |  |
| [36579-7-g70.zip](https://www.3gpp.org/ftp/Specs/archive/36_series/36.579-7/36579-7-g70.zip) | TS 36.579-7 | Mission Critical (MC) services over LTE; Part 7: Mission Critical Data (MCData) User Equipment (UE) Protocol conformance specification | v16.7.0 (Rel-16, 2025-03) |  |
| [37579-1-i10.zip](https://www.3gpp.org/ftp/Specs/archive/37_series/37.579-1/37579-1-i10.zip) | TS 37.579-1 | Mission Critical (MC) services; Part 1: Common test environment | v18.1.0 (Rel-18, 2026-09) |  |
| [37579-2-i10.zip](https://www.3gpp.org/ftp/Specs/archive/37_series/37.579-2/37579-2-i10.zip) | TS 37.579-2 | Mission Critical (MC) services; Part 2: Mission Critical Push To Talk (MCPTT) User Equipment (UE) Protocol conformance specification | v18.1.0 (Rel-18, 2026-09) |  |
| [37579-4-i10.zip](https://www.3gpp.org/ftp/Specs/archive/37_series/37.579-4/37579-4-i10.zip) | TS 37.579-4 | Mission Critical (MC) services; Part 4: Test Applicability and Implementation Conformance Statement (ICS) proforma specification | v18.1.0 (Rel-18, 2026-09) |  |
| [37579-5-j10.zip](https://www.3gpp.org/ftp/Specs/archive/37_series/37.579-5/37579-5-j10.zip) | TS 37.579-5 | Mission Critical (MC) services; Part 5: Abstract test suite (ATS) | v19.1.0 (Rel-19, 2026-09) | 동봉: 37579-5-j10_TTCN3.zip |
| [37579-6-i00.zip](https://www.3gpp.org/ftp/Specs/archive/37_series/37.579-6/37579-6-i00.zip) | TS 37.579-6 | Mission Critical (MC) services; Part 6: Mission Critical Video (MCVideo) User Equipment (UE) Protocol conformance specification | v18.0.0 (Rel-18, 2026-09) |  |
| [37579-7-h70.zip](https://www.3gpp.org/ftp/Specs/archive/37_series/37.579-7/37579-7-h70.zip) | TS 37.579-7 | Mission Critical (MC) services; Part 7: Mission Critical Data (MCData) User Equipment (UE) Protocol conformance specification | v17.7.0 (Rel-17, 2026-09) |  |

## 적합성 시험 - 본문 없는 판

| 원문 (zip) | 표준 | 공식 명칭 | 버전 | 비고 |
| --- | --- | --- | --- | --- |
| [36579-8-001.zip](https://www.3gpp.org/ftp/Specs/archive/36_series/36.579-8/36579-8-001.zip) | TS 36.579-8 | Mission Critical (MC) services over LTE; Part 8: Mission Critical Video (MCVideo) Server Application conformance specification | v0.0.1 (Rel-16, 2023-03) | 본문 없음 - 착수만 된 판 |
| [36579-9-001.zip](https://www.3gpp.org/ftp/Specs/archive/36_series/36.579-9/36579-9-001.zip) | TS 36.579-9 | Mission Critical (MC) services over LTE; Part 9: Mission Critical Data (MCData) Server Application conformance specification | v0.0.1 (Rel-16, 2023-03) | 본문 없음 - 착수만 된 판 |
| [37579-10-001.zip](https://www.3gpp.org/ftp/Specs/archive/37_series/37.579-10/37579-10-001.zip) | TS 37.579-10 | Mission Critical (MC) services; Server application common test environment | v0.0.1 (Rel-18, 2026-09) | 본문 없음 - 착수만 된 판 |
| [37579-3-001.zip](https://www.3gpp.org/ftp/Specs/archive/37_series/37.579-3/37579-3-001.zip) | TS 37.579-3 | Mission Critical (MC) services; Mission Critical Push To Talk (MCPTT) server application conformance specification | v0.0.1 (Rel-18, 2026-09) | 본문 없음 - 착수만 된 판 |
| [37579-8-001.zip](https://www.3gpp.org/ftp/Specs/archive/37_series/37.579-8/37579-8-001.zip) | TS 37.579-8 | Mission Critical (MC) services; Mission Critical Video (MCVideo) server application conformance specification | v0.0.1 (Rel-18, 2026-09) | 본문 없음 - 착수만 된 판 |
| [37579-9-001.zip](https://www.3gpp.org/ftp/Specs/archive/37_series/37.579-9/37579-9-001.zip) | TS 37.579-9 | Mission Critical (MC) services; Mission Critical Data (MCData) server application conformance specification | v0.0.1 (Rel-18, 2026-09) | 본문 없음 - 착수만 된 판 |

## ITU-T 권고 (`07-media-codec/itu-t`)

HEVC · AVC 는 3GPP 규격이 아니라 ITU-T 권고다. 3GPP 아카이브에 없으므로 `fetch_3gpp.py` 가 받지 않는다. 26.281 (MCVideo 코덱) 과 26.114 (MTSI 미디어 핸들링) 가 이 둘을 참조하므로 참조 사슬의 끝에 해당한다. ITU 사이트에서 무료로 받을 수 있지만 재배포는 허용되지 않는다. 로컬 파일명은 `H.264-V16-202606_AVC.pdf` 처럼 판과 승인월을 붙인다.

| 원문 | 권고 | 공식 명칭 | 판 |
| --- | --- | --- | --- |
| [T-REC-H.264](https://www.itu.int/rec/T-REC-H.264) | ITU-T H.264 | Advanced video coding for generic audiovisual services | V16 (2026-06) |
| [T-REC-H.265](https://www.itu.int/rec/T-REC-H.265) | ITU-T H.265 | High efficiency video coding | V11 (2026-01) |

H.266 (VVC) 는 받지 않는다. 26.281 이 H.264 Constrained Baseline 을 필수로, H.265 를 선택으로 규정하고 VVC 는 대상이 아니기 때문이다.

## IETF RFC (`10-ietf-rfc`)

MCX 본체 규격 16건의 References 절에서 실제로 인용된 RFC 108종을 영역별로 받아 두었다. 목록과 인용 규격 대응은 [10-ietf-rfc/README.md](10-ietf-rfc/README.md) 에 있다. 26.114 (MTSI) 와 24.229 (IMS) 는 인용 폭이 넓어 그 집합에서 뺐다.

## 읽을 때 주의할 점

- **릴리스가 규격마다 다르다.** 한 절의 동작을 다른 규격과 대조할 때 두 문서의 Release 가 같은지 먼저 확인한다.
- **`_draft-empty/` 6건은 본문이 없다.** 제목만 있고 시험 케이스가 들어 있지 않다. 검색 결과에 섞여 나와 실제 시험 규격으로 오인되는 것을 막으려고 분리해 두었다.
- **TR 33.879 는 Rel-13 에서 멈춘 MCPTT 전용 설계 배경 TR 이다.** 보안 규격은 33.180 을 보고, 같은 Rel-13 구판이던 TS 33.179 는 내용이 33.180 으로 이관돼 대상에서 뺐다.
- **MCX IWF 프로토콜은 29.379 · 29.380 · 29.582 셋이다.** 29.387 · 29.388 · 29.389 는 V2X, 29.579 는 SMS 연동으로 번호만 이웃일 뿐이다.
- **위치 관리는 두 군데에 있다.** Rel-19 부터 MCLoc(24.283)이 독립했지만 서비스별 위치 보고 절(24.379 §13 등)도 그대로 남아 있다.
- **ANSI-C 참조 소스와 TTCN-3 번들은 zip 인 채로 남는다.** `fetch_3gpp.py` 는 아카이브 zip 을 한 번만 풀고 그 안의 zip 은 풀지 않는다.
