"""ORA Neutral Bytecode Bitstream v1.0 -- reference codec.

The normative byte layout is docs/ora_poc_standard_specification.typ, section 5
("V-HAL"). This module must stay byte-for-byte consistent with that section;
every structural rule there is enforced by `OraBitstream.validate()`, which is
run on both encode and decode.

Summary (all integers little-endian):

    0x00  u8[4]  magic          "ORA1"
    0x04  u32    version        (major << 16) | minor  -> 0x00010000
    0x08  u32    profile        bit0 ORA-D, bit1 ORA-A, bit2 ORA-M, bit3 ORA-N
    0x0C  u32    header_crc     CRC-32 over bytes 0x00-0x0B
    0x10  u32[8] manifest       gle4, gle6, peu, cab, router, ni, rsv0, rsv1
    0x30  ...    sections       repeated {u16 tag, u32 len, u8[len] payload}
    end-4 u32    file_crc       CRC-32 over every preceding byte
"""

from __future__ import annotations

import binascii
import struct
from dataclasses import dataclass, field

# --------------------------------------------------------------------------
# Constants
# --------------------------------------------------------------------------

MAGIC = b"ORA1"
SPEC_VERSION = (1, 0)

PROFILE_ORA_D = 1 << 0
PROFILE_ORA_A = 1 << 1
PROFILE_ORA_M = 1 << 2
PROFILE_ORA_N = 1 << 3
PROFILE_KNOWN_MASK = PROFILE_ORA_D | PROFILE_ORA_A | PROFILE_ORA_M | PROFILE_ORA_N

HEADER_LEN = 16
HEADER_CRC_COVERAGE = 12  # header CRC covers 0x00-0x0B, never itself
MANIFEST_LEN = 32
FILE_CRC_LEN = 4

SECTION_VRB = 0x0001
SECTION_NETLIST = 0x0002
SECTION_NOC = 0x0003
SECTION_ANALOG = 0x0004
SECTION_ORDER = (SECTION_VRB, SECTION_NETLIST, SECTION_NOC, SECTION_ANALOG)

SECTION_HEAD = struct.Struct("<HI")  # tag, payload length          (6 B)
MANIFEST = struct.Struct("<8I")  #                                  (32 B)
VRB_HEAD = struct.Struct("<BBBBHH")  # type, k, flags, rsv, n_init, n_port (8 B)
EDGE = struct.Struct("<HHHHH")  # src, dst, src_port, dst_port, delay (10 B)
ROUTE_HEAD = struct.Struct("<HHBB")  # src_tile, dst_tile, n_headers, rsv (6 B)
ANALOG_REC = struct.Struct("<HHBBI")  # cab_id, reg, dtype, rsv, value (10 B)

VRB_GLE4 = 0x01
VRB_GLE6 = 0x02
VRB_PEU = 0x03
VRB_FLAG_PEU_OUT = 0x01  # GLE output is registered by an elastic buffer

ANALOG_TYPE_U32_FIXED = 0x01  # unsigned integer in the register's fixed unit

# CAB register map: offset -> (name, min, max). All registers are
# ANALOG_TYPE_U32_FIXED in v1.0.
CAB_OTA_GM = 0x00  # transconductance in picosiemens (10 nS .. 1 mS)
CAB_CAP_BANK = 0x04  # code c -> C = 100 fF * (c + 1)   (100 fF .. 25.6 pF)
CAB_MITE_BIAS = 0x08  # 12-bit bias DAC code
CAB_VMM_CFG = 0x0C  # 16-bit crossbar row/column enable mask
CAB_REGISTERS = {
    CAB_OTA_GM: ("CAB_OTA_GM", 10_000, 1_000_000_000),
    CAB_CAP_BANK: ("CAB_CAP_BANK", 0, 255),
    CAB_MITE_BIAS: ("CAB_MITE_BIAS", 0, 0x0FFF),
    CAB_VMM_CFG: ("CAB_VMM_CFG", 0, 0xFFFF),
}

# ORA-N flit types and virtual channels
FLIT_TYPE_HEADER = 0b00
FLIT_TYPE_BODY = 0b01
FLIT_TYPE_TAIL = 0b10
FLIT_TYPE_SINGLE_AER = 0b11

VC0 = 0b00
VC1 = 0b01

NO_VC_TRANSITION = 0b111
MAX_HEADER_HOPS = 7
MAX_AER_HOPS = 2

PORT_LOCAL = 0b000
PORT_NORTH = 0b001
PORT_EAST = 0b010
PORT_SOUTH = 0b011
PORT_WEST = 0b100
PORT_UP = 0b101
PORT_DOWN = 0b110


class BitstreamError(ValueError):
    """Raised on any violation of the ORA bitstream v1.0 format."""


def crc32(data: bytes) -> int:
    """CRC-32 (IEEE 802.3 / zlib polynomial)."""
    return binascii.crc32(data) & 0xFFFFFFFF


# --------------------------------------------------------------------------
# ORA-N header flit
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class HeaderFlit:
    """Decoded ORA-N header flit (flit type 00).

    vc_transition_hop is ordinal: value k (0-6) means the packet is promoted
    to VC1 on its k-th forwarding hop within this header's segment (0-based).
    NO_VC_TRANSITION (0b111) means no promotion in this segment.
    direction_vector holds exactly hop_count ports, first hop first.
    """

    vc_id: int
    hop_count: int
    chained: bool
    vc_transition_hop: int
    direction_vector: tuple[int, ...]

    def validate(self) -> None:
        if self.vc_id not in (VC0, VC1):
            raise BitstreamError(f"vc_id must be VC0 or VC1, got {self.vc_id}")
        if not 0 <= self.hop_count <= MAX_HEADER_HOPS:
            raise BitstreamError(f"hop_count out of range: {self.hop_count}")
        if len(self.direction_vector) != self.hop_count:
            raise BitstreamError(
                f"direction_vector has {len(self.direction_vector)} entries, "
                f"hop_count is {self.hop_count}"
            )
        for port in self.direction_vector:
            if not 0 <= port <= 0b111:
                raise BitstreamError(f"port index out of 3-bit range: {port}")
        t = self.vc_transition_hop
        if t != NO_VC_TRANSITION and not 0 <= t < self.hop_count:
            raise BitstreamError(
                f"vc_transition_hop must be < hop_count ({self.hop_count}) "
                f"or {NO_VC_TRANSITION}, got {t}"
            )
        if self.vc_id == VC1 and t != NO_VC_TRANSITION:
            raise BitstreamError("a header already on VC1 cannot request promotion")

    def pack(self) -> int:
        self.validate()
        word = (FLIT_TYPE_HEADER << 30) | (self.vc_id << 28) | (self.hop_count << 25)
        word |= int(self.chained) << 24
        word |= self.vc_transition_hop << 21
        for i, port in enumerate(self.direction_vector):
            word |= port << (3 * i)
        return word

    @classmethod
    def unpack(cls, word: int) -> "HeaderFlit":
        if not 0 <= word <= 0xFFFFFFFF:
            raise BitstreamError(f"flit is not a u32: {word}")
        if (word >> 30) & 0b11 != FLIT_TYPE_HEADER:
            raise BitstreamError(f"not a header flit: type {(word >> 30) & 0b11:02b}")
        hops = (word >> 25) & 0b111
        dv_bits = word & 0x1FFFFF
        if dv_bits >> (3 * hops):
            raise BitstreamError("direction vector bits set beyond hop_count")
        flit = cls(
            vc_id=(word >> 28) & 0b11,
            hop_count=hops,
            chained=bool((word >> 24) & 1),
            vc_transition_hop=(word >> 21) & 0b111,
            direction_vector=tuple((word >> (3 * i)) & 0b111 for i in range(hops)),
        )
        flit.validate()
        return flit


def pack_header_flit(
    *,
    vc_id: int,
    hop_count: int,
    chained: bool,
    vc_transition_hop: int,
    direction_vector: list[int],
) -> int:
    """Pack one ORA-N header flit into a u32 (see HeaderFlit)."""
    return HeaderFlit(
        vc_id, hop_count, chained, vc_transition_hop, tuple(direction_vector)
    ).pack()


def unpack_header_flit(word: int) -> HeaderFlit:
    return HeaderFlit.unpack(word)


@dataclass(frozen=True)
class RouterDecision:
    """Result of one router evaluation of a header flit.

    action: "forward"  -> send `word` (rewritten header) out of `out_port`
            "eject"    -> deliver the packet to the local NI
            "chain"    -> drop this header; the next flit must be a header
                          (type 00) and is evaluated at this same router
    """

    action: str
    out_port: int | None
    vc_id: int
    word: int | None


def router_step(word: int) -> RouterDecision:
    """Normative per-router header processing (spec section 2.3).

    Order: hop-count check, VC promotion countdown, port decode from Bit[2:0],
    hop decrement, logical (zero-fill) shift of the 21-bit direction vector.
    """
    flit = HeaderFlit.unpack(word)
    if flit.hop_count == 0:
        return RouterDecision("chain" if flit.chained else "eject", None, flit.vc_id, None)

    vc = flit.vc_id
    t = flit.vc_transition_hop
    if t == 0:
        vc, t = VC1, NO_VC_TRANSITION
    elif t != NO_VC_TRANSITION:
        t -= 1

    out_port = word & 0b111
    dv = (word & 0x1FFFFF) >> 3
    hops = flit.hop_count - 1
    new_word = (
        (FLIT_TYPE_HEADER << 30) | (vc << 28) | (hops << 25)
        | (int(flit.chained) << 24) | (t << 21) | dv
    )
    return RouterDecision("forward", out_port, vc, new_word)


def trace_route(headers: list[int]) -> list[tuple[int, int]]:
    """Run a chained header sequence through router_step.

    Returns the (out_port, vc_id) of every forwarding hop. The VC used after a
    chain boundary is max(current VC, next header's VC), so it never decreases.
    """
    if not headers:
        raise BitstreamError("route has no header flits")
    hops: list[tuple[int, int]] = []
    current_vc = VC0
    idx = 0
    word = headers[0]
    while True:
        decision = router_step(word)
        current_vc = max(current_vc, decision.vc_id)
        if decision.action == "forward":
            assert decision.out_port is not None and decision.word is not None
            hops.append((decision.out_port, current_vc))
            word = decision.word
        elif decision.action == "eject":
            if idx != len(headers) - 1:
                raise BitstreamError("route ejects before its last header")
            return hops
        else:  # chain
            idx += 1
            if idx >= len(headers):
                raise BitstreamError("chained header has no successor")
            word = headers[idx]


def validate_route_headers(headers: list[int]) -> None:
    """Encoder-side rules for one route's chained header sequence."""
    if not 1 <= len(headers) <= 255:
        raise BitstreamError("a route needs 1-255 header flits")
    flits = [HeaderFlit.unpack(w) for w in headers]
    if flits[0].vc_id != VC0:
        raise BitstreamError("packets are injected on VC0")
    promoted = False
    for i, f in enumerate(flits):
        last = i == len(flits) - 1
        if f.chained == last:
            raise BitstreamError(
                "every header except the last must set chained=1, the last chained=0"
            )
        if not last and f.hop_count == 0:
            raise BitstreamError("a chained header must advance at least one hop")
        if f.vc_id != (VC1 if promoted else VC0):
            raise BitstreamError(f"header {i} VC does not match the promotion state")
        if f.vc_transition_hop != NO_VC_TRANSITION:
            if promoted:
                raise BitstreamError("a route may promote to VC1 at most once")
            promoted = True
    trace_route(headers)


# --------------------------------------------------------------------------
# Single-flit AER event
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class AerFlit:
    """Single-flit AER event (type 11, VC0 only, at most 2 hops).

    Layout: [31:30]=11, [29:28]=VC0, [27:26]=hop_count, [25:20]=direction
    vector (first hop in [22:20]), [19:0]=local neuron address.
    """

    hop_count: int
    direction_vector: tuple[int, ...]
    neuron_address: int

    def validate(self) -> None:
        if not 0 <= self.hop_count <= MAX_AER_HOPS:
            raise BitstreamError(f"AER hop_count out of range: {self.hop_count}")
        if len(self.direction_vector) != self.hop_count:
            raise BitstreamError("AER direction_vector length must equal hop_count")
        for port in self.direction_vector:
            if not 0 <= port <= 0b111:
                raise BitstreamError(f"port index out of 3-bit range: {port}")
        if not 0 <= self.neuron_address < (1 << 20):
            raise BitstreamError("neuron_address must fit 20 bits")

    def pack(self) -> int:
        self.validate()
        word = (FLIT_TYPE_SINGLE_AER << 30) | (VC0 << 28) | (self.hop_count << 26)
        for i, port in enumerate(self.direction_vector):
            word |= port << (20 + 3 * i)
        return word | self.neuron_address

    @classmethod
    def unpack(cls, word: int) -> "AerFlit":
        if (word >> 30) & 0b11 != FLIT_TYPE_SINGLE_AER:
            raise BitstreamError("not a single-flit AER event")
        if (word >> 28) & 0b11 != VC0:
            raise BitstreamError("AER events must travel on VC0")
        hops = (word >> 26) & 0b11
        flit = cls(
            hop_count=hops,
            direction_vector=tuple((word >> (20 + 3 * i)) & 0b111 for i in range(hops)),
            neuron_address=word & 0xFFFFF,
        )
        flit.validate()
        return flit


def pack_single_flit_aer(*, hop_count: int, direction_vector: list[int], neuron_address: int) -> int:
    return AerFlit(hop_count, tuple(direction_vector), neuron_address).pack()


# --------------------------------------------------------------------------
# Records
# --------------------------------------------------------------------------


@dataclass
class VrbRecord:
    """One VRB record. GLE-4: k=4, 1 init word (bits 31:16 zero);
    GLE-6: k=6, 2 init words (64-bit truth table, low word first);
    PEU: k=0, no init words, flags=0, exactly 1 input binding."""

    record_type: int = VRB_GLE4
    lut_width: int = 4
    flags: int = 0
    lut_init: list[int] = field(default_factory=list)
    port_bindings: list[int] = field(default_factory=list)

    def input_count(self) -> int:
        return 1 if self.record_type == VRB_PEU else self.lut_width

    def validate(self, index: int) -> None:
        where = f"VRB[{index}]"
        rules = {VRB_GLE4: (4, 1), VRB_GLE6: (6, 2), VRB_PEU: (0, 0)}
        if self.record_type not in rules:
            raise BitstreamError(f"{where}: unknown record_type 0x{self.record_type:02x}")
        k, n_init = rules[self.record_type]
        if self.lut_width != k:
            raise BitstreamError(f"{where}: lut_width must be {k}")
        if len(self.lut_init) != n_init:
            raise BitstreamError(f"{where}: needs {n_init} LUT init word(s)")
        if any(not 0 <= w <= 0xFFFFFFFF for w in self.lut_init):
            raise BitstreamError(f"{where}: LUT init word is not a u32")
        if self.record_type == VRB_GLE4 and self.lut_init[0] >> 16:
            raise BitstreamError(f"{where}: 4-LUT truth table uses only bits 15:0")
        if self.flags & ~VRB_FLAG_PEU_OUT:
            raise BitstreamError(f"{where}: reserved flag bits set")
        if self.record_type == VRB_PEU and self.flags:
            raise BitstreamError(f"{where}: PEU records take no flags")
        if len(self.port_bindings) != self.input_count():
            raise BitstreamError(f"{where}: needs {self.input_count()} input binding(s)")
        if any(not 0 <= p <= 0xFFFF for p in self.port_bindings):
            raise BitstreamError(f"{where}: PSB port id is not a u16")


@dataclass
class EdgeRecord:
    """Netlist edge. In v1.0 every VRB has exactly one output (port 0)."""

    src_vrb_id: int
    dst_vrb_id: int
    src_port: int
    dst_port: int
    delay_budget: int


@dataclass
class RouteRecord:
    """One precomputed source route: a single chained header sequence."""

    src_tile: int
    dst_tile: int
    headers: list[int] = field(default_factory=list)


@dataclass
class AnalogRecord:
    """One CAB register write."""

    cab_id: int
    reg_offset: int
    value: int
    data_type: int = ANALOG_TYPE_U32_FIXED


@dataclass
class Manifest:
    gle4_count: int = 0
    gle6_count: int = 0
    peu_count: int = 0
    cab_count: int = 0
    router_count: int = 0
    ni_count: int = 0
    reserved: tuple[int, int] = (0, 0)

    def pack(self) -> bytes:
        return MANIFEST.pack(
            self.gle4_count, self.gle6_count, self.peu_count, self.cab_count,
            self.router_count, self.ni_count, *self.reserved,
        )

    @classmethod
    def unpack(cls, blob: bytes) -> "Manifest":
        v = MANIFEST.unpack(blob)
        return cls(v[0], v[1], v[2], v[3], v[4], v[5], (v[6], v[7]))


# --------------------------------------------------------------------------
# Bitstream
# --------------------------------------------------------------------------


class _Reader:
    """Bounds-checked cursor; every overrun becomes a BitstreamError."""

    def __init__(self, buf: bytes, what: str):
        self.buf, self.pos, self.what = buf, 0, what

    def take(self, st: struct.Struct) -> tuple:
        if self.pos + st.size > len(self.buf):
            raise BitstreamError(f"{self.what}: truncated record at byte {self.pos}")
        value = st.unpack_from(self.buf, self.pos)
        self.pos += st.size
        return value

    def take_array(self, code: str, count: int) -> list[int]:
        st = struct.Struct(f"<{count}{code}")
        return list(self.take(st)) if count else []

    def at_end(self) -> bool:
        return self.pos == len(self.buf)


@dataclass
class OraBitstream:
    profile: int = PROFILE_ORA_D | PROFILE_ORA_N
    manifest: Manifest = field(default_factory=Manifest)
    vrb_records: list[VrbRecord] = field(default_factory=list)
    edges: list[EdgeRecord] = field(default_factory=list)
    routes: list[RouteRecord] = field(default_factory=list)
    analog: list[AnalogRecord] = field(default_factory=list)

    # ---- validation (shared by encode and decode) ----

    def validate(self) -> None:
        self._validate_profile()
        self._validate_vrb_section()
        self._validate_netlist_section()
        self._validate_noc_section()
        self._validate_analog_section()

    def _validate_profile(self) -> None:
        if self.profile & ~PROFILE_KNOWN_MASK:
            raise BitstreamError(f"reserved profile bits set: 0x{self.profile:08x}")
        if self.profile & PROFILE_ORA_A and not self.profile & PROFILE_ORA_M:
            raise BitstreamError("ORA-A requires ORA-M (mixed-signal boundary)")
        m = self.manifest
        if m.reserved != (0, 0):
            raise BitstreamError("manifest reserved words must be zero")
        if self.vrb_records and not self.profile & PROFILE_ORA_D:
            raise BitstreamError("VRB records require the ORA-D profile")
        if self.routes and not self.profile & PROFILE_ORA_N:
            raise BitstreamError("NoC routes require the ORA-N profile")
        if self.analog and not self.profile & PROFILE_ORA_A:
            raise BitstreamError("analog records require the ORA-A profile")

    def _validate_vrb_section(self) -> None:
        m = self.manifest
        for i, rec in enumerate(self.vrb_records):
            rec.validate(i)
        counts = {t: sum(r.record_type == t for r in self.vrb_records)
                  for t in (VRB_GLE4, VRB_GLE6, VRB_PEU)}
        if (m.gle4_count, m.gle6_count, m.peu_count) != (
            counts[VRB_GLE4], counts[VRB_GLE6], counts[VRB_PEU]
        ):
            raise BitstreamError("manifest GLE/PEU counts do not match VRB records")

    def _validate_netlist_section(self) -> None:
        driven: set[tuple[int, int]] = set()
        for i, e in enumerate(self.edges):
            where = f"edge[{i}]"
            for name in ("src_vrb_id", "dst_vrb_id", "src_port", "dst_port", "delay_budget"):
                if not 0 <= getattr(e, name) <= 0xFFFF:
                    raise BitstreamError(f"{where}: {name} is not a u16")
            if e.src_vrb_id >= len(self.vrb_records) or e.dst_vrb_id >= len(self.vrb_records):
                raise BitstreamError(f"{where}: VRB index out of range")
            if e.src_port != 0:
                raise BitstreamError(f"{where}: VRBs have a single output port 0")
            if e.dst_port >= self.vrb_records[e.dst_vrb_id].input_count():
                raise BitstreamError(f"{where}: dst_port out of range")
            if (e.dst_vrb_id, e.dst_port) in driven:
                raise BitstreamError(f"{where}: input port driven twice")
            driven.add((e.dst_vrb_id, e.dst_port))

    def _validate_noc_section(self) -> None:
        m = self.manifest
        for i, r in enumerate(self.routes):
            where = f"route[{i}]"
            if r.src_tile >= m.router_count or r.dst_tile >= m.router_count:
                raise BitstreamError(f"{where}: tile id >= manifest router_count")
            try:
                validate_route_headers(r.headers)
            except BitstreamError as exc:
                raise BitstreamError(f"{where}: {exc}") from None

    def _validate_analog_section(self) -> None:
        m = self.manifest
        for i, a in enumerate(self.analog):
            where = f"analog[{i}]"
            if a.cab_id >= m.cab_count:
                raise BitstreamError(f"{where}: cab_id >= manifest cab_count")
            if a.reg_offset not in CAB_REGISTERS:
                raise BitstreamError(f"{where}: unknown CAB register 0x{a.reg_offset:02x}")
            if a.data_type != ANALOG_TYPE_U32_FIXED:
                raise BitstreamError(f"{where}: v1.0 registers use data_type 0x01")
            name, lo, hi = CAB_REGISTERS[a.reg_offset]
            if not lo <= a.value <= hi:
                raise BitstreamError(f"{where}: {name} value {a.value} outside [{lo}, {hi}]")

    def encode(self) -> bytes:
        self.validate()
        out = bytearray(MAGIC)
        out += struct.pack("<II", (SPEC_VERSION[0] << 16) | SPEC_VERSION[1], self.profile)
        out += struct.pack("<I", crc32(bytes(out[:HEADER_CRC_COVERAGE])))
        out += self.manifest.pack()
        for tag, payload in (
            (SECTION_VRB, self._pack_vrb()),
            (SECTION_NETLIST, b"".join(EDGE.pack(e.src_vrb_id, e.dst_vrb_id, e.src_port,
                                                 e.dst_port, e.delay_budget) for e in self.edges)),
            (SECTION_NOC, self._pack_noc()),
            (SECTION_ANALOG, b"".join(ANALOG_REC.pack(a.cab_id, a.reg_offset, a.data_type, 0,
                                                      a.value) for a in self.analog)),
        ):
            out += SECTION_HEAD.pack(tag, len(payload)) + payload
        out += struct.pack("<I", crc32(bytes(out)))
        return bytes(out)

    def _pack_vrb(self) -> bytes:
        blob = bytearray()
        for r in self.vrb_records:
            blob += VRB_HEAD.pack(r.record_type, r.lut_width, r.flags, 0,
                                  len(r.lut_init), len(r.port_bindings))
            blob += struct.pack(f"<{len(r.lut_init)}I", *r.lut_init)
            blob += struct.pack(f"<{len(r.port_bindings)}H", *r.port_bindings)
        return bytes(blob)

    def _pack_noc(self) -> bytes:
        blob = bytearray()
        for r in self.routes:
            blob += ROUTE_HEAD.pack(r.src_tile, r.dst_tile, len(r.headers), 0)
            blob += struct.pack(f"<{len(r.headers)}I", *r.headers)
        return bytes(blob)

    # ---- decoding ----

    @classmethod
    def decode(cls, blob: bytes) -> "OraBitstream":
        if len(blob) < HEADER_LEN + MANIFEST_LEN + FILE_CRC_LEN:
            raise BitstreamError("bitstream too short")
        if blob[0:4] != MAGIC:
            raise BitstreamError(f"bad magic: {blob[0:4]!r}")
        version, profile, header_crc = struct.unpack_from("<III", blob, 4)
        if (version >> 16, version & 0xFFFF) != SPEC_VERSION:
            raise BitstreamError(f"unsupported spec version: {version >> 16}.{version & 0xFFFF}")
        if header_crc != crc32(blob[:HEADER_CRC_COVERAGE]):
            raise BitstreamError("header CRC mismatch")
        (file_crc,) = struct.unpack_from("<I", blob, len(blob) - FILE_CRC_LEN)
        if file_crc != crc32(blob[:-FILE_CRC_LEN]):
            raise BitstreamError("file CRC mismatch")

        stream = cls(profile=profile,
                     manifest=Manifest.unpack(blob[HEADER_LEN:HEADER_LEN + MANIFEST_LEN]))
        body = _Reader(blob[HEADER_LEN + MANIFEST_LEN:-FILE_CRC_LEN], "section table")
        last_tag = 0
        while not body.at_end():
            tag, length = body.take(SECTION_HEAD)
            if tag not in SECTION_ORDER:
                raise BitstreamError(f"unknown section tag: 0x{tag:04x}")
            if tag <= last_tag:
                raise BitstreamError(f"section 0x{tag:04x} duplicated or out of order")
            last_tag = tag
            if body.pos + length > len(body.buf):
                raise BitstreamError(f"section 0x{tag:04x} payload overruns file")
            payload = body.buf[body.pos:body.pos + length]
            body.pos += length
            cls._parse_section(stream, tag, _Reader(payload, f"section 0x{tag:04x}"))
        stream.validate()
        return stream

    @staticmethod
    def _parse_section(stream: "OraBitstream", tag: int, rd: _Reader) -> None:
        while not rd.at_end():
            if tag == SECTION_VRB:
                rtype, k, flags, rsv, n_init, n_port = rd.take(VRB_HEAD)
                if rsv:
                    raise BitstreamError("VRB reserved byte must be zero")
                stream.vrb_records.append(
                    VrbRecord(rtype, k, flags, rd.take_array("I", n_init), rd.take_array("H", n_port))
                )
            elif tag == SECTION_NETLIST:
                stream.edges.append(EdgeRecord(*rd.take(EDGE)))
            elif tag == SECTION_NOC:
                src, dst, n, rsv = rd.take(ROUTE_HEAD)
                if rsv:
                    raise BitstreamError("route reserved byte must be zero")
                stream.routes.append(RouteRecord(src, dst, rd.take_array("I", n)))
            else:
                cab, reg, dtype, rsv, value = rd.take(ANALOG_REC)
                if rsv:
                    raise BitstreamError("analog reserved byte must be zero")
                stream.analog.append(AnalogRecord(cab, reg, value, dtype))
