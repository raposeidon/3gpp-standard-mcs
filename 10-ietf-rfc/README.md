# MCX 구현에 필요한 IETF RFC - 최소 집합

손으로 고른 목록이 아니다. **보유한 MCX 본체 규격 16건의 References 절에서 실제로 인용된 RFC** 를 모아 영역별로 나눈 것이다. 모두 107종이며 본문은 `rfc<번호>.txt` 로 들어 있다.

근거로 삼은 규격: 24.379 · 24.380 · 24.281 · 24.581 · 24.282 · 24.582 · 24.283 · 24.481 · 24.482 · 24.483 · 24.484 · 33.180 · 26.179 · 26.281 · 29.379 · 29.582

- **26.114 (MTSI) 와 24.229 (IMS) 는 뺐다.** MCX 전용이 아니고 인용 폭이 넓어 최소 집합의 뜻이 사라진다 - 24.229 한 건이 RFC 247종을 언급한다. IMS 기반까지 훑어야 하면 그 두 규격의 References 절을 직접 본다.
- **23.283 과 29.380 은 RFC 를 인용하지 않는다.** 3GPP 규격만 참조하므로 누락이 아니다.
- 3GPP 는 특정 판을 규범 참조하므로 **인용된 판 그대로** 받아 두었다. 폐기·갱신된 것은 표의 비고에 적었고, 구현할 때 어느 쪽을 따를지는 인용한 3GPP 규격의 판을 기준으로 정한다.

출처: <https://www.rfc-editor.org/rfc/>

## 3GPP 규격과 RFC 의 관계

RFC 가 프로토콜 본체를 정의하고 3GPP 규격이 그것을 **프로파일링**한다. 다만 권고나 제안이 아니라 **규범 참조**다 - 각 TS 의 References 절 머리말이 "The following documents contain provisions which, through reference in this text, constitute provisions of the present document" 라고 밝힌다. 인용된 RFC 의 조항이 그 3GPP 규격의 조항이 된다는 뜻이며, RFC 만 구현해도 3GPP 적합이 아니고 3GPP 규격만 읽어도 구현이 되지 않는다.

- **어디서 무엇을 보는가** - 메시지 문법과 상태 기계는 RFC 이고, 어떤 필드를 어떤 값으로 언제 보내는지는 3GPP 다. 예를 들어 24.379 는 SIP INVITE 의 Alert-Info 를 `<file:///dev/null>` 로 두라고 정하는데, 그 값이 무엇을 뜻하는지는 24.379 에만 있고 RFC 3261 에는 헤더 문법만 있다.
- **판이 고정되는 참조가 있다** - `[29] IETF RFC 4412 (February 2006)` 처럼 날짜가 붙은 specific reference 는 후속 개정이 적용되지 않는다. 날짜가 없으면 최신판이다. 이 폴더가 인용된 판 그대로 받아 둔 이유다.
- **방향이 반대인 것도 있다** - RFC 8101 은 3GPP 가 정의한 MCPTT 의 요구를 채우려고 SIP Resource-Priority 네임스페이스를 IANA 에 등록한 문서다 (Informational, 2017). RFC 4964 (P-Answer-State) 도 같은 경위다.
- **대응 RFC 가 없는 부분도 있다** - 24.380 의 floor control 은 RTCP 위에 3GPP 가 직접 정의한 프로토콜이라 IETF 대응물이 없다. 24.380 이 RFC 를 8종만 인용하고 29.380 이 한 건도 인용하지 않는 이유다.

## SIP 코어·확장 (`sip`, 25종)

24.379 · 24.281 · 24.282 의 시그널링 기반.

| RFC | 제목 | 인용 규격 | 비고 |
| --- | --- | --- | --- |
| [RFC 3261](sip/rfc3261.txt) | SIP: Session Initiation Protocol | 24.281 · 24.282 · 24.379 · 29.379 · 29.582 | 갱신 RFC3265, RFC3853, RFC4320, RFC4916, RFC5393, RFC5621, RFC5626, RFC5630, RFC5922, RFC5954, RFC6026, RFC6141, RFC6665, RFC6878, RFC7462, RFC7463, RFC8217, RFC8591, RFC8760, RFC8898, RFC8996 |
| [RFC 3325](sip/rfc3325.txt) | Private Extensions to the Session Initiation Protocol (SIP) for Asserted Identity within Trusted Networks | 24.379 | 갱신 RFC5876, RFC8217 / Informational |
| [RFC 3326](sip/rfc3326.txt) | The Reason Header Field for the Session Initiation Protocol (SIP) | 24.281 · 24.282 · 24.379 | 갱신 RFC8606, RFC9366 |
| [RFC 3428](sip/rfc3428.txt) | Session Initiation Protocol (SIP) Extension for Instant Messaging | 24.281 · 24.282 · 24.379 · 29.379 · 29.582 | 갱신 RFC8591 |
| [RFC 3515](sip/rfc3515.txt) | The Session Initiation Protocol (SIP) Refer Method | 24.281 · 24.282 · 24.379 | 갱신 RFC7647, RFC8217 |
| [RFC 3840](sip/rfc3840.txt) | Indicating User Agent Capabilities in the Session Initiation Protocol (SIP) | 24.281 · 24.282 · 24.379 · 29.379 · 29.582 |  |
| [RFC 3841](sip/rfc3841.txt) | Caller Preferences for the Session Initiation Protocol (SIP) | 24.281 · 24.282 · 24.379 · 29.379 · 29.582 |  |
| [RFC 3891](sip/rfc3891.txt) | The Session Initiation Protocol (SIP) "Replaces" Header | 24.379 |  |
| [RFC 3903](sip/rfc3903.txt) | Session Initiation Protocol (SIP) Extension for Event State Publication | 24.281 · 24.282 · 24.379 · 29.379 · 29.582 | 갱신 RFC8996 |
| [RFC 4028](sip/rfc4028.txt) | Session Timers in the Session Initiation Protocol (SIP) | 24.281 · 24.282 · 24.379 · 29.379 · 29.582 |  |
| [RFC 4412](sip/rfc4412.txt) | Communications Resource Priority for the Session Initiation Protocol (SIP) | 24.281 · 24.282 · 24.379 | 갱신 RFC7134 |
| [RFC 4483](sip/rfc4483.txt) | A Mechanism for Content Indirection in Session Initiation Protocol (SIP) Messages | 24.281 · 24.282 · 24.379 · 29.379 |  |
| [RFC 4538](sip/rfc4538.txt) | Request Authorization through Dialog Identification in the Session Initiation Protocol (SIP) | 24.281 · 24.282 · 24.379 · 29.379 |  |
| [RFC 4964](sip/rfc4964.txt) | The P-Answer-State Header Extension to the Session Initiation Protocol for the Open Mobile Alliance Push to Talk over Cellular | 24.281 · 24.379 · 29.379 | 갱신 RFC8996 / Informational |
| [RFC 5318](sip/rfc5318.txt) | The Session Initiation Protocol (SIP) P-Refused-URI-List Private- Header (P-Header) | 24.281 · 24.379 · 29.379 | 갱신 RFC8217 / Informational |
| [RFC 5366](sip/rfc5366.txt) | Conference Establishment Using Request-Contained Lists in the Session Initiation Protocol (SIP) | 24.281 · 24.282 · 24.379 · 29.379 · 29.582 |  |
| [RFC 5368](sip/rfc5368.txt) | Referring to Multiple Resources in the Session Initiation Protocol (SIP) | 24.281 · 24.379 | 갱신 RFC8262 |
| [RFC 5373](sip/rfc5373.txt) | Requesting Answering Modes for the Session Initiation Protocol (SIP) | 24.281 · 24.379 · 29.379 |  |
| [RFC 5626](sip/rfc5626.txt) | Managing Client-Initiated Connections in the Session Initiation Protocol (SIP) | 24.281 · 24.379 |  |
| [RFC 5627](sip/rfc5627.txt) | Obtaining and Using Globally Routable User Agent URIs (GRUUs) in the Session Initiation Protocol (SIP) | 24.281 · 24.282 · 24.379 |  |
| [RFC 6050](sip/rfc6050.txt) | A Session Initiation Protocol (SIP) Extension for the Identification of Services | 24.281 · 24.282 · 24.379 · 24.481 · 24.484 · 29.379 · 29.582 | Informational |
| [RFC 6086](sip/rfc6086.txt) | Session Initiation Protocol (SIP) INFO Method and Package Framework | 24.281 · 24.282 · 24.379 · 29.379 |  |
| [RFC 6809](sip/rfc6809.txt) | Mechanism to Indicate Support of Features and Capabilities in the Session Initiation Protocol (SIP) | 24.281 · 24.379 |  |
| [RFC 7462](sip/rfc7462.txt) | URNs for the Alert-Info Header Field of the Session Initiation Protocol (SIP) | 24.281 · 24.379 |  |
| [RFC 8101](sip/rfc8101.txt) | IANA Registration of New Session Initiation Protocol (SIP) Resource- Priority Namespace for Mission Critical Push To Talk Service | 24.281 · 24.282 · 24.379 · 24.484 · 29.379 | Informational |

## SIP 이벤트·프레즌스 (`sip-events`, 8종)

affiliation, conference state, 필터.

| RFC | 제목 | 인용 규격 | 비고 |
| --- | --- | --- | --- |
| [RFC 3856](sip-events/rfc3856.txt) | A Presence Event Package for the Session Initiation Protocol (SIP) | 24.281 · 24.282 · 24.379 · 29.379 · 29.582 | 갱신 RFC8996 |
| [RFC 3863](sip-events/rfc3863.txt) | Presence Information Data Format (PIDF) | 24.281 · 24.282 · 24.379 |  |
| [RFC 4354](sip-events/rfc4354.txt) | A Session Initiation Protocol (SIP) Event Package and Data Format for Various Settings in Support for the Push-to-Talk over Cellular (PoC) Service | 24.281 · 24.282 · 24.379 | Informational |
| [RFC 4488](sip-events/rfc4488.txt) | Suppression of Session Initiation Protocol (SIP) REFER Method Implicit Subscription | 24.281 · 24.282 · 24.379 · 29.379 |  |
| [RFC 4575](sip-events/rfc4575.txt) | A Session Initiation Protocol (SIP) Event Package for Conference State | 24.281 · 24.282 · 24.379 · 29.379 (+26.114) |  |
| [RFC 4661](sip-events/rfc4661.txt) | An Extensible Markup Language (XML)-Based Format for Event Notification Filtering | 24.281 · 24.282 · 24.379 |  |
| [RFC 6665](sip-events/rfc6665.txt) | SIP-Specific Event Notification | 24.281 · 24.282 · 24.379 · 29.379 · 29.582 | 갱신 RFC7621 |
| [RFC 7614](sip-events/rfc7614.txt) | Explicit Subscriptions for the REFER Method | 24.281 · 24.379 |  |

## SDP (`sdp`, 7종)

오퍼/앤서와 미디어 기술. 대역폭 시그널링의 기반이다.

| RFC | 제목 | 인용 규격 | 비고 |
| --- | --- | --- | --- |
| [RFC 3264](sdp/rfc3264.txt) | An Offer/Answer Model with Session Description Protocol (SDP) | 24.281 · 24.379 (+26.114) | 갱신 RFC6157, RFC8843, RFC9143 |
| [RFC 3605](sdp/rfc3605.txt) | Real Time Control Protocol (RTCP) attribute in Session Description Protocol (SDP) | 24.281 · 24.379 |  |
| [RFC 4566](sdp/rfc4566.txt) | SDP: Session Description Protocol | 24.281 · 24.282 · 24.379 · 24.481 · 24.483 · 29.379 (+26.114) | **폐기** - 후속 RFC8866 |
| [RFC 4567](sdp/rfc4567.txt) | Key Management Extensions for Session Description Protocol (SDP) and Real Time Streaming Protocol (RTSP) | 24.281 · 24.282 · 24.379 · 29.379 · 29.582 |  |
| [RFC 5547](sdp/rfc5547.txt) | A Session Description Protocol (SDP) Offer/Answer Mechanism to Enable File Transfer | 24.282 |  |
| [RFC 5576](sdp/rfc5576.txt) | Source-Specific Media Attributes in the Session Description Protocol (SDP) | 24.281 · 24.379 |  |
| [RFC 5888](sdp/rfc5888.txt) | The Session Description Protocol (SDP) Grouping Framework | 24.282 | 갱신 RFC8843, RFC9143 |

## RTP · RTCP · 페이로드 (`rtp`, 8종)

미디어 플레인 전송과 코덱 페이로드.

| RFC | 제목 | 인용 규격 | 비고 |
| --- | --- | --- | --- |
| [RFC 3095](rtp/rfc3095.txt) | RObust Header Compression (ROHC): Framework and four profiles: RTP, UDP, ESP, and uncompressed | 24.282 · 24.379 · 24.380 | 갱신 RFC3759, RFC4815 |
| [RFC 3550](rtp/rfc3550.txt) | RTP: A Transport Protocol for Real-Time Applications | 24.281 · 24.379 · 24.380 · 24.581 · 24.582 · 26.179 · 26.281 · 33.180 (+26.114) | 갱신 RFC5506, RFC5761, RFC6051, RFC6222, RFC7022, RFC7160, RFC7164, RFC8083, RFC8108, RFC8860 |
| [RFC 3551](rtp/rfc3551.txt) | RTP Profile for Audio and Video Conferences with Minimal Control | 26.179 (+26.114) | 갱신 RFC5761, RFC7007, RFC8860 |
| [RFC 4867](rtp/rfc4867.txt) | RTP Payload Format and File Storage Format for the Adaptive Multi- Rate (AMR) and Adaptive Multi-Rate Wideband (AMR-WB) Audio Codecs | 26.179 (+26.114) |  |
| [RFC 5225](rtp/rfc5225.txt) | RObust Header Compression Version 2 (ROHCv2): Profiles for RTP, UDP, IP, ESP and UDP-Lite | 24.380 |  |
| [RFC 5761](rtp/rfc5761.txt) | Multiplexing RTP Data and Control Packets on a Single Port | 24.281 · 24.282 · 24.379 · 24.380 | 갱신 RFC8035, RFC8858 |
| [RFC 5795](rtp/rfc5795.txt) | The RObust Header Compression (ROHC) Framework | 24.282 · 24.379 · 24.380 |  |
| [RFC 6184](rtp/rfc6184.txt) | RTP Payload Format for H.264 Video | 26.281 (+26.114) |  |

## SRTP (`srtp`, 3종)

미디어 보호. 33.180 의 키 유도가 여기로 연결된다.

| RFC | 제목 | 인용 규격 | 비고 |
| --- | --- | --- | --- |
| [RFC 3711](srtp/rfc3711.txt) | The Secure Real-time Transport Protocol (SRTP) | 24.380 · 24.581 · 24.582 · 26.179 · 26.281 · 29.582 · 33.180 | 갱신 RFC5506, RFC6904, RFC9335 |
| [RFC 4771](srtp/rfc4771.txt) | Integrity Transform Carrying Roll-Over Counter for the Secure Real- time Transport Protocol (SRTP) | 33.180 |  |
| [RFC 7714](srtp/rfc7714.txt) | AES-GCM Authenticated Encryption in the Secure Real-time Transport Protocol (SRTP) | 33.180 |  |

## 키 관리 (MIKEY-SAKKE) (`key-mgmt`, 8종)

GMK · PCK · CSK · SPK · MuSiK 분배의 기반. 33.180 §7 · §9 가 이 RFC 들을 참조한다.

| RFC | 제목 | 인용 규격 | 비고 |
| --- | --- | --- | --- |
| [RFC 3394](key-mgmt/rfc3394.txt) | Advanced Encryption Standard (AES) Key Wrap Algorithm | 33.180 | Informational |
| [RFC 3830](key-mgmt/rfc3830.txt) | MIKEY: Multimedia Internet KEYing | 24.380 · 24.481 · 24.581 · 33.180 | 갱신 RFC4738, RFC6309 |
| [RFC 5480](key-mgmt/rfc5480.txt) | Elliptic Curve Cryptography Subject Public Key Information | 33.180 | 갱신 RFC8813 |
| [RFC 6043](key-mgmt/rfc6043.txt) | MIKEY-TICKET: Ticket-Based Modes of Key Distribution in Multimedia Internet KEYing (MIKEY) | 24.481 · 33.180 | 갱신 RFC6309 / Informational |
| [RFC 6090](key-mgmt/rfc6090.txt) | Fundamental Elliptic Curve Cryptography Algorithms | 33.180 | Informational |
| [RFC 6507](key-mgmt/rfc6507.txt) | Elliptic Curve-Based Certificateless Signatures for Identity-Based Encryption (ECCSI) | 33.180 | Informational |
| [RFC 6508](key-mgmt/rfc6508.txt) | Sakai-Kasahara Key Encryption (SAKKE) | 33.180 | Informational |
| [RFC 6509](key-mgmt/rfc6509.txt) | MIKEY-SAKKE: Sakai-Kasahara Key Encryption in Multimedia Internet KEYing (MIKEY) | 24.281 · 24.282 · 24.379 · 24.380 · 24.481 · 24.581 · 33.180 | Informational |

## MSRP (`msrp`, 4종)

MCData SDS · FD 의 미디어 플레인 (24.582).

| RFC | 제목 | 인용 규격 | 비고 |
| --- | --- | --- | --- |
| [RFC 4975](msrp/rfc4975.txt) | The Message Session Relay Protocol (MSRP) | 24.282 · 24.582 · 29.582 | 갱신 RFC7977, RFC8591, RFC8873, RFC8996 |
| [RFC 4976](msrp/rfc4976.txt) | Relay Extensions for the Message Sessions Relay Protocol (MSRP) | 24.582 | 갱신 RFC7977, RFC8553, RFC8996 |
| [RFC 6135](msrp/rfc6135.txt) | An Alternative Connection Model for the Message Session Relay Protocol (MSRP) | 24.282 · 24.582 · 29.582 |  |
| [RFC 6714](msrp/rfc6714.txt) | Connection Establishment for Media Anchoring (CEMA) for the Message Session Relay Protocol (MSRP) | 24.282 · 24.582 · 29.582 |  |

## XCAP · XML 문서 형식 (`xcap`, 4종)

그룹 관리(24.481)와 설정 관리(24.484).

| RFC | 제목 | 인용 규격 | 비고 |
| --- | --- | --- | --- |
| [RFC 4745](xcap/rfc4745.txt) | Common Policy: A Document Format for Expressing Privacy Preferences | 24.481 · 24.484 |  |
| [RFC 4825](xcap/rfc4825.txt) | The Extensible Markup Language (XML) Configuration Access Protocol (XCAP) | 24.481 · 24.484 |  |
| [RFC 4826](xcap/rfc4826.txt) | Extensible Markup Language (XML) Formats for Representing Resource Lists | 24.282 · 24.379 · 24.481 · 29.582 |  |
| [RFC 5875](xcap/rfc5875.txt) | An Extensible Markup Language (XML) Configuration Access Protocol (XCAP) Diff Event Package | 24.481 · 24.484 |  |

## OAuth 2.0 · JWT (`oauth`, 9종)

신원 관리(24.482)와 33.180 의 토큰 처리.

| RFC | 제목 | 인용 규격 | 비고 |
| --- | --- | --- | --- |
| [RFC 6749](oauth/rfc6749.txt) | The OAuth 2.0 Authorization Framework | 24.482 · 33.180 | 갱신 RFC8252, RFC8996, RFC9700 |
| [RFC 6750](oauth/rfc6750.txt) | The OAuth 2.0 Authorization Framework: Bearer Token Usage | 24.283 · 24.482 · 33.180 | 갱신 RFC8996, RFC9700 |
| [RFC 7515](oauth/rfc7515.txt) | JSON Web Signature (JWS) | 33.180 |  |
| [RFC 7519](oauth/rfc7519.txt) | JSON Web Token (JWT) | 24.379 · 33.180 | 갱신 RFC7797, RFC8725 |
| [RFC 7521](oauth/rfc7521.txt) | Assertion Framework for OAuth 2.0 Client Authentication and Authorization Grants | 33.180 |  |
| [RFC 7523](oauth/rfc7523.txt) | JSON Web Token (JWT) Profile for OAuth 2.0 Client Authentication and Authorization Grants | 24.482 · 33.180 |  |
| [RFC 7636](oauth/rfc7636.txt) | Proof Key for Code Exchange by OAuth Public Clients | 33.180 |  |
| [RFC 7662](oauth/rfc7662.txt) | OAuth 2.0 Token Introspection | 33.180 |  |
| [RFC 8693](oauth/rfc8693.txt) | OAuth 2.0 Token Exchange | 24.482 |  |

## HTTP · URI (`http`, 7종)

CSC 인터페이스의 전송.

| RFC | 제목 | 인용 규격 | 비고 |
| --- | --- | --- | --- |
| [RFC 1738](http/rfc1738.txt) | Uniform Resource Locators (URL) | 24.282 · 29.582 | **폐기** - 후속 RFC4248, RFC4266 / 갱신 RFC1808, RFC2368, RFC2396, RFC3986, RFC6196, RFC6270, RFC8089 |
| [RFC 2392](http/rfc2392.txt) | Content-ID and Message-ID Uniform Resource Locators | 24.281 · 24.282 · 24.379 · 33.180 |  |
| [RFC 2818](http/rfc2818.txt) | HTTP Over TLS | 24.482 | **폐기** - 후속 RFC9110 / 갱신 RFC5785, RFC7230 / Informational |
| [RFC 3986](http/rfc3986.txt) | Uniform Resource Identifier (URI): Generic Syntax | 24.282 · 24.484 · 29.379 · 29.582 | 갱신 RFC7320, RFC8820 |
| [RFC 9110](http/rfc9110.txt) | HTTP Semantics | 24.282 · 24.481 · 24.482 |  |
| [RFC 9112](http/rfc9112.txt) | HTTP/1.1 | 24.282 · 24.482 (+26.114) | 갱신 RFC9931 |
| [RFC 9113](http/rfc9113.txt) | HTTP/2 | 24.283 · 24.482 |  |

## ICE (`ice`, 2종)

NAT 통과.

| RFC | 제목 | 인용 규격 | 비고 |
| --- | --- | --- | --- |
| [RFC 8445](ice/rfc8445.txt) | Interactive Connectivity Establishment (ICE): A Protocol for Network Address Translator (NAT) Traversal | 24.282 · 24.379 | 갱신 RFC8863 |
| [RFC 8839](ice/rfc8839.txt) | Session Description Protocol (SDP) Offer/Answer Procedures for Interactive Connectivity Establishment (ICE) | 24.282 · 24.379 (+26.114) |  |

## EAP (`eap`, 1종)

인증 프레임워크.

| RFC | 제목 | 인용 규격 | 비고 |
| --- | --- | --- | --- |
| [RFC 3748](eap/rfc3748.txt) | Extensible Authentication Protocol (EAP) | 24.483 · 24.484 | 갱신 RFC5247, RFC7057 |

## MIME · 인코딩 (`mime`, 4종)

SIP 바디와 MCData 페이로드의 표현.

| RFC | 제목 | 인용 규격 | 비고 |
| --- | --- | --- | --- |
| [RFC 2017](mime/rfc2017.txt) | Definition of the URL MIME External-Body Access-Type | 24.282 |  |
| [RFC 2045](mime/rfc2045.txt) | Multipurpose Internet Mail Extensions (MIME) Part One: Format of Internet Message Bodies | 24.281 · 24.282 · 24.379 · 33.180 | 갱신 RFC2184, RFC2231, RFC5335, RFC6532 |
| [RFC 2046](mime/rfc2046.txt) | Multipurpose Internet Mail Extensions (MIME) Part Two: Media Types | 24.281 · 24.282 · 24.379 · 24.582 | 갱신 RFC2646, RFC3798, RFC5147, RFC6657, RFC8098 |
| [RFC 4648](mime/rfc4648.txt) | The Base16, Base32, and Base64 Data Encodings | 24.281 · 24.282 · 24.379 |  |

## 그 밖의 기반 규격 (`misc`, 17종)

ABNF · UUID · 시각 · 주소 표기 등.

| RFC | 제목 | 인용 규격 | 비고 |
| --- | --- | --- | --- |
| [RFC 1166](misc/rfc1166.txt) | Internet numbers | 24.481 | 갱신 RFC5737 / Informational |
| [RFC 2784](misc/rfc2784.txt) | Generic Routing Encapsulation (GRE) | 24.582 | 갱신 RFC2890, RFC9601 |
| [RFC 2790](misc/rfc2790.txt) | Host Resources MIB | 24.582 |  |
| [RFC 3602](misc/rfc3602.txt) | The AES-CBC Cipher Algorithm and Its Use with IPsec | 33.180 |  |
| [RFC 4122](misc/rfc4122.txt) | A Universally Unique IDentifier (UUID) URN Namespace | 24.582 · 29.582 | **폐기** - 후속 RFC9562 |
| [RFC 5116](misc/rfc5116.txt) | An Interface and Algorithms for Authenticated Encryption | 33.180 |  |
| [RFC 5234](misc/rfc5234.txt) | Augmented BNF for Syntax Specifications: ABNF | 24.282 (+26.114) | 갱신 RFC7405 |
| [RFC 5288](misc/rfc5288.txt) | AES Galois Counter Mode (GCM) Cipher Suites for TLS | 24.379 | 갱신 RFC9325, RFC10015 |
| [RFC 5322](misc/rfc5322.txt) | Internet Message Format | 24.282 | 갱신 RFC6854 |
| [RFC 5905](misc/rfc5905.txt) | Network Time Protocol Version 4: Protocol and Algorithms Specification | 33.180 | 갱신 RFC7822, RFC8573, RFC9109, RFC9748, RFC9769 |
| [RFC 5952](misc/rfc5952.txt) | A Recommendation for IPv6 Address Text Representation | 24.481 |  |
| [RFC 7159](misc/rfc7159.txt) | The JavaScript Object Notation (JSON) Data Interchange Format | 24.482 | **폐기** - 후속 RFC8259 |
| [RFC 7647](misc/rfc7647.txt) | Clarifications for the Use of REFER with RFC 6665 | 24.281 · 24.282 · 24.379 |  |
| [RFC 8086](misc/rfc8086.txt) | GRE-in-UDP Encapsulation | 24.582 |  |
| [RFC 8200](misc/rfc8200.txt) | Internet Protocol, Version 6 (IPv6) Specification | 24.582 | 갱신 RFC9673 |
| [RFC 8259](misc/rfc8259.txt) | The JavaScript Object Notation (JSON) Data Interchange Format | 24.283 |  |
| [RFC 9562](misc/rfc9562.txt) | Universally Unique IDentifiers (UUIDs) | 24.281 · 24.282 · 24.283 · 24.379 |  |

## 기존 큐레이션 목록과의 차이

이 집합을 만들기 전에 손으로 골라 두었던 60종과 대조한 결과다.

**새로 들어온 75종** - 기존 목록에 없었지만 MCX 본체가 실제로 인용한다.

```
RFC1166 RFC1738 RFC2017 RFC2045 RFC2046 RFC2392 RFC2784 RFC2790 RFC2818 RFC3095
RFC3264 RFC3325 RFC3394 RFC3602 RFC3605 RFC3711 RFC3840 RFC3891 RFC3986 RFC4028
RFC4122 RFC4354 RFC4483 RFC4488 RFC4538 RFC4567 RFC4575 RFC4648 RFC4661 RFC4745
RFC4825 RFC4826 RFC4867 RFC4964 RFC4975 RFC4976 RFC5116 RFC5225 RFC5234 RFC5288
RFC5318 RFC5322 RFC5366 RFC5368 RFC5480 RFC5547 RFC5627 RFC5795 RFC5875 RFC5888
RFC5905 RFC5952 RFC6043 RFC6050 RFC6086 RFC6090 RFC6135 RFC6714 RFC6809 RFC7159
RFC7462 RFC7521 RFC7523 RFC7614 RFC7647 RFC7714 RFC8086 RFC8200 RFC8259 RFC8693
RFC8839 RFC9110 RFC9112 RFC9113 RFC9562
```

**빠진 28종** - 기존 목록에는 있으나 MCX 본체 16건은 인용하지 않는다. 대부분 24.229 · 26.114 · 33.402 · 24.302 쪽에서 오는 IMS·접속 기반이라 이 최소 집합의 대상이 아니다.

```
RFC3265 RFC4186 RFC4187 RFC4474 RFC4662 RFC4733 RFC5245 RFC5246 RFC5280 RFC5389
RFC5448 RFC5766 RFC5768 RFC6066 RFC7009 RFC7315 RFC7469 RFC7516 RFC7587 RFC7656
RFC7742 RFC7798 RFC7989 RFC8224 RFC8446 RFC8489 RFC8656 RFC8866
```

## 갱신

```
python _tools/rfc_refs.py   # 로컬 원문의 References 절 -> rfc_refs.json
python _tools/fetch_rfc.py --plan   # 영역 배치 미리보기
python _tools/fetch_rfc.py          # 내려받기
```

`_tools/rfc-index.txt` (RFC Editor 공식 색인) 를 함께 읽는다. 제목·폐기·갱신 정보는 거기서 읽는다.
