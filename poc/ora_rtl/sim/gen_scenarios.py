"""Scenario generator for ORA-N co-simulation (Python golden model side).

Models the RTL contract exactly:
  - One flit offered per cycle, held until the router accepts it
  - The East link is drained every cycle when out_ready=1 (matching the
    RTL testbench's always-ready sink) and forced full when out_ready=0
  - STALL events are logged when the offered flit is not accepted

Writes, per scenario:
  <name>.stim          : one 32-bit flit per line (RTL stimulus)
  <name>.ready         : out_ready bit per cycle (RTL testbench input)
  <name>.ref.trace     : "cycle FWD|EJECT|STALL ..." lines (golden reference)
"""

from __future__ import annotations

import os
import sys

from ora_bitstream import (
    FLIT_TYPE_BODY,
    FLIT_TYPE_TAIL,
    VC0,
    NO_VC_TRANSITION,
    PORT_EAST,
    pack_header_flit,
    pack_single_flit_aer,
)
from ora_fabric.router import NoCRouter

EAST_IN_PORT = 3  # PORT_SOUTH (input side of the neighbor)


def set_link_ready(nbr: NoCRouter, ready: bool) -> None:
    """Emulate the RTL link's ready signal on the neighbor's input buffers.

    ready=True  -> buffers drained (RTL always-ready sink consumes everything)
    ready=False -> buffers forced full (can_receive() returns False)
    """
    for key in nbr.in_buffers:
        nbr.in_buffers[key].clear()
        if not ready:
            for _ in range(nbr.buffer_depth):
                nbr.in_buffers[key].append(0)  # dummy filler


def golden_trace(stimulus: list[int], ready_pattern: str) -> list[str]:
    """Run the Python golden model under the RTL handshake contract.

    The offered flit enters the router's input buffer once and is re-evaluated
    every cycle until it is consumed (forwarded, ejected, or dropped as a
    chained header). A cycle where it is not consumed logs STALL, matching
    the RTL's inp.ready gating.
    """
    r = NoCRouter(tile_id=0)
    nbr = NoCRouter(tile_id=1)
    r.connect(PORT_EAST, nbr, EAST_IN_PORT)

    lines: list[str] = []
    idx = 0
    total = len(stimulus)
    in_router = False

    for cyc in range(4 * total + 64):
        out_ready = ready_pattern[cyc % len(ready_pattern)] == "1"
        set_link_ready(nbr, out_ready)

        # Offer the next flit once the previous one was consumed
        if not in_router and idx < total:
            accepted = r.receive_flit(0, stimulus[idx])  # 0 = PORT_LOCAL
            if accepted:
                in_router = True
            else:
                lines.append(f"{cyc} STALL")
                continue

        if not in_router:
            # Nothing pending: drain any in-flight state, then check exit
            r.evaluate_cycle()
            r.commit_cycle()
            if idx >= total and not r.ejection_queue:
                break
            continue

        # The offered flit sits at the head of the input buffer; evaluate.
        dropped_before = r.chained_headers_dropped
        r.evaluate_cycle()
        fwd = r.staged_tx[PORT_EAST][2] if PORT_EAST in r.staged_tx else None
        ejec = r.ejection_queue[0] if r.ejection_queue else None
        r.commit_cycle()

        consumed = (
            fwd is not None
            or ejec is not None
            or r.chained_headers_dropped > dropped_before
        )

        if consumed:
            in_router = False
            idx += 1
            if ejec is not None:
                r.ejection_queue.popleft()
            parts = [str(cyc)]
            if fwd is not None:
                parts.append(f"FWD {fwd:08x}")
            if ejec is not None:
                parts.append(f"EJECT {ejec:08x}")
            if len(parts) > 1:
                lines.append(" ".join(parts))
        else:
            # The router did not consume the flit this cycle (out_ready low
            # or equivalent): it stays at the buffer head for a retry.
            lines.append(f"{cyc} STALL")

    return lines


def body(word: int) -> int:
    return (FLIT_TYPE_BODY << 30) | (VC0 << 28) | word


def tail(word: int) -> int:
    return (FLIT_TYPE_TAIL << 30) | (VC0 << 28) | word


def hdr(hops: int, dv: list[int], chained: bool = False, trans: int = NO_VC_TRANSITION) -> int:
    return pack_header_flit(vc_id=VC0, hop_count=hops, chained=chained,
                           vc_transition_hop=trans, direction_vector=dv)


SCENARIOS: dict[str, tuple[list[int], str]] = {
    # name: (stimulus flits, ready pattern per cycle)
    "hdr_fwd_2hop": ([hdr(2, [PORT_EAST, PORT_EAST])], "1"),
    "chained_pair": ([hdr(1, [PORT_EAST], chained=True),
                     hdr(1, [PORT_EAST])], "1"),
    "hdr_eject": ([hdr(1, [PORT_EAST]),
                  hdr(0, [])], "1"),
    "wormhole_4flit": ([hdr(1, [PORT_EAST]), body(0x111), body(0x222), tail(0x333)], "1"),
    "vc_promotion": ([hdr(3, [PORT_EAST] * 3, trans=0), body(0xAAA), tail(0xBBB)], "1"),
    "aer_single": ([pack_single_flit_aer(hop_count=1, direction_vector=[PORT_EAST],
                                        neuron_address=0xABCDE)], "1"),
    # Extended: >4 flits to exercise neighbor-buffer backpressure
    "long_stream_12flit": ([hdr(4, [PORT_EAST] * 4)] +
                            [body(0x100 + i) for i in range(10)] +
                            [tail(0x999)], "1"),
    # Extended: out_ready drops periodically (every 4th cycle not ready)
    "backpressure_rdy1110": ([hdr(2, [PORT_EAST, PORT_EAST])] +
                             [body(0x200 + i) for i in range(8)] +
                             [tail(0x777)], "1110"),
}


def main() -> None:
    outdir = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(__file__), "scenarios")
    os.makedirs(outdir, exist_ok=True)

    for name, (stimulus, rdy) in SCENARIOS.items():
        stim_path = os.path.join(outdir, f"{name}.stim")
        with open(stim_path, "w") as f:
            for flit in stimulus:
                f.write(f"{flit:08x}\n")

        rdy_path = os.path.join(outdir, f"{name}.ready")
        with open(rdy_path, "w") as f:
            f.write(rdy)

        lines = golden_trace(stimulus, rdy)
        ref_path = os.path.join(outdir, f"{name}.ref.trace")
        with open(ref_path, "w") as f:
            for ln in lines:
                f.write(ln + "\n")
        n_stall = sum(1 for ln in lines if "STALL" in ln)
        print(f"{name}: {len(stimulus)} flits, ready='{rdy}' -> "
              f"{len(lines)} events ({n_stall} stalls)")


if __name__ == "__main__":
    main()
