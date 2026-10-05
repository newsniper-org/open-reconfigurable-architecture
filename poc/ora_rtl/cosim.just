# ORA-N co-simulation: RTL (Verilator in Podman) vs Python golden model
#
# Usage: just --justfile poc/ora_rtl/cosim.just cosim [scenario]

default: cosim

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
        diff "sim/scenarios/$name.ref.trace" "sim/scenarios/$name.rtl.trace" | head -n 10
        fail=1
      fi
    done

    exit $fail
