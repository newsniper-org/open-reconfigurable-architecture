"""Golden-model generator for the 2-router chain co-simulation.

Topology (both directions wired):

    R0.EAST (port 2)  <---->  R1.WEST (port 4)

Each router has a local injector on PORT_LOCAL that offers one flit per
cycle, held until the router's input FIFO for the flit's VC has a credit
(start-of-cycle occupancy < depth). The golden model is
ora_fabric.router.NoCRouter, the same code covered by the Python tests.

Per-cycle protocol (identical in tb_chain.cpp):
  1. Injection decision from start-of-cycle credits.
  2. All routers evaluate (start-of-cycle state), then all commit.
  3. Accepted injections are pushed into the PORT_LOCAL FIFOs.

Trace line order per cycle: router ascending; per router an optional
"INJ" line, then one line per output port with a flit, port ascending
(port 0 = local eject):
    <cycle> R<r> INJ <hex>
    <cycle> R<r> P<port> <hex>

Writes, per scenario, into the output directory:
    <name>.chain.stim       : "cycles N" then "<router> <hex>" lines
    <name>.chain.ref.trace  : golden trace
"""

from __future__ import annotations

import os
import sys

from ora_bitstream import (
    FLIT_TYPE_BODY,
    FLIT_TYPE_SINGLE_AER,
    FLIT_TYPE_TAIL,
    NO_VC_TRANSITION,
    PORT_EAST,
    PORT_LOCAL,
    PORT_WEST,
    VC0,
    pack_header_flit,
    pack_single_flit_aer,
)
from ora_fabric.router import NoCRouter

DEPTH = 2  # must match OraRouterVerilog (depth = 2)
NUM_ROUTERS = 2


def flit_vc(f: int) -> int:
    return VC0 if (f >> 30) & 0b11 == FLIT_TYPE_SINGLE_AER else (f >> 28) & 0b11


def build_chain() -> list[NoCRouter]:
    rs = [NoCRouter(tile_id=i, buffer_depth=DEPTH) for i in range(NUM_ROUTERS)]
    rs[0].connect(PORT_EAST, rs[1], PORT_WEST)
    rs[1].connect(PORT_WEST, rs[0], PORT_EAST)
    return rs


def golden_chain(stim: dict[int, list[int]], cycles: int) -> tuple[list[str], dict[str, int]]:
    rs = build_chain()
    pending = {r: list(stim.get(r, [])) for r in range(NUM_ROUTERS)}
    lines: list[str] = []
    stats = {"inj": 0, "inj_stall": 0, "link": 0, "eject": 0, "lock_left": 0}

    for cyc in range(cycles):
        inject: dict[int, int] = {}
        for r in range(NUM_ROUTERS):
            if pending[r]:
                f = pending[r][0]
                if rs[r].can_receive(PORT_LOCAL, flit_vc(f)):
                    inject[r] = pending[r].pop(0)
                else:
                    stats["inj_stall"] += 1

        ej_before = [len(r.ejection_queue) for r in rs]
        for r in rs:
            r.evaluate_cycle()

        for r in range(NUM_ROUTERS):
            if r in inject:
                lines.append(f"{cyc} R{r} INJ {inject[r]:08x}")
                stats["inj"] += 1
            outs: dict[int, int] = {}
            new_ej = list(rs[r].ejection_queue)[ej_before[r]:]
            assert len(new_ej) <= 1, "contract: at most one eject per cycle"
            if new_ej:
                outs[PORT_LOCAL] = new_ej[0]
                stats["eject"] += 1
            for port, (_, _, word) in rs[r].staged_tx.items():
                outs[port] = word
                stats["link"] += 1
            for port in sorted(outs):
                lines.append(f"{cyc} R{r} P{port} {outs[port]:08x}")

        for r in rs:
            r.commit_cycle()
        for r, f in inject.items():
            assert rs[r].receive_flit(PORT_LOCAL, f)
        for r in rs:
            r.ejection_queue.clear()

    leftover = sum(len(p) for p in pending.values())
    leftover += sum(len(b) for r in rs for b in r.in_buffers.values())
    assert leftover == 0, f"scenario did not drain within {cycles} cycles ({leftover} flits left)"
    stats["lock_left"] = sum(len(r.crossbar_locks) for r in rs)
    return lines, stats


# ---------------------------------------------------------------- helpers
def hdr(hops: int, dv: list[int], *, chained: bool = False,
        trans: int = NO_VC_TRANSITION, vc: int = VC0) -> int:
    return pack_header_flit(vc_id=vc, hop_count=hops, chained=chained,
                            vc_transition_hop=trans, direction_vector=dv)


def body(word: int, vc: int = VC0) -> int:
    return (FLIT_TYPE_BODY << 30) | (vc << 28) | (word & 0xFFFFFFF)


def tail(word: int, vc: int = VC0) -> int:
    return (FLIT_TYPE_TAIL << 30) | (vc << 28) | (word & 0xFFFFFFF)


def packet(headers: list[int], payload: list[int]) -> list[int]:
    return headers + [body(w) for w in payload[:-1]] + [tail(payload[-1])]


def aer(hops: int, dv: list[int], addr: int) -> int:
    return pack_single_flit_aer(hop_count=hops, direction_vector=dv, neuron_address=addr)


E, W = PORT_EAST, PORT_WEST

# name -> (stimulus per router, cycles)
SCENARIOS: dict[str, tuple[dict[int, list[int]], int]] = {
    # R0 -> R1 wormhole, ejected at R1
    "chain_fwd_wormhole": (
        {0: packet([hdr(1, [E])], [0x101, 0x102, 0x103, 0x104, 0x105])},
        40,
    ),
    # Simultaneous R0 -> R1 and R1 -> R0 on the two link directions
    "chain_bidir": (
        {0: packet([hdr(1, [E])], [0xA1, 0xA2, 0xA3]),
         1: packet([hdr(1, [W])], [0xB1, 0xB2, 0xB3])},
        40,
    ),
    # R1 sends a U-turn packet (W then E) that is promoted to VC1 at R0;
    # R0's own VC0 packet competes for R0.EAST -> per-port RR alternates
    # VC classes on R0.EAST and again on R1's eject port.
    "chain_uturn_rr": (
        {0: packet([hdr(1, [E])], [0xA0 + i for i in range(6)]),
         1: packet([hdr(2, [W, E], trans=1)], [0xB0 + i for i in range(6)])},
        80,
    ),
    # Same U-turn without promotion: both packets need (R0.EAST, VC0), so the
    # second waits for the first wormhole's Tail (lock contention) while the
    # depth-2 FIFOs back up.
    "chain_uturn_lock": (
        {0: packet([hdr(1, [E])], [0xA0 + i for i in range(6)]),
         1: packet([hdr(2, [W, E])], [0xB0 + i for i in range(6)])},
        80,
    ),
    # AER from R1 bouncing through R0 towards R1 must wait while R0's VC0
    # wormhole holds (R0.EAST, VC0); a local AER at R0 ejects directly.
    "chain_aer_vs_wormhole": (
        {0: packet([hdr(1, [E])], [0xC0 + i for i in range(5)]) + [aer(0, [], 0x5A5A5)],
         1: [aer(2, [W, E], 0x12345)]},
        60,
    ),
    # Chained header: R1 drops the spent header and forwards the successor
    # back West; R0 ejects.
    "chain_chained_hdr": (
        {0: packet([hdr(1, [E], chained=True), hdr(1, [W])], [0xD1, 0xD2])},
        40,
    ),
    # Lone header (no Tail) injected at R1 for itself: it ejects and keeps
    # (R1.LOCAL, VC0) until the next header on R1's local channel triggers
    # the self-release cycle. Meanwhile R0's packet also targets
    # (R1.LOCAL, VC0) and must wait for that lock. (A lone header may never
    # cross a link: the upstream forward lock would never be released.)
    "chain_lone_hdr_selfrel": (
        {0: packet([hdr(1, [E])], [0xE1, 0xE2]),
         1: [hdr(0, [])] + packet([hdr(0, [])], [0xE5, 0xE6])},
        40,
    ),
    # VC promotion on the first hop: the packet travels and ejects on VC1
    "chain_vc_promotion": (
        {0: packet([hdr(1, [E], trans=0)], [0xF1, 0xF2, 0xF3])},
        40,
    ),
    # Lock holder on the HIGH-index channel: R1's U-turn packet enters R0 on
    # EAST (channel 4) and takes (R0.EAST, VC0) first; R0's own E-bound
    # packet (LOCAL, channel 0) is delayed by a self-ejecting packet and
    # arrives while the wormhole is open. Lower index would win arbitration,
    # so only the lock check keeps it out until the U-turn's Tail.
    "chain_lock_holder_high_index": (
        {0: packet([hdr(0, [])], [0x31, 0x32, 0x33]) + packet([hdr(1, [E])], [0xA1, 0xA2]),
         1: packet([hdr(2, [W, E])], [0xB0 + i for i in range(6)])},
        60,
    ),
}


def main() -> None:
    outdir = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(__file__), "scenarios")
    os.makedirs(outdir, exist_ok=True)
    for name, (stim, cycles) in SCENARIOS.items():
        lines, stats = golden_chain(stim, cycles)
        with open(os.path.join(outdir, f"{name}.chain.stim"), "w") as fh:
            fh.write(f"cycles {cycles}\n")
            for r in range(NUM_ROUTERS):
                for f in stim.get(r, []):
                    fh.write(f"{r} {f:08x}\n")
        with open(os.path.join(outdir, f"{name}.chain.ref.trace"), "w") as fh:
            fh.write("\n".join(lines) + "\n")
        print(f"  {name}: {len(lines)} events, inj={stats['inj']} "
              f"inj_stall={stats['inj_stall']} link={stats['link']} "
              f"eject={stats['eject']} locks_left={stats['lock_left']}")


if __name__ == "__main__":
    main()
