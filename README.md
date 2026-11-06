# ORA: Open Reconfigurable Architecture

ORA(Open Reconfigurable Architecture)는 연산 소자와 반도체 공정에 묶이지 않는 개방형 재구성 가능 컴퓨팅 패브릭 표준을 목표로 한다. 이 저장소에는 다음이 들어 있다.

- 표준 명세 초안 (Typst)
- 명세의 핵심 가설을 검증하는 Python PoC
- SpinalHDL 레퍼런스 RTL과 Verilator co-simulation
- 실물 생산 단계를 위한 구성 메모리 셀 실험 노트

> **상태:** 초안·PoC 단계다. 명세와 비트스트림 형식은 아직 확정되지 않았다.

## 표준 계층

| 계층 | 역할 |
|------|------|
| V-HAL | 물리 소자를 감추는 가상 하드웨어 추상화 계층. 중립 넷리스트를 32비트 워드 바이트코드 비트스트림으로 직렬화한다 |
| ORA-D | 기본 디지털 패브릭. 가상 LUT, 가상 스위치, 탄성 버퍼로 지연 무관(latency-insensitive) Valid/Ready 데이터플로우를 구성한다 |
| ORA-N | 토폴로지 비종속 NoC. 32비트 플릿, 무테이블 소스 라우팅, 단조 VC 계층화로 불규칙 토폴로지에서도 데드락을 막는다 |
| ORA-A | 아날로그 확장. 구성 가능 아날로그 블록(CAB)을 트랜지스터 기하 구조가 아닌 연속 시간 전달 함수와 지배 미분 방정식으로 기술해 공정에서 분리한다 |
| ORA-M | 혼성 신호 경계. ADC, DAC, 비교기 등 연속–이산 신호 경계와 전기적 격리를 정한다 |

자세한 내용은 `docs/`의 명세를 본다.

## 저장소 구조

```text
docs/
  ora_specification_typst_document.typ  ORA 표준 명세 및 참조 모델
  ora_poc_standard_specification.typ    PoC 상세 기술 표준 규격서 v1.0
                                        (ORA-D, ORA-N, ORA-A/M, V-HAL 바이너리 레이아웃)
  ora_poc_architecture_plan.md          PoC 설계 계획, 마일스톤 S1–S4와 진행 현황
  references.bib                        참고 문헌
poc/
  ora_bitstream/   V-HAL 중립 바이트코드 비트스트림 v1.0 참조 인코더/디코더
  ora_fabric/      패브릭 그래프(M1), 탄성 코어(M2), ORA-N 라우터(M3), 검증 하네스(M4)
  ora_rtl/         SpinalHDL 레퍼런스 RTL(OraRouterCore, OraRouter)과 co-sim 환경
experiments/
  config_cell_classes.typ               구성 메모리 셀 클래스 실물 실험 노트 (표준 아님)
```

## PoC 검증 가설과 현황

| # | 가설 | 검증 방법 |
|---|------|-----------|
| H1 | 중립 비트스트림이 물리 구현과 독립적으로 직렬화·복원된다 | v1.0 바이너리 인코딩·디코딩 (CRC 2중 검증), 무작위 넷리스트 왕복 손실 0 |
| H2 | 무테이블 소스 라우팅과 단조 VC 계층화가 불규칙 토폴로지에서 무데드락이다 | 컴파일된 라우트의 채널 의존성 그래프(CDG) 정적 비순환 검사, 결함 주입 후 시뮬레이션 |
| H3 | Valid/Ready 탄성 파이프라인이 슬랙 탄력성을 제공한다 | 임의 경로에 FIFO를 0→N개 넣어도 토큰 시퀀스(기능 결과)가 같음 |

현재 결과 (아래 명령으로 재현할 수 있다):

| 범위 | 결과 |
|------|------|
| `ora_bitstream` 단위 테스트 | 46건 통과 |
| `ora_fabric` 단위·통합 테스트 (H1–H3 하네스 포함) | 60건 통과 |
| RTL 단일 채널 코어 `OraRouterCore` 대 Python 골든 모델 | 8/8 시나리오 트레이스 일치 |
| RTL 다중 포트 라우터 `OraRouter` 2개 체인 대 골든 모델 | 9/9 시나리오 트레이스 일치 |

남은 한계는 다음과 같다 (`docs/ora_poc_architecture_plan.md` 참조).

- RTL co-sim 토폴로지는 2-라우터 선형 체인뿐이다.
- 로컬 배출(eject)은 항상 수신 가능하다고 가정한다.
- 합성, 타이밍, 면적은 평가하지 않았다.

## 빠른 시작

필요한 도구는 다음과 같다.

- [uv](https://docs.astral.sh/uv/): Python 3.14 환경을 자동으로 준비한다.
- [Typst](https://typst.app/): 명세와 실험 노트를 렌더링할 때 필요하다.
- [Podman](https://podman.io/)과 [just](https://just.systems/): RTL co-sim에만 필요하다. sbt, SpinalHDL, Verilator는 컨테이너 안에서 실행된다.

### Python PoC 테스트

```sh
cd poc/ora_bitstream && uv run --with pytest pytest -q
cd ../ora_fabric    && uv run --with pytest pytest -q
```

### RTL co-simulation

먼저 RTL 개발 이미지를 한 번 빌드한다.

```sh
cd poc/ora_rtl
podman build -t ora-rtl -f Containerfile .
cd ../..
```

그다음 저장소 루트에서 co-sim을 실행한다.

```sh
just --justfile poc/ora_rtl/cosim.just cosim-all     # 두 스위트 모두
just --justfile poc/ora_rtl/cosim.just cosim         # 단일 채널 코어만
just --justfile poc/ora_rtl/cosim.just cosim-chain   # 2-라우터 체인만
```

co-sim은 다음 순서로 진행된다.

1. 호스트의 Python 골든 모델로 시나리오와 기준 트레이스를 만든다.
2. 컨테이너 안에서 SpinalHDL로 Verilog를 생성한다.
3. 생성한 Verilog를 Verilator로 빌드한다.
4. 시뮬레이션 결과 트레이스를 기준 트레이스와 비교한다.

### 문서 렌더링

```sh
typst compile docs/ora_specification_typst_document.typ
typst compile docs/ora_poc_standard_specification.typ
typst compile experiments/config_cell_classes.typ
```

생성된 PDF는 Git에서 추적하지 않는다 (`.gitignore`).

## 구성 메모리 셀 실험 노트

`experiments/config_cell_classes.typ`는 실물 생산 단계에서 검토할 구성 메모리 셀 후보와 위험 요소를 정리한 노트다. ORA 표준의 일부가 아니며, 비트스트림 형식은 셀 종류와 무관하게 중립으로 유지한다.

| 클래스 | 구성 |
|--------|------|
| Type 0 | CMOS SRAM 래치 계열. 하위형은 0-A (6T), 0-B (10T), 0-C (12T), 0-D (16T+)이고, 여기에 비휘발 부분을 결합한 0-xN이 있다 |
| Type I–V | 교차 결합 2-사이리스터 래치에 비휘발 차동 쌍을 붙인 계열. 비휘발 쌍은 PCM, SOT-MTJ, AlScN 강유전체, 1차 상전이 자성체, 2차 상전이·스핀-포논 결합 재료 중 하나다 |

노트의 수치는 출처 수준을 함께 적는다.

- 초록 확인
- 본문 확인
- 검색 요약 기준
- 가설
- 계산

## 개발 작업 공간 파일

다음 파일은 개발 에이전트 작업 공간과 프로젝트 간 통신 기록을 위한 것이며, ORA 표준이나 PoC의 일부가 아니다.

- 루트의 `justfile`
- 루트의 `pyproject.toml` (`oh-my-pi-workspace`)
- `.omp/`
- `.local-requests-*`, `.local-replies-*`, `.local-mentions-by/`

## 라이선스

이 저장소는 [BSD-2-Clause-Patent](https://opensource.org/license/BSD-2-Clause-Patent) 라이선스(SPDX 식별자 `BSD-2-Clause-Patent`)로 배포된다. 전문은 [`LICENSE`](LICENSE)에 있다. 별도 표기가 없는 한, 코드와 문서를 포함한 저장소의 모든 파일에 적용된다.

- BSD 2-Clause 조건을 그대로 따른다. 재배포할 때 저작권 표시, 조건 목록, 면책 조항을 유지해야 한다.
- 여기에 명시적인 특허 허락이 더해진다. 각 저작권자와 기여자는 자신의 기여물, 그리고 기여 시점에 그 기여물과 결합된 저작물이 필연적으로 침해하는 특허 청구항에 대해 무상·영구·취소 불가(조건 위반 시 제외)의 특허 사용권을 부여한다.

기여물은 같은 라이선스로 받는다.

이 저장소가 사용하는 외부 도구와 라이브러리는 각자의 라이선스를 따른다. 대표적으로 SpinalHDL, Verilator, sbt, Python 패키지가 있다. 문서에 인용한 문헌의 저작권은 각 저자와 출판사에 있다.
