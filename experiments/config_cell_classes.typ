// Configuration memory cell classes: physical experiment notes
// NOT part of the ORA standard (docs/). Typst >= 0.15

#set document(
  title: "구성 메모리 셀 클래스: 실물 실험 노트",
  author: "ORA PoC",
  date: auto,
)

#set page(
  paper: "a4",
  margin: (top: 2.0cm, bottom: 2.0cm, left: 1.9cm, right: 1.9cm),
  header: context {
    if here().page() > 1 {
      text(8.5pt, fill: luma(100))[
        _ORA 실물 실험 노트_
        #h(1fr)
        _구성 메모리 셀 클래스 (표준 아님)_
      ]
      v(-0.5em)
      line(length: 100%, stroke: 0.4pt + luma(180))
    }
  },
  footer: context {
    text(8.5pt, fill: luma(120))[#h(1fr) #here().page() #h(1fr)]
  },
)

#set text(font: ("Noto Sans CJK KR", "Noto Sans"), size: 9.5pt, lang: "ko")
#set par(justify: true, leading: 0.75em)
#show link: set text(fill: rgb("#1d4ed8"))
#show heading: set text(weight: "bold", fill: rgb("#111827"))
#show heading.where(level: 1): it => block(spacing: 1.3em, sticky: true)[
  #text(13.5pt)[#it.body]
  #v(0.2em)
  #line(length: 100%, stroke: 1pt + rgb("#1e3a8a"))
]
#show heading.where(level: 2): it => block(spacing: 1.0em, sticky: true)[
  #text(11pt, fill: rgb("#1e3a8a"))[#it.body]
]
#set table(stroke: 0.5pt + luma(190), inset: 5pt)
#show table.cell.where(y: 0): set text(weight: "bold")

#let note(body) = block(
  fill: rgb("#fff7ed"),
  stroke: 0.6pt + rgb("#f59e0b"),
  inset: 9pt,
  radius: 3pt,
  width: 100%,
)[#body]

#align(center)[
  #text(17pt, weight: "bold")[구성 메모리 셀 클래스: 실물 실험 노트]
  #v(0.2em)
  #text(10pt, fill: luma(90))[ORA PoC 실물 생산 단계 검토용]
]

#v(0.6em)
#note[
  *상태:* 실험 계획 초안. ORA 표준(`docs/`)의 일부가 아니다. ORA 비트스트림(V-HAL)은 셀 종류와 무관하게 중립으로 유지하며, 이 문서는 실물 생산 단계에서 검토할 구성 메모리 셀 후보와 위험 요소를 기록한다.

  문헌 인용이 없는 수치는 자릿수 추정(order-of-magnitude)이며 SPICE/TCAD 또는 실측으로 검증해야 한다.
]

= 분류

#table(
  columns: (12%, 30%, 25%, 33%),
  table.header([클래스], [셀], [공정 경로], [주 리스크]),
  [Type 0], [6T SRAM (기준선)], [표준 CMOS (예: SKY130 MPW)], [휘발성: 전원 투입 시 비트스트림 재적재],
  [Type I], [교차 결합 2-사이리스터 + 상보 PCM 쌍], [FD-SOI 계열 + BEOL PCM], [대기 전류, 상보 기록용 독립 히터, 열 크로스토크],
  [Type II], [교차 결합 2-사이리스터 + 상보 SOT-MTJ 쌍], [FD-SOI 계열 + BEOL MTJ], [Mn#sub[3]SnN 배향 성장, 반평행 기준층, 대기 전류],
)

공통 개념: 휘발성 래치(사이리스터 쌍)가 LUT/스위치를 구동하고, 비휘발 차동 쌍이 전원 차단 중 상태를 보존한다(nvSRAM의 "래치 + 그림자 저장소" 패턴). 런타임 재구성은 래치에서만 수행하고, 비휘발 기록은 명시적 commit 동작에서만 수행한다(PCM/MTJ 기록 수명 보호).

벌크 CMOS의 p-n-p-n 구조는 래치업 경로와 같으므로 SOI 계열 공정을 전제로 한다. 선행 사례인 TCCT/T-RAM도 SOI 기반이었다.

= 공통 코어: 교차 결합 2-사이리스터 래치

== 전원 투입 시 동시 래칭 위험

사이리스터는 일단 래칭되면 내부 재생 궤환($alpha_"npn" + alpha_"pnp" >= 1$)으로 스스로 유지되어 게이트가 제어력을 잃는다. 따라서 상대 게이트를 억제하는 교차 결합은 "아직 꺼진 쪽의 트리거"만 막을 수 있고, 양쪽이 이미 ON인 상태는 해소하지 못한다. 이 상태를 벗어나려면 양극 전류를 유지 전류 $I_H$ 미만으로 낮춰야 한다.

== 게이트-캐소드 바이패스 저항 $R_"GK"$

*목적:* 전원 상승 중 차단 접합의 변위 전류 $C_j dot dif V \/ dif t$가 게이트 전류처럼 작용해 양쪽을 동시에 트리거하는 것을 막는다(전력 사이리스터의 emitter short와 같은 원리). 트리거 회피 조건:

$ C_j dot (dif V) / (dif t) dot R_"GK" < V_"BE(on)" approx 0.6 "V" $

*대가:* 유지 전류가 대략 $V_"BE" \/ R_"GK"$만큼 증가한다. 셀마다 한쪽이 항상 ON이므로 칩 대기 전류는 (셀 수) × (증가분)만큼 늘어난다. $C_j approx 0.1$ fF 가정 시 예시(추정):

#table(
  columns: (22%, 22%, 26%, 30%),
  table.header([전원 상승 속도], [$R_"GK"$ 상한], [$I_H$ 증가분], [1천만 셀 대기 전류 증가]),
  [1 V/ns], [약 6 MΩ], [약 0.1 µA/셀], [약 1 A (불가)],
  [1 V/µs], [약 6 GΩ], [약 0.1 nA/셀], [약 1 mA],
)

결론: $R_"GK"$와 전원 상승 속도 규격은 함께 설계해야 한다. 상승 속도를 느리게 강제할수록 저항을 크게 잡을 수 있고 대기 전력이 줄어든다. MΩ 이상은 일반적인 TaN 박막 면저항으로는 셀 면적이 과도해질 수 있으므로, 고저항 폴리실리콘, 고질소 TaN, 트랜지스터 블리더를 함께 검토한다.

*한계:* 대칭 저항은 동시 트리거 확률을 낮출 뿐 승자를 정하지 않는다.

== 공통 전류 제한 (보조 수단)

두 양극을 공통 전류원(또는 공유 부하)으로 묶어 $I_H < I_"tail" < 2 I_H$로 두면 양쪽이 동시에 유지 전류를 확보할 수 없다. 이 전류원은 셀당 대기 전류의 상한 역할도 한다.

#note[
  *주의:* 이것만으로 승자가 보장되지 않는다. 두 소자가 잘 정합되어 있으면 양쪽이 동시에 $I_"tail" \/ 2 < I_H$로 떨어져 함께 꺼진 뒤 재트리거되거나, 느리게 수렴하는 준안정 상태에 머물 수 있다. 한쪽으로의 수렴은 비휘발 쌍이 만드는 비대칭 또는 의도적으로 설계한 오프셋에 의존한다.
]

== 전원 투입 복원 순서

전원 투입 경쟁은 결함이 아니라 복원 메커니즘으로 쓴다. 비휘발 쌍의 저항 차이가 저저항 쪽 사이리스터를 먼저 트리거하도록 조향한다.

+ Gate inhibit 유지, 양극 전원 OFF
+ Read Line으로 비휘발 쌍에 바이어스 인가 (차동 조향)
+ 양극 전원을 규격 $dif V \/ dif t$ 이하로 상승: 저저항 쪽이 먼저 래칭되고 교차 결합이 상대를 억제
+ *검증 판독 후 실패 시 1단계부터 재시도 (필수 단계)*
+ Gate inhibit 해제

*설계 조건:* 비휘발 쌍의 저항 비가 사이리스터 간 공정 편차($V_T$, $I_H$, 도핑)보다 충분히 커야 한다.

== Execute Line 신호 레벨

사이리스터 출력은 전류 또는 다이오드 강하 근처 전압이므로, LUT 먹스 게이트를 직접 레일 투 레일로 구동하기 어려울 가능성이 높다. 셀당 버퍼/레벨 시프터 필요 여부와 그 면적 비용을 측정 항목에 포함한다.

== 선행 사례

TCCT/T-RAM(Nemati & Plummer)은 SOI 기반 박막 사이리스터 메모리로, 온도에 따른 이득 변화와 도핑 편차가 상용화 장벽이었다고 보고된다.

- F. Nemati, J. D. Plummer, "A novel thyristor-based SRAM cell (T-RAM) for high-speed, low-voltage, giga-scale memories", IEDM 1999. #link("https://www.semanticscholar.org/paper/A-novel-thyristor-based-SRAM-cell-(T-RAM)-for-Nemati-Plummer/901312e72f9bec1f8c26b94f81e37d8e6ca73823")[Semantic Scholar]
- Hot Chips 19 T-RAM 발표 자료. #link("https://old.hotchips.org/wp-content/uploads/hc_archives/hc19/3_Tues/HC19.05/HC19.05.02.pdf")[PDF]

= Type I: 상보 PCM 쌍

- *상보 기록에는 PCM별 독립 히터가 필요하다.* SET(길고 낮은 펄스)과 RESET(짧은 용융·급냉 펄스)은 파형이 다르므로, 히터 하나를 공유하면 두 셀이 같은 열 이력을 받아 상보 상태를 만들 수 없다. 독립 히터는 단자 수를 늘린다.
- 간접 가열식 4단자 PCM은 RF 스위치 분야에 선례가 있으나, 직접 가열보다 기록 전력·시간이 크고 인접 셀 열 크로스토크가 커진다.
- *Projection liner:* 저항 드리프트 계수를 약 0.06에서 0.003 수준으로 낮춘 실증이 있다(Koelmans et al., Nat. Commun. 6, 8181 (2015), #link("https://pubmed.ncbi.nlm.nih.gov/26333363/")[PubMed]). 그러나 주 대상은 다중 레벨/아날로그 셀이다.
  - 상보 이진 쌍에서는 드리프트가 비정질 쪽 저항을 높여 판독 창을 오히려 넓힌다.
  - liner는 비정질 영역을 우회하는 션트이므로 SET/RESET 판독 창을 좁힌다. 이는 복원 조향 조건(저항 비 > 공정 편차)과 충돌한다.
  - 권고: Type I에서는 제외하거나 비교 실험용 변형으로만 둔다.
- *매트릭스 재료:* 열 집중과 수평 열 간섭 차단에는 열전도도가 낮은 재료가 필요하다. DLC는 sp#super[2]/sp#super[3] 비에 따라 열전도도가 높거나 부분 전도성을 띨 수 있으므로 실측 확인이 필요하다.
- *기록 수명:* PCM 기록 수명은 대략 10#super[8]–10#super[9]회로 알려져 있어, 비휘발 기록은 commit 시에만 수행한다.

= Type II: 상보 SOT-MTJ 쌍

- SOT는 읽기/쓰기 경로가 구조적으로 분리되는 3단자 소자라서 단자 분리 목표에 자연스럽게 맞는다.
- *상보 기록:* 같은 채널·같은 전류 방향·같은 $sigma_z$라면 두 자유층이 같은 방향으로 반전된다. 해법 후보는 다음과 같다.
  - (a) 두 MTJ의 기준층을 반평행으로 고정 (인접 SAF 반대 피닝, 공정 난이도 높음)
  - (b) U자형 채널로 두 셀 아래 전류 방향을 반대로 구성
- *Mn#sub[3]SnN 무자기장 SOT:* 클러스터 자기 팔중극에서 나온 $sigma_z$로 무자기장 반전이 실증되었고 임계 전류 밀도는 약 $9 times 10^6$ A/cm#super[2]이다(You et al., Nat. Commun. 12, 6524 (2021), #link("https://pubmed.ncbi.nlm.nih.gov/34764284/")[PubMed]). 채널 단면 100 nm × 10 nm 기준 약 90 µA로 셀 구동기가 감당할 수 있는 수준이다(계산).
  - *최대 리스크:* 실증은 단결정 기판 위 (110) 에피 박막이며, $sigma_z$는 전류가 팔중극 방향과 평행($J parallel T$)할 때만 생긴다. 비정질 BEOL 절연막 위 다결정 성장에서는 결정립 방향이 무작위라 $sigma_z$가 평균적으로 상쇄되어 메커니즘 자체가 사라질 수 있다.
  - 확인 실험: ≤400 °C BEOL 조건에서 배향 성장(시드층, 템플릿) 가능성, 그리고 MgO MTJ 적층과의 통합.
- *절연/장벽 재료:*
  - a-BN: 3 nm에서 $k approx 1.78$ (100 kHz), 600 °C 1시간 Co 확산 차단, 400 °C 증착(Hong et al., Nature 582, 511 (2020), #link("https://pr.ibs.re.kr/handle/8788114/7820")[IBS]). BEOL 장벽으로 근거가 있다.
  - F-BNNS의 "$k < 2.0$ + 초고열전도" 동시 달성은 확인 필요. 저유전율 요인(비정질화, 불소화, 공극)은 대개 열전도도도 낮추며, h-BN의 높은 열전도는 결정질 면내 방향에 한정된다.
  - 불소는 MgO 및 자성 금속 계면에 부식성이 있으므로 a-BN 장벽으로 감싸는 설계는 타당하다.

= 측정 항목 (셀 공통)

#table(
  columns: (20%, 80%),
  table.header([항목], [내용]),
  [래칭 특성], [$I_H$, 트리거 전압, 온도 의존성 (−40 °C – 125 °C)],
  [동시 래칭률], [전원 상승 속도 × $R_"GK"$ 매트릭스에서 양쪽 ON 발생 빈도],
  [복원 성공률], [비휘발 쌍 저항 비 대비 복원 정확도, 재시도 횟수 분포, 준안정 지속 시간],
  [대기 전류], [셀당 ON 측 전류, 온도 의존성],
  [기록], [비휘발 commit 에너지/시간, 상보 기록 정확도, 인접 셀 교란],
  [수명], [기록 수명, 보존 시간(온도 가속)],
  [구동], [Execute Line 출력 레벨, 버퍼 필요 여부],
)

= ORA와의 접점 (참고)

이 실험 결과가 확정되면, 셀 종류에 따라 달라지는 값만 장치 프로파일 형태로 노출하는 방안을 검토한다. 비트스트림 형식은 바꾸지 않는다.

#table(
  columns: (28%, 72%),
  table.header([후보 필드], [의미]),
  [`cell_class`], [Type 0 / I / II],
  [`t_restore`], [전원 인가 후 비휘발 → 래치 복원 시간],
  [`t_commit`, `E_commit`], [래치 → 비휘발 기록 시간/에너지],
  [`endurance_max`], [비휘발 기록 허용 횟수],
  [`retention`], [보존 기간과 온도 조건],
)

이 표는 표준 반영 결정이 아니라 후보 목록이다.
