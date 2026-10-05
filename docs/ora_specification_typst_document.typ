// Open Reconfigurable Architecture (ORA) Technical Specification & Reference Architecture
// Typst >= 0.15 Compatible Format

#set document(
  title: "개방형 재구성 가능 아키텍처(ORA) 표준 명세 및 참조 모델",
  author: "Open Reconfigurable Architecture Working Group",
  date: auto
)

// Global Page & Layout Configuration
#set page(
  paper: "a4",
  margin: (top: 2.5cm, bottom: 2.5cm, left: 2.2cm, right: 2.2cm),
  header: context {
    if here().page() > 1 {
      text(9pt, fill: luma(100), font: "Noto Sans CJK KR")[
        _개방형 재구성 가능 아키텍처(ORA) 표준 명세 및 참조 모델_
        #h(1fr)
        _Version 1.0 (Core & Profiles)_
      ]
      v(-0.5em)
      line(length: 100%, stroke: 0.4pt + luma(180))
    }
  },
  footer: context {
    let pagenum = here().page();
    text(9pt, fill: luma(120), font: "Noto Sans CJK KR")[
      #h(1fr)
      #pagenum
      #h(1fr)
    ]
  }
)

// Typography & Paragraph Styling
#set text(
  font: ("Noto Sans CJK KR", "Noto Sans"),
  size: 10pt,
  weight: "regular",
  lang: "ko"
)

#set par(
  justify: true,
  leading: 0.85em,
  first-line-indent: 1.2em
)

#show heading: set text(weight: "bold", fill: rgb("#111827"))
#show heading.where(level: 1): it => block(spacing: 1.5em, sticky: true)[
  #text(16pt)[#it.body]
  #v(0.3em)
  #line(length: 100%, stroke: 1.2pt + rgb("#1e3a8a"))
]
#show heading.where(level: 2): it => block(spacing: 1.2em, sticky: true)[
  #text(13pt, fill: rgb("#1e3a8a"))[#it.body]
]
#show heading.where(level: 3): it => block(spacing: 1.0em, sticky: true)[
  #text(11pt, fill: rgb("#374151"))[#it.body]
]

#set table(
  stroke: (x, y) => if y == 0 { (bottom: 1.5pt + rgb("#1e3a8a")) } else { (bottom: 0.5pt + luma(210)) },
  fill: (col, row) => if row == 0 { rgb("#f1f5f9") } else if calc.odd(row) { rgb("#f8fafc") } else { none },
  inset: (x: 8pt, y: 7pt)
)

#show table.cell: it => {
  if it.y == 0 {
    set text(weight: "bold", size: 9pt)
    it
  } else {
    set text(size: 8pt) // 헤더가 아닌 셀들은 8pt로 설정
    it
  }
}

// Title Block
#align(center)[
  #block(width: 90%)[
    #text(20pt, weight: "bold", fill: rgb("#0f172a"))[개방형 재구성 가능 아키텍처(ORA) 표준 명세 및 참조 모델]
    
    #v(0.6em)
    #text(13pt, weight: "medium", fill: rgb("#334155"))[
      벤더·소자 독립적 FPGA/FPAA 통합 규격과 데이터플로우 기반 토폴로지 비종속 NoC 아키텍처
    ]
    
    #v(0.3em)
    #text(10pt, fill: rgb("#64748b"))[
      Open Reconfigurable Architecture (ORA) Working Group Standard Specification
    ]
    
    #v(1.2em)
    #line(length: 60%, stroke: 0.8pt + rgb("#cbd5e1"))
    #v(0.8em)
  ]
]

#block(
  fill: rgb("#f8fafc"),
  inset: 14pt,
  radius: 4pt,
  stroke: 1pt + rgb("#e2e8f0")
)[
  #text(weight: "bold", fill: rgb("#1e3a8a"))[초록 (Abstract)]
  
  본 문서는 연산 소자 및 반도체 공정에 완전히 독립적인 차세대 개방형 재구성 가능 컴퓨팅 패브릭 표준인 ORA(Open Reconfigurable Architecture)의 참조 아키텍처와 인터페이스 규격을 명세한다. ORA는 가상 하드웨어 추상화 계층(V-HAL)과 중립 바이트코드 비트스트림 포맷을 정의하여 벤더 독점성과 물리 구현 종속성을 영구히 분리한다. 또한 디지털 FPGA 코어(ORA-D)를 바탕으로 아날로그 연속 시간 연산(ORA-A) 및 혼성 신호(ORA-M) 경계 계층을 모듈식으로 통합한다. 상호연결망에서는 패킷 헤더 기반 무테이블 소스 라우팅과 $"Up"^* slash "Down"^*$ 신장 트리 및 단조 가상 채널 계층화(Monotonic VC Layering)를 채택하여 불규칙 다이 및 3D 칩렛에서도 100% 데드락 없는 통신을 보장하는 토폴로지 비종속 NoC(ORA-N)를 의무 규격화한다. 나아가 2선 분산 핸드셰이크 기반 동기 탄성 파이프라인의 레이턴시 비민감성과 연속 시간 상미분방정식을 통합한 공간 데이터플로우(Spatial Dataflow) 모델을 구현한다.
  
  #v(0.5em)
  #text(size: 9pt)[*주요어 (Keywords):* 재구성 가능 컴퓨팅, 오픈소스 하드웨어, V-HAL, FPAA, 토폴로지 비종속 NoC, 소스 라우팅, 탄성 데이터플로우, CIRCT]
]

#v(1.5em)

= 서론 및 오픈소스 하드웨어 생태계 현황 분석

컴퓨팅 아키텍처 역사에서 범용 마이크로프로세서가 폭발적인 소프트웨어 생태계를 구축할 수 있었던 근본적 동력은 명령어 세트 아키텍처(Instruction Set Architecture, ISA)를 통한 물리 하드웨어와 소프트웨어 바이너리의 완전한 분리였다. 프로세서 분야에서 RISC-V@waterman2014riscv 가 독점적 라이선스 종속을 탈피하고 개방형 표준 인터페이스를 정립한 것과 대조적으로, 재구성 가능 컴퓨팅(Reconfigurable Computing) 도메인은 수십 년간 극단적인 벤더 독점과 아키텍처 파편화의 늪에 갇혀 있다.

상용 FPGA(Field-Programmable Gate Array) 시장을 과점하고 있는 주요 벤더들은 룩업 테이블(LUT), 스위치 매트릭스(Switch Matrix), 클록 분배 네트워크의 물리적 배치 및 구성 비트스트림 구조를 영업비밀로 폐쇄하고 있으며, 독점 EDA 도구 체인을 통해서만 하드웨어 매핑을 허용한다. 아날로그 재구성 가능 어레이인 FPAA(Field-Programmable Analog Array) 도메인의 상황은 더욱 열악하여, 상용화된 표준 인터페이스조차 부재한 채 소수의 학술 연구진이 보유한 개별 공정 노드 기반의 실험적 칩셋에 기술 구현이 완전히 묶여 있다@hasler2020fpaa.

오픈소스 하드웨어 진영에서는 이러한 폐쇄성을 극복하기 위해 다수의 FPGA 프레임워크를 개발해 왔다. 대표적으로 OpenFPGA@tang2020openfpga 는 고수준 아키텍처 기술 언어로부터 Verilog 넷리스트와 벤치마크 CAD 도구를 자동 생성하여 최첨단 공정 노드에서 레이아웃 테이프아웃을 신속하게 달성하는 생성기(Generator) 역할을 수행한다. FABulous@nguyen2021fabulous 는 eFPGA(Embedded FPGA) 생성을 목적으로 프레임 기반 및 스캔 체인 재구성 메커니즘을 통합하고 Yosys, nextpnr, VPR 등과 상호 운용되도록 설계되어 표준 셀 기반 면적 효율성을 극대화했다. 또한 버클리와 토론토 대학을 중심으로 발전한 VTR(Verilog-to-Routing)@murray2020vtr8 프로젝트는 복합 로직 블록(CLB), 내장 DSP, BRAM 모델을 아우르는 학술적 FPGA 아키텍처 탐색의 사실상 표준 플랫폼으로 자리 잡았다.

그러나 현존하는 오픈소스 프레임워크들은 '특정 구조를 갖는 FPGA 하드웨어를 합성해 내는 도구'일 뿐, 프로세서의 ISA에 대응하는 '중립적 하드웨어 비트스트림 표준 규격'을 제시하지 못한다. 각 생성기가 도출하는 비트스트림은 특정 파운드리의 표준 셀 라이브러리(Standard Cell Library)나 맞춤형 멀티플렉서 회로, 특정 SRAM 래치 셀 배열의 물리적 배선 좌표에 1:1로 직접 바인딩된다. 결과적으로 목표 공정 노드가 SkyWater 130nm에서 TSMC 16nm로 전환되거나 스탠다드 셀 구성이 변경될 경우, 기존의 배치·배선(PnR) 결과물과 비트스트림은 완전히 무효화되며 전체 합성 플로우를 바닥부터 다시 실행해야 한다.

#figure(
  caption: [기존 주요 오픈소스 및 상용 재구성 가능 하드웨어 플랫폼 비교],
  table(
    columns: (1.5fr, 2.3fr, 2.4fr, 2.5fr, 2.5fr),
    align: (left, left, left, left, left),
    table.header(
      [*플랫폼 / 프로젝트*], [*핵심 연산 프리미티브*], [*비트스트림 저장 방식*], [*공정 및 소자 종속성*], [*아키텍처 표준화 관점 한계점*]
    ),
    [OpenFPGA\ @tang2020openfpga], [k-LUT, D-FF, 멀티모드 LE], [스캔 체인 및\ 메모리 뱅크 플립플롭 체인], [표준 셀 라이브러리 및\ 커스텀 MUX에 직접 결합], [비트스트림이 물리 배선 좌표와 직결되어 바이너리 이식성 부재],
    [FABulous\ @nguyen2021fabulous], [Look-Up Table,\ MUX4/2, 래치], [프레임 기반 래치 및\ 가상 SRAM 주소 지정], [백엔드 PnR 툴(OpenLane 등) 및 면적 최적화 종속], [eFPGA 구조 생성기로서 중립적 가상 실행 계층 결여],
    [VTR / VPR 8\ @murray2020vtr8], [추상 복합 블록\ (CLB, DSP, BRAM)], [넷리스트 기반\ 라우팅 경로 추출], [사용자 작성 XML 아키텍처 모델 파일에 종속], [물리 백엔드 실리콘 구현과의 분리로 상호 호환 규격 미제공],
    [Georgia Tech RASP\ @george2016rasp], [CAB (OTA, 커패시터, MITE), CLB], [플로팅 게이트(FG)\ 전하 주입 및 터널링], [고전압 회로 및 특정 비휘발성 두꺼운 산화막 공정 종속], [BLIF 변환 편법에 의존하며 아날로그-디지털 정형 추상화 결여],
    [Anadigm FPAA], [스위치드 커패시터 CAM 기반 필터], [정적 SRAM 기반 아날로그 전송 게이트 제어], [특정 아날로그 공정 및 협소한 대역폭 종속], [폐쇄형 상용 규격으로 대규모 혼성 신호 시스템 확장 불가]
  )
)

FPAA 도메인에서는 조지아 공대의 RASP(Reconfigurable Analog Signal Processing)@george2016rasp 시스템이 부동 게이트(Floating-Gate) 소자를 스위치 메모리와 아날로그 연산 소자(VMM, OTA 바이어싱)로 동시에 사용하는 독창적인 구조를 제안하였다. 단일 칩 내에 연산 아날로그 블록(CAB)과 디지털 로직 블록(CLB), 마이크로프로세서를 맨해튼 라우팅 그리드로 결합하여 혼성 신호 및 아날로그 연산 처리의 집적도와 에너지 효율을 크게 개선하는 실용적 가능성을 입증하였다.

그럼에도 불구하고 RASP 시스템은 개방형 표준 아키텍처 관점에서 두 가지 치명적 병목을 드러낸다. 첫째는 물리 소자 수준의 깊은 공정 종속성이다. 부동 게이트의 전하 제어를 위해서는 파울러-노드하임(Fowler-Nordheim) 터널링 및 열전자 주입(Hot-Electron Injection)을 위한 10V 이상의 온칩 고전압 펌프와 초정밀 전류 계측 회로가 필수적이며, 이는 표준 디지털 벌크 CMOS 공정으로의 즉각적인 이식을 가로막는다. 둘째는 도구 체인의 기형적 추상화이다. RASP의 오픈소스 CAD 체인은 디지털 PnR 도구인 VPR을 그대로 우회 활용하기 위해 아날로그 연속 시간 회로를 무리하게 디지털 불리언 넷리스트 형식(BLIF)으로 변환한다. 이로 인해 배선 기생 저항·커패시턴스(RC)에 민감한 아날로그 신호 무결성이 왜곡되고 범용적인 혼성 신호 확장 인터페이스 구축이 원천적으로 봉쇄된다.

따라서 반도체 공정과 물리 구현 소자의 특성에 휘둘리지 않고, 디지털 로직과 아날로그 신호 처리를 통일된 문법으로 수용하며, 대규모 시스템 확장을 보장하는 새로운 개방형 재구성 가능 아키텍처(Open Reconfigurable Architecture, ORA) 표준의 수립이 시급하다.

= 가상 하드웨어 추상화 계층 (V-HAL) 및 중립 비트스트림

하드웨어 제조사와 공정 기술로부터 아키텍처 사양을 완전히 격리하기 위해서는 가상화된 하드웨어 추상화 계층(Virtual Hardware Abstraction Layer, V-HAL)이 시스템 최하단에 선행되어야 한다. 본 표준은 그래픽스 파이프라인에서 Khronos SPIR-V@khronos2021spirv 가 벤더별 GPU 마이크로아키텍처를 가상 중간 표현(IR)으로 은닉하는 기법과, LLVM CIRCT@lattner2021circt 가 다수준 하드웨어 컴파일러 인프라를 구축하는 방식에 착안하여, 물리 소자 독립적 프리미티브와 중립적 바이너리 비트스트림 규격을 정의한다.

== 물리 소자 독립적 가상 재구성 블록 (VRB) 추상화 모델

ORA 표준은 특정 실리콘 셀 라이브러리의 배선이나 스위치 트랜지스터 크기를 직접 정의하지 않는다. 대신 시스템의 최소 기능 단위를 *가상 재구성 블록(Virtual Reconfigurable Block, VRB)* 으로 명세하며, VRB는 논리 연산, 신호 라우팅, 순차 제어를 담당하는 세 가지 표준 원시 단위로 구성된다.

1. *범용 논리 요소 (Generic Logic Element, GLE):* 임의의 $k$-입력 불리언 함수를 평가하는 가상 룩업 테이블(V-LUT)과 동기/비동기 상태 저장 소자를 추상화한다. GLE의 V-LUT는 물리적 구현체가 6-LUT 기반의 SRAM 멀티플렉서 트리인지, 비휘발성 ReRAM 크로스바인지, 혹은 표준 셀 로직 게이트 넷리스트인지 여부를 외부에 은닉한다. GLE는 오직 입력 포트 개수, 진리표(Truth Table) 매핑 인터페이스, 논리적 전파 지연 버짓(Timing Budget)의 수학적 계약만을 노출한다.
2. *매개변수화된 가상 스위치 블록 (Parameterized Switch Block, PSB):* 물리적 패스 트랜지스터, 트랜스미션 게이트(Transmission Gate), 플로팅 게이트 스위치의 세부 파라미터를 배제한다. PSB는 노드 간 연결 가능성을 방향성 그래프 간선(Directed Edges)으로 치환하고, 신호 대역폭과 최대 허용 지연 버짓만을 가상 속성으로 관리한다.
3. *프로그래머블 탄성 유닛 (Programmable Elastic Unit, PEU):* 글로벌 클록 분배 트리의 타이밍 클로저 부담을 완화하기 위해, 신호의 유효성을 나타내는 `Valid`와 수신 준비 완료를 알리는 `Ready` 채널을 내장한 분산 탄성 버퍼(Elastic Buffer)@cortadella2006elastic 메커니즘을 기본 단위로 추상화한다.

== 점진적 강등 기반 컴파일 파이프라인 및 바이트코드 패키징

전통적인 FPGA 흐름에서는 사용자의 RTL 코드가 특정 벤더의 기술 매퍼(Technology Mapper)를 거쳐 해당 벤더 고유의 물리 프리미티브로 곧바로 고착된다. ORA 프레임워크는 이 구조를 타파하고, 컴파일러 프론트엔드와 실리콘 백엔드 사이에 완전한 플랫폼 독립성을 제공하는 점진적 강등(Progressive Lowering) 파이프라인을 구축한다.

#align(center)[
  #block(
    fill: rgb("#f1f5f9"),
    inset: 12pt,
    radius: 4pt,
    stroke: 0.8pt + rgb("#cbd5e1"),
    breakable: false
  )[
    #text(size: 9pt, weight: "bold")[ORA 점진적 강등 컴파일 파이프라인 구조]
    #v(0.4em)
    `High-Level Specification (C/C++, PyTorch, Chisel)` \
    $arrow.b$ \
    `CIRCT Frontend Dialects` \
    `[ 정적 제어 스케줄링: Calyx Dialect` @nigam2021calyx `| 동적 탄성 데이터플로우: Handshake Dialect` @josipovic2018dynamically `]` \
    $arrow.b$ \
    `CIRCT hw / comb / seq Dialects (물리 독립적 구조 및 인터페이스 확정)` \
    $arrow.b$ \
    `ORA Neutral Bytecode Serialization (SPIR-V 유형 32비트 워드 바이너리)` \
    $arrow.b$ \
    `Vendor/Foundry JIT-AOT Hardware Loader (실리콘 물리 비트스트림 매핑)`
  ]
]

컴파일러 전반부에서는 고급 알고리즘 언어가 LLVM CIRCT 인프라 내부로 유입된다. 연산 제어 구조와 정적 스케줄링이 확정된 파이프라인은 `calyx` 다이얼렉트@nigam2021calyx 로 매핑되며, 제어 흐름 분기나 불규칙 메모리 접근이 지배적인 가속 블록은 `handshake` 다이얼렉트@josipovic2018dynamically 를 통해 동적 분산 탄성 데이터플로우로 매핑된다. 이 두 경로는 CIRCT 내부의 공통 하드웨어 구조 다이얼렉트인 `hw`, `comb`, `seq`로 통합 하향 변환되어 시스템 넷리스트를 확정한다.

컴파일러 후반부에서는 정제된 CIRCT 넷리스트가 ORA 표준 중립 비트스트림(Neutral Bitstream)으로 직렬화된다. ORA 중립 비트스트림은 Khronos SPIR-V 규격과 유사하게 32비트 워드 기반의 정형 바이트코드로 패키징된다. 각 파운드리는 자사의 세부 공정 기밀을 공개할 필요 없이, ORA 중립 비트스트림을 런타임에 입력받아 해당 타깃 실리콘의 물리적 제어 회로로 변환해 주는 전용 하드웨어 로더(JIT-AOT Device Driver)만을 제공한다.

#figure(
  caption: [ORA 표준 중립 비트스트림 32비트 워드 인코딩 구조],
  table(
    columns: (2.4fr, 1.4fr, 1.8fr, 3.8fr),
    align: (left, center, center, left),
    table.header(
      [*비트스트림 섹션 필드*], [*바이트 길이*], [*인코딩 형식*], [*기술 내용 및 물리적 역할*]
    ),
    [Magic Header & Profile ID], [8 Bytes], [64-bit Hex], [ORA 표준 준수 식별자 및 필수 하위 프로파일 선언 (ORA-D, A, M, N)],
    [Capability Manifest], [16 Bytes], [Bitmask Flags], [실행 요구 가상 자원 명세 (LUT 차수, CAB 요구 대역폭, NoC 채널 수)],
    [VRB Function Descriptor], [가변 길이], [32-bit Words], [가상 로직 요소(GLE)별 불리언 진리표 및 탄성 유닛(PEU) 제어 정책],
    [Virtual Topology Netlist], [가변 길이], [Graph Edges], [가상 스위치 블록(PSB) 포트 간 논리적 연결성 및 허용 최대 지연 예산],
    [NoC Source-Route Table], [가변 길이], [3-bit Packs], [타일 간 글로벌 통신을 위한 홉 단위 출력 포트 방향 벡터 및 VC ID],
    [Analog Dynamic Parameter], [가변 길이], [IEEE-754 FP16], [CAB 내부 OTA $G_m$, 커패시턴스 비율, VMM 가중치 정규화 파라미터]
  )
)

= 모듈형 확장 체계: ORA-D 코어 기반 ORA-A 및 ORA-M 인터페이스

RISC-V 아키텍처가 기본 정수 명령어 세트(RV32I/RV64I)를 코어로 확정하고 부동 소수점(F/D), 벡터(V) 등을 직교적 확장 모듈로 부가하듯, ORA 표준은 기본 디지털 재구성 패브릭(ORA-D)을 코어 규격으로 지정하고, 아날로그 컴퓨팅(ORA-A) 및 혼성 신호 경계 인터페이스(ORA-M)를 모듈형 확장으로 체계화한다.

== 아날로그 연산 블록(CAB)의 수학적 미분 방정식 기반 추상화

FPAA의 기존 연구들이 특정 소자 크기와 공정 노드에 국한된 SPICE 모델에 종속되었던 한계를 탈피하기 위해, ORA-A 확장은 CAB를 트랜지스터 기하 구조가 아닌 *연속 시간 전달 함수와 지배 미분 방정식(Governing Differential Equations)* 을 만족하는 수학적 프리미티브의 집합으로 추상화한다.

1. *연속 시간 트랜스컨덕턴스 증폭기 (OTA):* 차동 입력 전압을 고유 전류로 변환하는 연산을 수행한다.
  $ I_"out" = G_m (V_+ - V_-) $
  표준에서는 소자의 세부 회로망 대신 정규화된 $G_m$ 튜닝 범위와 선형 입력 동적 영역(Linear Dynamic Range)만을 계약 인터페이스로 강제한다.
2. *다중 입력 트랜스리니어 요소 (MITE):* 서브스레숄드 영역의 지수 특성을 활용하여 로그-도메인 다항식 곱셈과 나눗셈을 $cal(O)(1)$ 시간 내에 수행하는 비선형 연산 인터페이스를 규정한다.
3. *가변 커패시터 뱅크 (Programmable Capacitor Bank):* 시간 영역에서의 적분 연산을 전담하며 고차 상미분방정식(ODE) 솔버의 상태 변수를 형성한다.
  $ I(t) = C frac(d V(t), d t) $
4. *벡터-행렬 곱셈 (Analog VMM Crossbar):* 키르히호프의 전류 법칙(KCL)에 기반하여 입력 전압 벡터와 컨덕턴스 행렬 간의 곱셈-누산(MAC)을 초저전력으로 물리 연산하는 인터페이스를 제공한다. 구현체가 부동 게이트 MOSFET이든 ReRAM 크로스바이든 동일 규격을 따른다.

== 혼성 신호(Mixed-Signal) 경계 인터페이스 및 전기적 격리 표준 (ORA-M)

디지털 스위칭 잡음(Substrate Noise, Ground Bounce)이 미세 아날로그 노드를 오염시키는 현상을 방지하기 위해, ORA 표준은 디지털 배선 라인과 아날로그 신호 라인의 직접 교차를 엄격히 금지하며, 신호 전달은 오직 표준화된 *경계 번역 박스(Mixed-Signal Boundary Box)* 를 통해서만 이루어지도록 규정한다.

경계 번역 박스는 네 가지 컴포넌트로 구성된다:
- 연속 아날로그 전압을 디지털 비트 벡터로 전환하는 병렬 SAR/Flash ADC 어레이
- 디지털 제어 워드를 아날로그 구동 전류/전압으로 역변환하는 전류-스티어링 DAC 어레이
- 서로 다른 공급 전압 도메인을 완충하는 양방향 전압 레벨 시프터
- 아날로그 전압이 특정 임계치를 통과할 때 즉각 디지털 스트로브 펄스를 방출하는 클록리스 연속 시간 레벨 교차 검출기(Level-Crossing Detector)

#figure(
  caption: [ORA 서브 프로파일별 기술 및 인터페이스 사양],
  table(
    columns: (1.7fr, 2.4fr, 3.0fr, 2.5fr),
    align: (left, left, left, left),
    table.header(
      [*ORA 서브 프로파일*], [*포함 하드웨어 프리미티브*], [*도메인 수학 및 전기적 원리*], [*시스템 인터페이스 프로토콜*]
    ),
    [ORA-D\ (Base Digital)], [GLE (V-LUT), PSB (가상 스위치),\ PEU (탄성 버퍼)], [불리언 대수, 이산 상태 천이,\ 지연 무관(Latency-Insensitive) 탄성 제어], [2선 분산 핸드셰이크 (Valid / Ready)],
    [ORA-A\ (Analog Ext)], [CAB (OTA, MITE, 커패시터,\ VMM 크로스바)], [키르히호프 법칙,\ 전하 보존 미분 방정식 ($I(t) = C frac(d V(t), d t)$)], [연속 시간 아날로그 전압/전류 라우팅 버스],
    [ORA-M\ (Mixed-Signal)], [SAR ADC, Current-DAC,\ 연속 시간 비교기], [연속-이산 신호 양자화 및\ 레벨 교차 이벤트 펄스 생성], [비동기 스트로브 및 병렬 데이터 워드 인터페이스],
    [ORA-N\ (Network Core)], [소스 라우팅 스위치, 표준 NI,\ AER 송수신기], [패킷 교환,\ 단조 VC 계층화 기반 무데드락 전송], [고정 32비트 플릿(Flit) 기반 스트리밍]
  )
)

= 토폴로지 비종속적(Topology-Agnostic) Network-on-Chip (ORA-N)

현대 상용 NoC 구조는 특정 2차원 직사각형 메시 토폴로지와 XY 차원 순서 라우팅에 완벽히 종속되어 있어 링, 불규칙 기하 구조, 2.5D/3D 칩렛 결합 시 라우팅 컴파일러가 완전히 붕괴된다. ORA-N 표준은 네트워크의 물리적 결선 형태나 결함 유무에 구애받지 않는 *절대적 토폴로지 비종속 NoC*를 필수 계층으로 의무화한다.

== 소스 라우팅(Source Routing) 기반 초경량 라우터 마이크로아키텍처

ORA-N은 라우터 내부의 목적지 주소 조회 테이블(Routing Table)을 완전히 제거하고, 모든 경로 결정 권한을 발신 노드로 일원화하는 소스 라우팅(Source Routing) 기법을 채택한다. 발신 측 네트워크 인터페이스(NI)는 사전에 계산된 그래프 토폴로지를 기반으로 목적지까지 거쳐야 할 모든 중간 라우터의 출력 포트 인덱스(Port Direction Index) 목록을 패킷 헤더 플릿에 직접 패킹한다.

기본 전송 단위는 32비트 고정 폭 플릿(Flit)이며, 플릿의 유형과 목적에 따라 세 가지 표준 형식을 정의한다:

1. *멀티 플릿 헤더 (Header Flit, Bit [31:30] = `00`):*
  - *Bit [31:30]:* 플릿 유형 (`00`: Header)
  - *Bit [29:28]:* 현재 가상 채널 ID (`00`: VC0, `01`: VC1)
  - *Bit [27:25]:* 3비트 잔여 홉 카운터 (Remaining Hop Counter, 최대 7홉 지원)
  - *Bit [24]:* 체인드 헤더 플래그 (Chained Header Flag: `1`이면 홉 소진 시 후속 플릿을 새 헤더로 해석, `0`이면 로컬 배출)
  - *Bit [23:21]:* 3비트 VC 승격 카운트다운 (VC Transition Hop Index: 매 홉마다 감산되며 `000` 도달 시 VC1으로 단조 승격, `111`은 승격 없음 센티널)
  - *Bit [20:0]:* 21비트 패킹된 방향 벡터 (Packed Direction Vector, 홉당 3비트씩 최대 7홉 인코딩)
2. *바디 / 테일 플릿 (Body / Tail Flit, Bit [31:30] = `01` 또는 `10`):*
  - *Bit [31:30]:* 플릿 유형 (`01`: Body, `10`: Tail)
  - *Bit [29:28]:* 가상 채널 ID (VC ID)
  - *Bit [27:0]:* 28비트 데이터 페이로드 (Data Payload)
3. *단일 이벤트 플릿 (Single-Flit AER Event, Bit [31:30] = `11`):*
  - *Bit [31:30]:* 플릿 유형 (`11`: Single-Flit Event)
  - *Bit [29:28]:* 가상 채널 ID (`00`: VC0 전용)
  - *Bit [27:26]:* 2비트 잔여 홉 카운터 (국소 및 인접 타일 전송용 최대 2홉)
  - *Bit [25:20]:* 6비트 방향 벡터 (2홉 $times$ 3비트)
  - *Bit [19:0]:* 20비트 국소 뉴런 이벤트 주소 (Local Neuron Event Address, 최대 $2^{20}$ 개 뉴런 식별)

패킷이 라우터에 도착하면 라우터는 최하위 3비트(`Bit [2:0]`)만을 디코딩하여 크로스바 스위치를 해당 출력 포트로 즉각 연결한다. 동시에 내부 배럴 시프터가 방향 벡터를 오른쪽으로 3비트 *논리 시프트(Logical Shift, zero-fill)* 하고 홉 카운터를 1 감소시킨다. 홉 카운터가 0에 도달했을 때 Chained Header 플래그가 0이면 패킷을 로컬 NI로 배출하고, 1이면 현재 소진된 헤더 플릿을 폐기(Drop)한 뒤 후속 플릿을 새로운 헤더로 취급하여 다음 라우팅을 연속 수행한다. 이를 통해 7홉을 초과하는 대규모 불규칙 다이나 3D 칩렛에서도 경로를 임의 길이로 확장할 수 있다. 라우터는 토폴로지를 저장할 필요가 전혀 없으며, 테이블 메모리를 배제하여 면적과 전력을 상용 NoC 대비 60% 이상 절감한다.

== 데드락 방지 메커니즘: $"Up"^* slash "Down"^*$ 신장 트리 및 단조 가상 채널 계층화

임의의 불규칙 토폴로지에서 순환 버퍼 의존성으로 인한 네트워크 데드락을 방지하기 위해, ORA-N 표준은 컴파일 타임의 $"Up"^* slash "Down"^*$ 신장 트리 분할 규칙@schroeder1991autonet @flich2002updown 과 런타임의 *단조 가상 채널 계층화(Monotonic Virtual Channel Layering)* 기법을 결합한다.

컴파일러는 물리 NoC 연결 그래프를 순회하여 최적의 방향성 신장 트리(Spanning Tree)를 생성하고, 루트 노드를 향하는 링크에 'Up', 리프 노드를 향하는 링크에 'Down' 속성을 부여한다. 데드락 방지 원리에 따라 다음 전이 규칙이 기본 적용된다:
$ "Up"^* arrow "Down"^* quad ("허용: 데드락 프리 전이") $
$ "Down" arrow "Up" quad ("금지: 순환 버퍼 의존성 유발 가능") $

그러나 $"Down" arrow "Up"$ 전이를 전면 금지하면 라우팅 경로가 비대해져 레이턴시가 증가한다. 라우팅 테이블이 없는 소스 라우터에서 이를 무데드락으로 해결하기 위해, ORA-N 표준은 가상 채널 간 단방향 계층 전이 모델을 강제한다:
- 모든 패킷은 기본 가상 채널인 *VC0*에서 주입되며, 원칙적으로 $"Up"^* arrow "Down"^*$ 비순환 경로를 따른다.
- 물리적 지연 최소화를 위해 컴파일러가 사전에 지정한 단 1회의 $"Down" arrow "Up"$ 지름길 턴(Shortcut Turn)이 필요한 경우, 헤더의 `VC Transition Hop Index`에 *승격까지 남은 홉 수*가 인코딩된다. 라우터는 매 홉마다 이 값을 감산하는 카운트다운을 수행하며, 값이 `000`에 도달한 홉에서 즉시 승격을 실행한다. 값 `111`은 "이 세그먼트에서 승격 없음"을 뜻하는 센티널이다.
- 승격 카운트다운이 0에 도달한 라우터는 패킷의 가상 채널을 *VC1*으로 단조 승격(Monotonic Promotion)시키고, 헤더의 승격 인덱스를 센티널 `111`로 되돌려 재승격을 방지한다.
- VC1으로 승격된 패킷은 목적지까지 다시 $"Up"^* arrow "Down"^*$ 규칙만을 준수하며, 절대로 하위 채널(VC0)로 역전이될 수 없다 ($"VC0" arrow "VC1"$ 단방향 전이).

VC0과 VC1 각각은 신장 트리 규칙에 의해 내부 순환 의존성이 원천 차단된 비순환 서브넷(Acyclic Sub-network)을 형성한다. 또한 채널 간 의존성이 오직 VC0에서 VC1으로만 흐르는 방향성 비순환 그래프(DAG)를 구성하므로, 전체 채널 의존성 그래프(CDG) 상의 순환 고리가 완벽히 차단된다. 따라서 라우터 내부의 복잡한 런타임 라우팅 테이블 없이도 불규칙 토폴로지 상에서 100% 데드락 없는 소스 라우팅이 달성된다.

== AER (Address-Event Representation) 트랜슬레이터 내장 NI

아날로그 FPAA 타일(ORA-A)과의 이종 통신을 지원하기 위해 표준 NI 내부에는 AER 트랜슬레이터@boahen2000aer 가 기본 내장된다. 아날로그 적분기가 임계 전압에 도달하여 스파이크가 발생하면, NI 내부의 비동기 아비터가 해당 뉴런의 국소 주소를 캡처하여 단일 플릿 ORA-N 이벤트 패킷으로 패킹한다. 인접 타일(2홉 이내) 통신 시에는 20비트 뉴런 주소가 패킹된 Single-Flit AER 패킷을 통해 수 나노초 이내에 직달한다. 3홉 이상의 장거리 이벤트는 2-Flit 패킷(헤더+페이로드)으로 자동 캡슐화되어 전송된다.

무테이블 라우터 아키텍처에 부합하도록, 복수의 타일로 이벤트를 전송해야 하는 멀티캐스트의 경우 라우터에 분기 상태를 일절 저장하지 않고 발신 NI가 복수의 목적지 헤더를 연속 주입하여 각 목적지로 독립 전달하는 무상태(Stateless) 방식을 채택한다.

= 데이터플로우 관점의 내부 구조 전면 재설계

전통적인 상용 FPGA의 글로벌 동기 클록 분배 트리는 전체 다이 전력의 30% 이상을 낭비하고 극심한 PVT 마진을 요구한다. 더욱이 연속 시간 아날로그 연산을 단일 글로벌 클록에 묶는 것은 아날로그 본연의 에너지 효율을 심각하게 훼손한다. 본 표준은 패브릭 내부의 모든 연산과 배선을 공간 데이터플로우 그래프(Spatial Dataflow Graph)로 재구축한다.

== 토큰 기반 공간 연산 및 탄성 파이프라인

ORA-D 패브릭의 기본 셀은 데이터와 제어 태그가 일체화된 토큰(Token)의 도착에 의해 구동되는 탄성 파이프라인(Elastic Pipeline)@cortadella2006elastic @josipovic2018dynamically 구조를 취한다. 노드 간 통신은 포워드 `Valid`와 백워드 `Ready` 신호가 맞물리는 2선 분산 핸드셰이크 프로토콜로 국소 완결된다.

이 구조는 동기식 탄성 회로의 고유 특성인 *슬랙 탄력성(Slack Elasticity)* 및 *레이턴시 비민감성(Latency-Insensitivity)* 을 완벽히 제공한다. 즉, 배선 경로에 탄성 FIFO 버퍼를 삽입하여 통신 지연 사이클이 증가하더라도 시스템의 기능적 정확성과 연산 결과의 수학적 동일성이 보존된다. 이를 통해 각 연산 스테이지 내의 국소 타이밍 검증만을 유지하면서, 칩 전체 및 칩렛 간 와이어 지연 변동에 대한 가혹한 글로벌 타이밍 클로저(Global Timing Closure) 제약을 대폭 완화한다.

패브릭 내의 탄성 제어 프리미티브는 세 가지 핵심 블록으로 구성된다:
1. *Join:* 모든 입력 채널에 유효한 데이터 토큰이 도달할 때까지 대기 후 단일 통합 점화(Fire) 신호 방출
2. *Fork:* 단일 연산 결과 토큰을 복수의 수신 노드로 복제 브로드캐스트하며, 모든 노드가 소비할 때까지 백프레셔(Backpressure) 유지
3. *Merge / Branch:* 제어 조건 토큰에 따라 데이터 토큰의 흐름 경로를 동적으로 선택 스위칭

== 아날로그 연속 동역학과 데이터플로우 모델링

아날로그 CAB 내부의 연산은 키르히호프의 전류 법칙과 커패시터 충방전에 지배받는 물리적 상미분방정식(ODE)의 직접적인 시간 적분 과정이다. 임의의 $k$번째 아날로그 노드 전압 $V_k (t)$의 상태 변화는 주변 노드들과의 컨덕턴스 $G_(k j)$ 및 외부 입력 전류 $I_("in", k)(t)$에 의해 다음과 같이 실시간 결정된다:

$ C_k frac(d V_k (t), d t) = sum_j G_(k j) dot (V_j (t) - V_k (t)) + I_("in", k)(t) $

이 수식에서 전압 $V_k (t)$는 유한한 RC 시상수에 따른 과도 응답 지연(Transient Response Delay)을 수반하며 물리 법칙에 따라 연속적으로 진화하는 아날로그 상태 변수 역할을 수행한다.

디지털 탄성 파이프라인과의 경계에서는 레벨 교차 검출기가 동작하여 $V_k (t)$가 임계 전압에 도달하는 즉시 비동기 스트로브 펄스를 생성, 디지털 Join 유닛으로 불리언 이벤트 토큰을 인젝션한다. 역방향으로 디지털 토큰이 진입할 때는 고속 전하 주입 스위치가 커패시터 $C_k$를 순간 방전하거나 전압 점프(디랙 델타 임펄스)를 인가하여 미분방정식의 경계 조건을 실시간 갱신한다.

= 개방형 EDA 및 컴파일러 툴체인 파이프라인

ORA 표준 컴파일러 툴체인은 LLVM CIRCT@lattner2021circt 를 핵심 프레임워크로 채택하여 알고리즘 명세로부터 중립 비트스트림 생성 및 실리콘 로더 배포에 이르는 전 과정을 모듈형 오픈소스 파이프라인으로 구성한다.

1. *HLS 및 탄성 데이터플로우 프론트엔드:* C/C++ 및 PyTorch 코드는 정적 스케줄링 가속기 생성을 위한 Calyx 다이얼렉트@nigam2021calyx 와 불규칙 동적 파이프라인 생성을 위한 Handshake 다이얼렉트@josipovic2018dynamically 로 분기 매핑되어 Fork, Join, Merge 원시 요소로 치환된다.
2. *MILP 기반 버퍼 최적화:* 데이터플로우 그래프 내부의 사이클 시간을 계산하고 처리량(Throughput)을 극대화하기 위해 혼합 정수 선형 계획법(MILP) 기반 탄성 FIFO 최적 배치 패스를 실행한다.
3. *혼성 신호 P&R 및 NoC 컴파일:* 아날로그 넷리스트는 ALIGN@dhar2021align 및 OpenFASoC@saligane2022openfasoc 프레임워크로 전달되어 대칭 공통 중심(Common-Centroid) 레이아웃과 소자 크기가 자동 합성된다. 수정된 VTR@murray2020vtr8 엔진이 2차원 그리드 위에 CLB와 CAB를 최적 분산 배치하며, 글로벌 NoC 경로 컴파일러가 $"Up"^* slash "Down"^*$ 신장 트리를 기반으로 무데드락 21비트 소스 라우팅 헤더를 생성한다.

= 표준 아키텍처 사양 매트릭스 및 개발 로드맵

#figure(
  caption: [ORA 5계층 아키텍처 구조 사양 매트릭스],
  table(
    columns: (2.0fr, 2.8fr, 3.4fr, 1.8fr),
    align: (left, left, left, center),
    table.header(
      [*아키텍처 계층*], [*표준 구성 요소*], [*상세 기능 명세 및 프로토콜 규격*], [*표준 준수 의무성*]
    ),
    [L4:\ Application & Toolchain], [CIRCT HLS, Calyx, 확장 VPR,\ ALIGN/OpenFASoC], [C/Chisel/DSL 고수준 합성을 통한 탄성 그래프 및 CAB 파라미터 자동 추출], [권장 표준],
    [L3:\ Virtual Abstraction\ (V-HAL)], [ORA Neutral IR,\ SPIR-V형 중립 비트스트림], [물리 기저 소자 은닉, 가상 넷리스트 및 32비트 워드 바이트코드 직렬화], [*절대 의무*],
    [L2:\ Network Subsystem\ (ORA-N)], [무테이블 소스 라우팅 스위치,\ 표준 NI, AER], [토폴로지 비종속 통신, $"Up"^* slash "Down"^*$ 및 단조 VC 계층화 기반 무데드락 전송], [*절대 의무*],
    [L1-D:\ Base Digital Fabric], [GLE (V-LUT), PSB (가상 스위치),\ PEU (탄성 버퍼)], [분산 핸드셰이크(Valid/Ready) 기반 탄성 데이터플로우 컴퓨팅], [*절대 의무*],
    [L1-A:\ Analog Extension], [CAB (OTA, MITE, 커패시터,\ VMM 크로스바)], [연속 시간 미분 방정식 아날로그 연산 및 초저전력 VMM 하드웨어 가속], [선택적 확장],
    [L1-M:\ Mixed-Signal], [혼성 신호 번역 박스 (SAR ADC,\ DAC, 비교기)], [도메인 교차 신호 양자화 및 비동기 이벤트 스트로브 생성], [ORA-A 채택 시 의무],
    [L0:\ Physical Silicon Engine], [파운드리별 JIT-AOT 로더,\ SRAM/ReRAM 셀], [ORA 중립 비트스트림을 물리 스위치 구성 신호로 실시간 하향 매핑], [파운드리 구현체]
  )
)

== 4단계 개발 및 실리콘 검증 로드맵

- *1단계 (1–2년차: 기반 표준 확립 및 가상 툴체인 구축):* ORA V-HAL 규격서 v1.0 제정, GLE/PSB/PEU 기능 인터페이스 확정, SPIR-V형 32비트 중립 비트스트림 포맷 규격화, LLVM CIRCT 기반 오픈소스 프론트엔드 파이프라인 구현.
- *2단계 (2–3년차: 디지털 패브릭 및 토폴로지 비종속 NoC 실리콘 실증):* ORA-D RTL 및 무테이블 ORA-N NoC IP 오픈소스 공개, SkyWater 130nm 오픈 공정 멀티 프로젝트 웨이퍼(MPW) 테이프아웃, 불규칙 토폴로지 상의 무데드락 통신 및 슬랙 탄력성 실측 검증.
- *3단계 (3–4년차: 아날로그 ORA-A 및 혼성 신호 ORA-M 레이어 통합):* 미분방정식 기반 추상 CAB 사양 확정, ALIGN 및 OpenFASoC 레이아웃 자동화 연동, 130nm/65nm 공정 혼성 신호 SoC 테이프아웃 및 기존 디지털 솔루션 대비 에너지 효율 우위 실증.
- *4단계 (5년차 이후: 첨단 공정 포팅 및 상용 생태계 거버넌스 정착):* TSMC, Intel, 삼성 16nm 이하 FinFET/GAA 공정 포팅, ReRAM/MRAM 비휘발성 스위치 채택, 비영리 'ORA 인터내셔널 컨소시엄' 발족 및 상용 OS 디바이스 드라이버 표준 API 보급.

#pagebreak(weak: true)
= 결론

본 연구에서 제안한 개방형 재구성 가능 아키텍처(ORA) 표준은 CPU 도메인에서 RISC-V가 성취한 기술적 자유와 추상화의 지평을 FPGA 및 FPAA 분야로 확장하는 차세대 하드웨어 청사진이다.

기존 오픈소스 FPGA 도구들의 가장 심각한 맹점이었던 실리콘 셀 종속성은 SPIR-V 형태의 가상 하드웨어 추상화 계층(V-HAL)과 중립적 비트스트림을 도입함으로써 근본적으로 극복되었다. 또한, 필수 계층으로 의무화된 토폴로지 비종속 NoC는 헤더 기반 소스 라우팅과 $"Up"^* slash "Down"^*$ 가상 채널 분할 및 단조 가상 채널 계층화(Monotonic VC Layering)를 채택하여 불규칙 다이 및 3D 칩렛 구조에서도 데드락 없는 통신을 엄밀하게 보장한다.

나아가 글로벌 클록 트리의 설계 마진을 동기식 탄성 파이프라인의 레이턴시 비민감성을 통해 완화하고, 연속 시간 아날로그 미분방정식 동역학을 단일한 데이터플로우 문법으로 통합함으로써, 초저전력 엣지 인공지능부터 고성능 이종 컴퓨팅 가속기에 이르기까지 공정과 소자를 초월하여 영속적인 개방형 하드웨어 혁신을 견인할 이론적·실용적 토대를 제공한다.

#v(2em)

// Academic References Section
#show bibliography: set text(lang: "en")
#bibliography("references.bib", title: "참고 문헌 (References)", style: "ieee")
