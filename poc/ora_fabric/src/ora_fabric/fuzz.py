"""H1 fuzz harness: random bitstream encode/decode round-trip equivalence.

Property: for any structurally valid OraBitstream, encode() followed by
decode() yields an equal bitstream. Run with a bounded RNG for reproducibility.
"""

from __future__ import annotations

import random

from ora_bitstream import (
    OraBitstream,
    Manifest,
    VrbRecord,
    EdgeRecord,
    RouteRecord,
    AnalogRecord,
    VRB_GLE4,
    VRB_GLE6,
    VRB_PEU,
    VRB_FLAG_PEU_OUT,
    PROFILE_ORA_D,
    PROFILE_ORA_A,
    PROFILE_ORA_M,
    PROFILE_ORA_N,
    CAB_OTA_GM,
    CAB_CAP_BANK,
    CAB_MITE_BIAS,
    CAB_VMM_CFG,
    VC0,
    VC1,
    pack_header_flit,
    NO_VC_TRANSITION,
    MAX_HEADER_HOPS,
    PORT_NORTH,
    PORT_EAST,
    PORT_SOUTH,
    PORT_WEST,
    PORT_UP,
    PORT_DOWN,
)


def random_routes(rng: random.Random, num_routers: int, count: int) -> list[RouteRecord]:
    """Generate random structurally valid routes (no deadlock guarantee needed for H1)."""
    routes: list[RouteRecord] = []
    ports = [PORT_EAST, PORT_WEST, PORT_NORTH, PORT_SOUTH, PORT_UP, PORT_DOWN]

    pairs = [(s, d) for s in range(num_routers) for d in range(num_routers) if s != d]
    rng.shuffle(pairs)

    for src, dst in pairs[:count]:
        total_hops = rng.randint(1, 12)  # forces chained headers sometimes
        headers: list[int] = []
        remaining = total_hops
        promoted = False
        first = True
        while remaining > 0:
            seg = min(remaining, MAX_HEADER_HOPS)
            chained = (remaining - seg) > 0
            vc = VC1 if promoted else VC0
            trans = NO_VC_TRANSITION
            if first and not promoted and rng.random() < 0.3 and seg > 1:
                # at most one promotion across the whole chained route
                trans = rng.randint(0, seg - 1)
                promoted = True
            first = False
            headers.append(pack_header_flit(
                vc_id=vc,
                hop_count=seg,
                chained=chained,
                vc_transition_hop=trans,
                direction_vector=[rng.choice(ports) for _ in range(seg)],
            ))
            remaining -= seg
        routes.append(RouteRecord(src_tile=src, dst_tile=dst, headers=headers))
    return routes


def random_bitstream(rng: random.Random) -> OraBitstream:
    """Generate a random structurally valid OraBitstream."""
    use_analog = rng.random() < 0.5
    profile = PROFILE_ORA_D | PROFILE_ORA_N
    if use_analog:
        profile |= PROFILE_ORA_A | PROFILE_ORA_M

    n_gle4 = rng.randint(0, 6)
    n_gle6 = rng.randint(0, 4)
    n_peu = rng.randint(0, 4)
    num_routers = rng.randint(2, 12)

    bs = OraBitstream(profile=profile)
    bs.manifest = Manifest(
        gle4_count=n_gle4,
        gle6_count=n_gle6,
        peu_count=n_peu,
        cab_count=2 if use_analog else 0,
        router_count=num_routers,
        ni_count=num_routers,
    )

    vrb_records: list[VrbRecord] = []
    for _ in range(n_gle4):
        lut = rng.getrandbits(16)
        bindings = [rng.randint(0, 100) for _ in range(4)]
        flags = VRB_FLAG_PEU_OUT if rng.random() < 0.5 else 0
        vrb_records.append(VrbRecord(VRB_GLE4, 4, flags, [lut], bindings))
    for _ in range(n_gle6):
        w0 = rng.getrandbits(32)
        w1 = rng.getrandbits(32)
        bindings = [rng.randint(0, 100) for _ in range(6)]
        vrb_records.append(VrbRecord(VRB_GLE6, 6, 0, [w0, w1], bindings))
    for _ in range(n_peu):
        vrb_records.append(VrbRecord(VRB_PEU, 0, 0, [], [rng.randint(0, 100)]))
    bs.vrb_records = vrb_records

    # Netlist: chain records arbitrarily (each input driven at most once)
    n_vrbs = len(vrb_records)
    edges: list[EdgeRecord] = []
    driven: set[tuple[int, int]] = set()
    for _ in range(rng.randint(0, n_vrbs * 2)):
        if n_vrbs < 2:
            break
        src = rng.randrange(n_vrbs)
        dst = rng.randrange(n_vrbs)
        if src == dst:
            continue
        rec = vrb_records[dst]
        if rec.record_type == VRB_PEU:
            max_in = 1
        else:
            max_in = rec.lut_width
        free = [p for p in range(max_in) if (dst, p) not in driven]
        if not free:
            continue
        dp = rng.choice(free)
        driven.add((dst, dp))
        edges.append(EdgeRecord(src, dst, 0, dp, rng.randint(0, 50)))
    bs.edges = edges

    bs.routes = random_routes(rng, num_routers, rng.randint(0, 8))

    if use_analog:
        reg_ranges = {
            CAB_OTA_GM: (10_000, 1_000_000_000),
            CAB_CAP_BANK: (0, 255),
            CAB_MITE_BIAS: (0, 4095),
            CAB_VMM_CFG: (0, 65535),
        }
        bs.analog = []
        for _ in range(rng.randint(1, 4)):
            reg = rng.choice(list(reg_ranges.keys()))
            lo, hi = reg_ranges[reg]
            bs.analog.append(AnalogRecord(
                cab_id=rng.randrange(2),
                reg_offset=reg,
                value=rng.randint(lo, hi),
                data_type=0x01,
            ))
    else:
        bs.analog = []

    return bs


def fuzz_roundtrip(n_samples: int, seed: int = 1234) -> tuple[int, int]:
    """Run n_samples round-trip checks. Returns (passed, failed)."""
    rng = random.Random(seed)
    passed = failed = 0
    for _ in range(n_samples):
        bs = random_bitstream(rng)
        try:
            blob = bs.encode()
            decoded = OraBitstream.decode(blob)
            ok = decoded == bs
        except Exception:
            ok = False
        if ok:
            passed += 1
        else:
            failed += 1
    return passed, failed
