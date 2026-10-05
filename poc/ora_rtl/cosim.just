# ORA-N co-simulation: RTL (Verilator in Podman) vs Python golden model
#
# Usage: just --justfile poc/ora_rtl/cosim.just cosim [scenario]        # single-channel core
#        just --justfile poc/ora_rtl/cosim.just cosim-chain [scenario]  # 2x multi-port OraRouter
#        just --justfile poc/ora_rtl/cosim.just cosim-all

default: cosim-all

# Both co-simulation suites; fails if either fails
cosim-all:
    #!/usr/bin/env bash
    set -uo pipefail
    just --justfile "{{justfile()}}" cosim; a=$?
    just --justfile "{{justfile()}}" cosim-chain; b=$?
    echo "core suite: $([ $a -eq 0 ] && echo PASS || echo FAIL), chain suite: $([ $b -eq 0 ] && echo PASS || echo FAIL)"
    exit $(( a | b ))

# Full co-simulation pipeline: scenarios -> SpinalHDL -> Verilator -> diff
cosim scenario="":
    #!/usr/bin/env bash
    set -euo pipefail
    cd "{{justfile_directory()}}"   # -> poc/ora_rtl/

    # 1. Regenerate scenarios + reference traces (host Python, ora_fabric env)
    (cd ../ora_fabric && uv run python ../ora_rtl/sim/gen_scenarios.py ../ora_rtl/sim/scenarios)

    # 2. Regenerate Verilog from SpinalHDL (inside the Podman container)
    podman run --rm -v "$PWD":/work:Z -w /work localhost/ora-rtl \
      sbt -batch "runMain ora.OraRouterCoreVerilog" >/dev/null

    # 3. Verilate + build the RTL simulator (inside the Podman container)
    podman run --rm -v "$PWD":/work:Z -w /work/sim localhost/ora-rtl \
      verilator --cc --exe --build -Wno-fatal \
        --top-module OraRouterCore \
        ../generated/OraRouterCore.v \
        tb_main.cpp \
        -o sim_router \
        --Mdir obj_dir

    # 4. Run each scenario inside the container and diff traces
    fail=0
    for stim in sim/scenarios/*.stim; do
      case "$stim" in *.chain.stim) continue ;; esac   # handled by cosim-chain
      name=$(basename "$stim" .stim)
      if [ -n "{{scenario}}" ] && [ "$name" != "{{scenario}}" ]; then continue; fi

      rdy="sim/scenarios/$name.ready"
      echo "=== scenario: $name (ready=$(cat "$rdy")) ==="

      podman run --rm -v "$PWD":/work:Z -w /work localhost/ora-rtl \
        ./sim/obj_dir/sim_router "$stim" "sim/scenarios/$name.rtl.trace" "$(cat "$rdy")"

      if diff -q "sim/scenarios/$name.ref.trace" "sim/scenarios/$name.rtl.trace" >/dev/null; then
        echo "  MATCH"
      else
        echo "  MISMATCH:"
        # `|| true`: with pipefail, head closing early SIGPIPEs diff and set -e would abort the loop
        diff "sim/scenarios/$name.ref.trace" "sim/scenarios/$name.rtl.trace" | head -n 10 || true
        fail=1
      fi
    done

    exit $fail

# 2-router chain co-simulation of the multi-port OraRouter (R0.EAST <-> R1.WEST)
cosim-chain scenario="":
    #!/usr/bin/env bash
    set -euo pipefail
    cd "{{justfile_directory()}}"   # -> poc/ora_rtl/

    # 1. Golden traces from ora_fabric.router.NoCRouter (host Python)
    (cd ../ora_fabric && uv run python ../ora_rtl/sim/gen_chain_scenarios.py ../ora_rtl/sim/scenarios)

    # 2. Verilog from SpinalHDL (inside the Podman container)
    podman run --rm -v "$PWD":/work:Z -w /work localhost/ora-rtl \
      sbt -batch "runMain ora.OraRouterVerilog" >/dev/null

    # 3. Verilate two-instance testbench (inside the Podman container)
    podman run --rm -v "$PWD":/work:Z -w /work/sim localhost/ora-rtl \
      verilator --cc --exe --build -Wno-fatal \
        --top-module OraRouter \
        ../generated/OraRouter.v \
        tb_chain.cpp \
        -o sim_chain \
        --Mdir obj_chain

    # 4. Run each scenario inside the container and diff traces
    fail=0
    for stim in sim/scenarios/*.chain.stim; do
      name=$(basename "$stim" .chain.stim)
      if [ -n "{{scenario}}" ] && [ "$name" != "{{scenario}}" ]; then continue; fi
      echo "=== chain scenario: $name ==="

      podman run --rm -v "$PWD":/work:Z -w /work localhost/ora-rtl \
        ./sim/obj_chain/sim_chain "$stim" "sim/scenarios/$name.chain.rtl.trace"

      if diff -q "sim/scenarios/$name.chain.ref.trace" "sim/scenarios/$name.chain.rtl.trace" >/dev/null; then
        echo "  MATCH ($(wc -l < "sim/scenarios/$name.chain.ref.trace") events)"
      else
        echo "  MISMATCH:"
        # `|| true`: with pipefail, head closing early SIGPIPEs diff and set -e would abort the loop
        diff "sim/scenarios/$name.chain.ref.trace" "sim/scenarios/$name.chain.rtl.trace" | head -n 12 || true
        fail=1
      fi
    done

    exit $fail
