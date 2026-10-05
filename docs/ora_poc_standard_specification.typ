// Open Reconfigurable Architecture (ORA) PoC Detailed Standard Specification
// Version 1.0 - Core Fabric, Protocol, and Bytecode Specification
// Typst >= 0.15 Compatible Format

#set document(
  title: "ORA PoC 상세 기술 표준 규격서 (v1.0)",
  author: "Open Reconfigurable Architecture Working Group",
  date: auto
)

#set page(
  paper: "a4",
  margin: (top: 2.2cm, bottom: 2.2cm, left: 2.0cm, right: 2.0cm),
  header: context {
    if here().page() > 1 {
      text(8.5pt, fill: luma(100), font: "Noto Sans CJK KR")[
        _ORA PoC Technical Specification v1.0_
        #h(1fr)
        _Core & Bytecode Binary Standard_
      ]
      v(-0.5em)
      line(length: 100%, stroke: 0.4pt + luma(180))
    }
  },
  footer: context {
    let pagenum = here().page();
    text(8.5pt, fill: luma(120), font: "Noto Sans CJK KR")[
      #h(1fr)
      #pagenum
      #h(1fr)
    ]
  }
)

#set text(
  font: ("Noto Sans CJK KR", "Noto Sans"),
  size: 9.5pt,
  weight: "regular",
  lang: "ko"
)

#set par(
  justify: true,
  leading: 0.8em,
  first-line-indent: 1.2em
)

#show heading: set text(weight: "bold", fill: rgb("#111827"))
#show heading.where(level: 1): it => block(spacing: 1.4em, sticky: true)[
  #text(15pt)[#it.body]
  #v(0.3em)
  #line(length: 100%, stroke: 1.2pt + rgb("#1e3a8a"))
]
#show heading.where(level: 2): it => block(spacing: 1.1em, sticky: true)[
  #text(12pt, fill: rgb("#1e3a8a"))[#it.body]
]
#show heading.where(level: 3): it => block(spacing: 0.9em, sticky: true)[
  #text(10.5pt, fill: rgb("#374151"))[#it.body]
]

#set table(
  stroke: (x, y) => if y == 0 { (bottom: 1.2pt + rgb("#1e3a8a")) } else { (bottom: 0.5pt + luma(210)) },
  fill: (col, row) => if row == 0 { rgb("#f1f5f9") } else if calc.odd(row) { rgb("#f8fafc") } else { none },
  inset: (x: 7pt, y: 6pt)
)

#show table.cell: it => {
  if it.y == 0 {
    set text(weight: "bold", size: 8.5pt)
    it
  } else {
    set text(size: 8pt)
    it
  }
}

// Title
#align(center)[
  #block(width: 95%)[
    #text(18pt, weight: "bold", fill: rgb("#0f172a"))[개방형 재구성 가능 아키텍처(ORA) PoC 상세 표준 규격서]
    #v(0.4em)
    #text(11pt, weight: "medium", fill: rgb("#334155"))[
      V-HAL 바이트코드 포맷, ORA-N NoC 프로토콜, 탄성 데이터플로우 인터페이스 명세 (v1.0)
    ]
    #v(1.0em)
    #line(length: 50%, stroke: 0.8pt + rgb("#cbd5e1"))
    #v(0.6em)
  ]
]

#block(
  fill: rgb("#f8fafc"),
  inset: 12pt,
  radius: 4pt,
  stroke: 1pt + rgb("#e2e8f0")
)[
  #text(weight: "bold", fill: rgb("#1e3a8a"))[문서 목적 및 범위 (Scope)]
  
  본 문서는 ORA(Open Reconfigurable Architecture)의 기능 실증을 위한 PoC(Proof-of-Concept) 소프트웨어 시뮬레이터 및 가상 에뮬레이터 개발에 직접 사용되는 구체적인 하드웨어 인터페이스, 신호 규약, 통신 플릿 포맷, 그리고 중립 바이트코드 비트스트림 v1.0의 32비트 메모리 맵을 명세한다.
]

#v(1.0em)

= ORA-D: 디지털 탄성 패브릭 인터페이스 명세

== 2선 분산 핸드셰이크 (Valid / Ready) 채널 규약

모든 ORA-D 연산 노드 및 상호연결 라인은 글로벌 클록 도메인의 스큐(Skew)에 무관하게 동작할 수 있도록 전방 신호 `Valid`와 후방 신호 `Ready`가 결합된 탄성 인터페이스(Elastic Channel)를 표준 채널로 규정한다.

#figure(
  caption: [ORA-D 기본 탄성 채널 신호 정의],
  table(
    columns: (1.8fr, 1.2fr, 1.0fr, 4.0fr),
    align: (left, center, center, left),
    table.header([*신호명*], [*비트 폭*], [*방향*], [*기능 및 프로토콜 동작*]),
    [`DATA`], [$W$ 비트], [송신 $arrow$ 수신], [연산 데이터 페이로드 ($W in {1, 8, 16, 32}$)],
    [`VALID`], [1 비트], [송신 $arrow$ 수신], [데이터 유효성 지시자 (`1`일 때 `DATA` 라인 안정 상태 보장)],
    [`READY`], [1 비트], [수신 $arrow$ 송신], [수신 측 버퍼 수용 준비 완료 지시자 (`1`일 때 데이터 소비 가능)],
    [`CONTROL`], [2 비트], [송신 $arrow$ 수신], [제어 태그 (`00`: 일반 데이터, `01`: 시작 토큰, `10`: 종료 토큰, `11`: 리셋)]
  )
)

*핸드셰이크 전이 규칙:*
- 데이터 트랜잭션은 단일 사이클 내에서 `VALID == 1`과 `READY == 1`이 동시에 만족(점화 조건, Fire)되는 순간 즉시 완료된다.
- `VALID`가 `1`로 천이된 후에는 해당 트랜잭션이 완료(`READY == 1`)될 때까지 `DATA`와 `VALID` 신호를 임의로 취소하거나 변경할 수 없다 (No Cancellation Rule).
- 백프레셔(Backpressure)는 `READY == 0`을 통해 상위 송신 노드로 지연 없이 전파된다.

== 가상 논리 요소 (GLE) 및 탄성 제어 프리미티브

GLE(Generic Logic Element)는 $k$-입력 LUT($k in {4, 6}$)와 선택적 탄성 레지스터(Elastic Register)로 구성된다.

1. *GLE 불리언 연산 인터페이스:*
  - 4-입력 LUT 기준: $16$-비트 구성 메모리(`CFG_LUT[15:0]`)를 바탕으로 입력 포트 $A, B, C, D$의 진리표를 직접 평가한다:
    $ Y = "CFG_LUT"[D dot 8 + C dot 4 + B dot 2 + A] $
2. *탄성 Join 유닛:*
  - 복수의 입력 탄성 채널 $A, B$를 수신하여 두 입력이 모두 유효할 때만 연산을 점화한다:
    $ "VALID"_Y = "VALID"_A and "VALID"_B $
    $ "READY"_A = "READY"_Y and "VALID"_B, quad "READY"_B = "READY"_Y and "VALID"_A $
3. *탄성 Fork 유닛:*
  - 단일 입력 토큰을 복수의 출력 채널 $Y_1, Y_2$로 복제 방출한다. 두 출력 채널이 모두 토큰을 수용할 때까지 입력을 유지한다:
    $ "VALID"_(Y_1) = "VALID"_A and not "ACK"_(1), quad "VALID"_(Y_2) = "VALID"_A and not "ACK"_(2) $
    $ "READY"_A = ("READY"_(Y_1) or "ACK"_(1)) and ("READY"_(Y_2) or "ACK"_(2)) $

= ORA-N: 32비트 토폴로지 비종속 NoC 플릿 명세

ORA-N 패킷은 고정 32비트 단위의 플릿(Flit) 시퀀스로 구성되며, 라우터 내부의 라우팅 테이블 메모리를 배제하기 위해 소스 라우팅(Source Routing) 및 단조 가상 채널 계층화(Monotonic VC Layering)를 수행한다.

== 플릿 타입별 32비트 비트 필드 매핑

#figure(
  caption: [ORA-N 32비트 플릿 아키텍처 비트맵],
  table(
    columns: (2.2fr, 1.8fr, 4.0fr),
    align: (left, center, left),
    table.header([*플릿 종류*], [*비트 구간*], [*필드 명칭 및 상세 인코딩*]),
    [Header Flit\ (`Bit [31:30] = 00`)], [Bit [31:30]\ Bit [29:28]\ Bit [27:25]\ Bit [24]\ Bit [23:21]\ Bit [20:0]], [Flit Type: `2'b00` (Header)\ Virtual Channel ID: `2'b00` (VC0), `2'b01` (VC1)\ Remaining Hop Count: `3'b000`–`3'b111` ($0 dash 7$ 홉; 방향 벡터 길이와 일치해야 함)\ Chained Header Flag: `1`=홉 소진 시 후속 플릿을 새 헤더로 해석 (후속 플릿은 반드시 유형 `00`이어야 함), `0`=로컬 배출\ VC Transition Hop Index: `3'b000`–`3'b110`은 순번(ordinal) 승격 홉을 뜻하며 매 홉마다 감산 카운트다운, `3'b111`=미승격\ Packed Direction Vector: 홉당 3비트 $times$ 최대 7홉 (Bit [2:0] = 첫 홉)],
    [Body Flit\ (`Bit [31:30] = 01`)], [Bit [31:30]\ Bit [29:28]\ Bit [27:0]], [Flit Type: `2'b01` (Body)\ Virtual Channel ID: 헤더의 현재 VC를 따름 (`2'b00` 또는 `2'b01`)\ Data Payload: 28비트 데이터 스트림 워드],
    [Tail Flit\ (`Bit [31:30] = 10`)], [Bit [31:30]\ Bit [29:28]\ Bit [27:0]], [Flit Type: `2'b10` (Tail - 패킷 종료 및 VC 자원 해제)\ Virtual Channel ID: 헤더의 현재 VC를 따름\ Data Payload: 28비트 최종 데이터 워드],
    [Single-Flit AER\ (`Bit [31:30] = 11`)], [Bit [31:30]\ Bit [29:28]\ Bit [27:26]\ Bit [25:20]\ Bit [19:0]], [Flit Type: `2'b11` (Single-Flit AER Event)\ Virtual Channel ID: `2'b00` (VC0 전용 고우선순위)\ Remaining Hop Count: `2'b00`–`2'b10` (최대 2홉, 인접 타일 고속 직달)\ Packed Direction Vector: 2홉 $times$ 3비트 (Bit [22:20] = 첫 홉)\ Local Neuron Address: 20비트 국소 뉴런 식별자 (최대 $2^20$ 개 = 1,048,576 개)]
  )
)

== 소스 라우터 포트 인코딩 및 처리 알고리즘

각 라우터의 3비트 방향 벡터 인코딩은 다음과 같다:
- `3'b000`: Local PE / Tile Core
- `3'b001`: North (+Y)
- `3'b010`: East (+X)
- `3'b011`: South (-Y)
- `3'b100`: West (-X)
- `3'b101`: Up (+Z, 3D 칩렛 적층)
- `3'b110`: Down (-Z, 3D 칩렛 인터포저)
- `3'b111`: Reserved / Loopback

#block(
  fill: rgb("#f1f5f9"),
  inset: 10pt,
  radius: 4pt,
  stroke: 0.5pt + rgb("#cbd5e1")
)[
  #text(size: 8.5pt, weight: "bold")[라우터 플릿 포워딩 및 논리 시프트 알고리즘 (의사코드)]
  #v(0.3em)
  ```
  function ProcessHeaderFlit(flit):
      current_hops = flit[27:25]                     // 잔여 홉
      trans_idx    = flit[23:21]                      // VC 승격 잔여 카운트

      if current_hops == 0:                          // 1. 홉 소련 판정이 최우선
          if flit[24] == 1:                          //    Chained Header
              DropCurrentFlit()                      //    헤더 폐기; 다음 플릿은
              GotoNextFlitAsHeader()                 //    반드시 유형 2'b00 헤더
          else:
              EjectToLocalNI(flit)                   //    최종 도착지 로컬 배출
          return

      if trans_idx == 3'b000:                        // 2. 승격 조건 (카운트다운 0)
          flit[29:28] = 2'b01                         //    VC1 단조 승격
          flit[23:21] = 3'b111                       //    재승격 방지 센티넬
      elif trans_idx != 3'b111:                      // 3'b111은 미승격을 뜻함
          flit[23:21] = trans_idx - 1                //    승격 카운트다운 감소

      out_port = flit[2:0]                           // 3. 최하위 3비트 = 출력 포트
      flit[27:25] = current_hops - 1                 //    홉 카운터 감소
      flit[20:0] = flit[20:0] >>> 3                  //    논리 시프트 (Zero-Fill)
      RouteToPort(out_port, flit)                    //    출력 포트로 포워딩
  ```
]

*승격 인덱스의 의미:* `VC Transition Hop Index`의 값 $k$는 *시작 노드로부터의 순번(ordinal) 홉*이 아니라, *현재 헤더 세그먼트 내 남은 승격까지의 홉 수*다. 즉 값 `000`이면 이번 홉에서 즉시 VC1으로 승격하고, 값 $k > 0$이면 라우터가 홉마다 $k$를 1씩 감산한다. 값 `111`은 "이 세그먼트에서 승격 없음"을 뜻하는 센티넬로, 잔여 홉 카운트(최대 7)와 절대 크기 비교하지 않는다. 이 카운트다운 규약으로 7홉 패킷이 첫 홉에서 우발 승격되는 오류가 원천 차단된다.

== 웜홀 자원 관리 및 사이클 중재 계약

본 절은 동기식 라우터 구현이 비트·사이클 단위로 동일한 동작을 보이기 위한 규범(normative) 계약이다. PoC 참조 모델 `ora_fabric.router.NoCRouter`와 SpinalHDL `OraRouter`가 이 계약을 공유하며, 2-라우터 체인 co-sim으로 트레이스 정합을 확인한다.

*자원 모델.* 각 입력 포트는 VC별 독립 FIFO(입력 채널 = (입력 포트, VC))를 갖는다. 헤더가 출력 자원 (출력 포트, 출력 VC)를 획득하면 해당 입력 채널에 웜홀 락이 걸리고, 이후 Body/Tail 플릿은 헤더 처리 없이 같은 경로로 흐르며 VC 필드 `[29:28]`이 락의 출력 VC로 재기록된다. 로컬 배출(포트 `3'b000`)도 하나의 출력 포트로 취급한다.

#figure(
  table(
    columns: (22%, 78%),
    align: (left, left),
    table.header([*규칙*], [*정의*]),
    [사이클 시작 상태], [모든 결정은 사이클 시작 시점의 FIFO 선두, 락, 하류 크레딧(점유 수 \< 깊이)만으로 내린다. 같은 사이클에 다른 채널이 만든 변화는 보지 않으므로, 라우터 평가 순서와 무관하게 결과가 결정된다.],
    [포트당 1 플릿], [각 출력 포트(로컬 배출 포함)는 사이클당 최대 1개 플릿만 승인한다.],
    [포트별 라운드로빈], [한 출력 포트를 요구하는 후보들은 *요구 출력 VC* 클래스로 구분된다. 그 포트에서 직전에 승인된 클래스는 상대 클래스에 양보한다. 포인터는 출력 포트별로 존재하며 그 포트가 승인할 때만 갱신된다(초기값 VC0, 즉 첫 차례는 VC1). 같은 클래스 안에서는 (입력 포트, 입력 VC) 오름차순이 우선한다.],
    [락 해제→재부여], [Tail이 해제한 (출력 포트, 출력 VC)는 *다음 사이클부터* 다른 헤더에 승인할 수 있다.],
    [패킷 종료], [모든 패킷은 Tail로 끝나야 한다(페이로드가 없으면 NI가 빈 Tail을 붙인다). 예외적으로 로컬 배출된 단독 헤더는 (로컬, VC) 락을 유지하다가 같은 채널에 다음 헤더가 도착하면 그 사이클에 락만 해제하고, 새 헤더는 다음 사이클에 처리한다. 단독 헤더가 링크를 통과하는 것은 금지된다(상류 전진 락이 해제되지 않음).],
    [체인드 헤더 폐기], [소진된 체인드 헤더의 폐기는 포트를 사용하지 않으며 무조건 수행된다. 후속 헤더는 다음 사이클에 같은 라우터에서 평가된다.],
    [AER], [단일 플릿 AER은 VC0 클래스를 사용하며, (출력 포트, VC0)이 웜홀에 점유된 동안에는 그 포트로 진입하지 않는다(로컬 배출 포함).],
  ),
  caption: [웜홀 자원 관리 및 사이클 중재 규칙],
)

*수신 측 재조립.* 단일 배출 포트에서 VC0과 VC1 웜홀이 플릿 단위로 교차될 수 있으므로, NI는 플릿의 VC 필드로 VC별 재조립 버퍼를 분리해야 한다.

= ORA-A & ORA-M: 아날로그 연산 및 혼성 경계 규격

== CAB 파라미터 레지스터 맵

#figure(
  caption: [CAB(연산 아날로그 블록) 제어 레지스터 규격],
  table(
    columns: (1.5fr, 1.2fr, 1.8fr, 3.5fr),
    align: (left, center, center, left),
    table.header([*레지스터 명칭*], [*주소 오프셋*], [*데이터 형식*], [*설정 내용 및 제어 물리량*]),
    [`CAB_OTA_GM`], [`0x00`], [u32 고정 단위\ (pS)], [OTA 트랜스컨덕턴스 $G_m$ 제어\ (10,000–1,000,000,000 pS = 10 nS–1 mS. FP16의 최소 비정규수는 약 $6 times 10^(-5)$이므로 10 nS를 FP16으로 저장하면 언더플로한다. 따라서 v1.0은 고정 단위 정수 인코딩을 사용한다)],
    [`CAB_CAP_BANK`], [`0x04`], [u32 고정 단위\ (코드 0–255)], [적분 커패시터 뱅크 정전용량 선택 (코드 $c arrow C = 100 "fF" dot (c + 1)$, 즉 100 fF–25.6 pF)],
    [`CAB_MITE_BIAS`], [`0x08`], [u32 고정 단위\ (12-bit 코드)], [트랜스리니어 요소 서브스레숄드 바이어스 전압 설정 (0–4095)],
    [`CAB_VMM_CFG`], [`0x0C`], [u32 고정 단위\ (16-bit 마스크)], [Crossbar 입력 라인 및 열 선택 활성화 비트마스크 (0–65535)]
  )
)

== ORA-M 혼성 신호 경계 번역 인터페이스

1. *SAR ADC 변환 인터페이스:*
  - 디지털 코어가 `ADC_START` 스트로브를 인가하면, 12비트 SAR ADC가 변환을 시작하고 $15$ 사이클 후 `ADC_DONE`과 함께 12비트 디지털 결과 워드 `ADC_DATA[11:0]`를 래치한다.
2. *연속 시간 레벨 교차 검출기 (Level-Crossing Detector):*
  - 아날로그 적분 전압 $V(t)$가 기준 전압 $V_"ref"$를 상향 교차하는 즉시 $1.5 "ns"$ 폭의 비동기 펄스를 생성하여 디지털 AER 송신 블록으로 전달한다.

= V-HAL: ORA 중립 바이트코드 비트스트림 v1.0 바이너리 레이아웃

ORA 중립 비트스트림 v1.0은 *고정 48바이트 헤더*와 *TLV(Tag-Length-Value) 섹션 프레이밍*으로 구성된다. 모든 정수는 리틀 엔디언(Little-Endian)이며, 본 절의 레이아웃은 참조 구현 `poc/ora_bitstream/`과 바이트 단위로 정합한다.

#figure(
  caption: [ORA 중립 비트스트림 v1.0 바이너리 레이아웃 구조],
  table(
    columns: (1.8fr, 1.5fr, 1.2fr, 3.5fr),
    align: (left, center, center, left),
    table.header([*바이너리 섹션*], [*오프셋 범위*], [*크기*], [*설명 및 유효성 검사 규칙*]),
    [Magic Header], [`0x0000`], [4 Bytes], [ASCII 문자열 `"ORA1"`],
    [Spec Version], [`0x0004`], [4 Bytes], [Major(16b) + Minor(16b), `0x00010000` (v1.0)],
    [Profile Bitmask], [`0x0008`], [4 Bytes], [Bit 0: ORA-D, Bit 1: ORA-A, Bit 2: ORA-M, Bit 3: ORA-N (ORA-A는 ORA-M을 수반해야 함)],
    [Header Checksum], [`0x000C`], [4 Bytes], [*바이트 `0x0000`–`0x000B`(12바이트)에 대한* CRC-32 (자기 자신은 제외)],
    [Manifest], [`0x0010`–`0x002F`], [32 Bytes], [`u32` $times 8$: GLE4 수, GLE6 수, PEU 수, CAB 수, 라우터 수, NI 수, 예약 2개(0이어야 함). GLE/PEU 수는 VRB 섹션 레코드 수와 일치해야 함],
    [Sections], [`0x0030`–], [가변], [아래 TLV 섹션 프레이밍 참조. 태그는 오름차순, 중복 없음],
    [File CRC32], [파일 최하단], [4 Bytes], [직전 모든 바이트에 대한 CRC-32 (자기 자신은 제외)]
  )
)

*TLV 섹션 프레이밍:* 각 섹션은 `u16 tag`, `u32 length`, `length` 바이트 페이로드 순으로 연속한다. 태그는 `0x0001`(VRB), `0x0002`(Netlist), `0x0003`(NoC Route), `0x0004`(Analog)이며, *정준 오름차순으로 각각 최대 1회* 등장해야 한다. 각 섹션의 페이로드는 다음 레코드 배열의 단순 연결이다.

#figure(
  caption: [섹션별 레코드 바이트 레이아웃 (참조 구현과 정합)],
  table(
    columns: (1.5fr, 2.2fr, 4.3fr),
    align: (left, left, left),
    table.header([*섹션*], [*레코드 구조체*], [*필드 및 제약*]),
    [VRB\ (`0x0001`)], [`u8 type, u8 k,` `u8 flags, u8 rsv,` `u16 n_init, u16 n_port,` `u32[n_init], u16[n_port]`], [type: `0x01`=GLE-4(k=4, 진리표 1워드, 상위 16비트 0), `0x02`=GLE-6(k=6, 진리표 2워드), `0x03`=PEU(k=0, 진리표 없음, 입력 1개). flags bit0 = 출력 탄성 레지스터. rsv는 0. n_port는 입력 수(k 또는 PEU는 1)와 일치해야 함],
    [Netlist\ (`0x0002`)], [`u16 src, u16 dst,` `u16 src_port,` `u16 dst_port,` `u16 delay`], [src/dst는 VRB 인덱스 범위 내. v1.0에서 모든 VRB의 출력은 단일 포트 0. 동일 (dst, dst_port) 입력이 두 번 구동되면 거부],
    [NoC Route\ (`0x0003`)], [`u16 src_tile, u16 dst_tile,` `u8 n_headers, u8 rsv,` `u32[n_headers]`], [헤더 배열은 *단일 체인 시퀀스*: 첫 헤더는 VC0로 주입, 마지막을 제외한 모든 헤더는 `chained=1`, 마지막은 `chained=0`. VC 승격은 경로 전체에서 최대 1회이며, 승격 이후 헤더는 VC1을 표시. `trace_route()`로 기계 검증됨],
    [Analog\ (`0x0004`)], [`u16 cab_id, u16 reg,` `u8 dtype, u8 rsv,` `u32 value`], [dtype `0x01`=고정 단위 정수. reg는 표 3의 주소. cab_id는 manifest CAB 수 미만. value는 레지스터별 범위 내]
  )
)

= PoC 가상 실행기 및 에뮬레이터 아키텍처 설계 계획

== 3단계 PoC 구현 아키텍처

#align(center)[
  #block(
    fill: rgb("#f1f5f9"),
    inset: 12pt,
    radius: 4pt,
    stroke: 0.8pt + rgb("#cbd5e1"),
    breakable: false
  )[
    #text(size: 9pt, weight: "bold")[ORA PoC 계층별 구현 및 검증 파이프라인]
    #v(0.4em)
    `1. ORA 중립 비트스트림 파서 및 디코더 (Rust / Python 기반 바이너리 해석기)` \
    $arrow.b$ \
    `2. 순환 주기 정밀(Cycle-Accurate) 탄성 데이터플로우 & NoC 시뮬레이터 (C++ / Rust)` \
    `[ 4x4 타일 그리드, Up*/Down* 소스 라우팅, 단조 VC 계층화 데드락 검증 ]` \
    $arrow.b$ \
    `3. CIRCT 프론트엔드 연동 가상 실행기 (MLIR/Handshake 다이얼렉트 코드 매핑)` \
    $arrow.b$ \
    `4. Verilog/Chisel RTL 레퍼런스 타일 합성 및 FPGA 에뮬레이션 실증`
  ]
]

1. *1단계 (바이너리 인터프리터 및 코어 데이터플로우 엔진):*
  - ORA 중립 비트스트림 v1.0 바이너리 파서를 구축하고, 가상 VRB 노드 간의 2선 분산 핸드셰이크 토큰 흐름을 이벤트 구동(Event-Driven) 시뮬레이터로 모델링한다.
2. *2단계 (토폴로지 비종속 NoC 및 무데드락 검증):*
  - 결함 주입 후 연결성을 점검하고 $"Up"^* slash "Down"^*$ 신장 트리와 소스 라우팅 헤더를 *재컴파일*한 뒤 시뮬레이션한다(낡은 라우트로는 배달 불가 링크를 통과할 수 없으므로, 결함 허용성은 라우트 재컴파일로 성립한다). 무데드락의 *1차 증명*은 컴파일된 라우트 전체에서 (방향 링크, VC) 채널 쌍을 노드로, 각 라우트의 연속 홉을 간선으로 갖는 채널 의존성 그래프(CDG)의 비순환성 정적 검사로 수행하고(밀리초 단위), 100만 회 패킷 인젝션 시뮬레이션은 보조 확인으로 사용한다. 승격은 VC0→VC1 단방향이므로 VC0 내부 순환, VC1 내부 순환, 역방향 전이가 모두 없음을 확인한다.
3. *3단계 (혼성 신호 경계 및 AER 이벤트 루프 검증):*
  - 아날로그 적분기 ODE 상태 전파 모델과 비동기 AER 단일 플릿 통신을 결합하여, 엣지 뉴로모픽 스파이킹 신경망(SNN) 추론 벤치마크를 가상 실행기 상에서 완결한다.
