"""Conformance tests for the ORA bitstream v1.0 reference codec."""

import struct

import pytest

from ora_bitstream import (
    CAB_CAP_BANK,
    CAB_OTA_GM,
    HEADER_CRC_COVERAGE,
    NO_VC_TRANSITION,
    PORT_EAST,
    PORT_NORTH,
    PORT_SOUTH,
    PORT_UP,
    PORT_WEST,
    PROFILE_ORA_A,
    PROFILE_ORA_D,
    PROFILE_ORA_M,
    PROFILE_ORA_N,
    SECTION_HEAD,
    VC0,
    VC1,
    VRB_FLAG_PEU_OUT,
    VRB_GLE4,
    VRB_GLE6,
    VRB_PEU,
    AerFlit,
    AnalogRecord,
    BitstreamError,
    EdgeRecord,
    HeaderFlit,
    Manifest,
    OraBitstream,
    RouteRecord,
    VrbRecord,
    crc32,
    pack_header_flit,
    pack_single_flit_aer,
    router_step,
    trace_route,
    validate_route_headers,
)

FULL_PROFILE = PROFILE_ORA_D | PROFILE_ORA_A | PROFILE_ORA_M | PROFILE_ORA_N


def hdr(vc=VC0, hops=None, chained=False, trans=NO_VC_TRANSITION, dv=()):
    dv = list(dv)
    return pack_header_flit(
        vc_id=vc,
        hop_count=len(dv) if hops is None else hops,
        chained=chained,
        vc_transition_hop=trans,
        direction_vector=dv,
    )


def sample() -> OraBitstream:
    bs = OraBitstream(profile=FULL_PROFILE)
    bs.manifest = Manifest(gle4_count=1, gle6_count=1, peu_count=1,
                           cab_count=1, router_count=16, ni_count=16)
    bs.vrb_records = [
        VrbRecord(VRB_GLE4, 4, 0, [0x8000], [3, 1, 4, 1]),  # 4-input AND
        VrbRecord(VRB_GLE6, 6, VRB_FLAG_PEU_OUT, [0xFFFF0000, 0x0000FFFF], [0, 1, 2, 3, 4, 5]),
        VrbRecord(VRB_PEU, 0, 0, [], [9]),
    ]
    bs.edges = [EdgeRecord(0, 1, 0, 0, 12), EdgeRecord(1, 2, 0, 0, 8)]
    # 9-hop route: 7 hops in a chained first header, 2 in the second;
    # promotion on hop 4 of the first segment.
    first = hdr(chained=True, trans=4,
                dv=[PORT_EAST, PORT_EAST, PORT_NORTH, PORT_NORTH, PORT_UP, PORT_WEST, PORT_SOUTH])
    second = hdr(vc=VC1, dv=[PORT_EAST, PORT_NORTH])
    bs.routes = [RouteRecord(0, 15, [first, second]), RouteRecord(3, 4, [hdr(dv=[PORT_EAST])])]
    bs.analog = [
        AnalogRecord(0, CAB_OTA_GM, 10_000),  # 10 nS, not representable in FP16
        AnalogRecord(0, CAB_CAP_BANK, 255),  # 25.6 pF
    ]
    return bs


class TestRoundTrip:
    def test_encode_decode_equal(self):
        bs = sample()
        assert OraBitstream.decode(bs.encode()) == bs

    def test_fixed_header_layout(self):
        blob = sample().encode()
        assert blob[0:4] == b"ORA1"
        version, profile, hcrc = struct.unpack_from("<III", blob, 4)
        assert version == 0x00010000
        assert profile == FULL_PROFILE
        assert HEADER_CRC_COVERAGE == 12
        assert hcrc == crc32(blob[0:12])  # covers 0x00-0x0B, not itself
        (fcrc,) = struct.unpack_from("<I", blob, len(blob) - 4)
        assert fcrc == crc32(blob[:-4])

    def test_sections_are_tlv_in_canonical_order(self):
        blob = sample().encode()
        pos, tags = 48, []
        while pos < len(blob) - 4:
            tag, length = SECTION_HEAD.unpack_from(blob, pos)
            tags.append(tag)
            pos += SECTION_HEAD.size + length
        assert tags == [1, 2, 3, 4]
        assert pos == len(blob) - 4

    def test_empty_bitstream_roundtrip(self):
        bs = OraBitstream(profile=PROFILE_ORA_D)
        assert OraBitstream.decode(bs.encode()) == bs


def resign(blob: bytearray) -> bytes:
    """Recompute both CRCs so that structural checks, not CRCs, are tested."""
    struct.pack_into("<I", blob, 12, crc32(bytes(blob[:12])))
    struct.pack_into("<I", blob, len(blob) - 4, crc32(bytes(blob[:-4])))
    return bytes(blob)


class TestDecoderRejects:
    def test_bad_magic(self):
        blob = bytearray(sample().encode())
        blob[0:4] = b"XXXX"
        with pytest.raises(BitstreamError, match="bad magic"):
            OraBitstream.decode(bytes(blob))

    def test_bad_version(self):
        blob = bytearray(sample().encode())
        struct.pack_into("<I", blob, 4, 0x00020000)
        with pytest.raises(BitstreamError, match="unsupported spec version"):
            OraBitstream.decode(resign(blob))

    def test_header_crc(self):
        blob = bytearray(sample().encode())
        struct.pack_into("<I", blob, 8, PROFILE_ORA_D)
        with pytest.raises(BitstreamError, match="header CRC"):
            OraBitstream.decode(bytes(blob))

    def test_file_crc(self):
        blob = bytearray(sample().encode())
        blob[-5] ^= 0xFF
        with pytest.raises(BitstreamError, match="file CRC"):
            OraBitstream.decode(bytes(blob))

    def test_too_short(self):
        with pytest.raises(BitstreamError, match="too short"):
            OraBitstream.decode(sample().encode()[:20])

    def test_section_out_of_order(self):
        bs = OraBitstream(profile=PROFILE_ORA_D)
        blob = bytearray(bs.encode())
        # Swap the tags of the first two (empty) sections: NETLIST before VRB.
        struct.pack_into("<H", blob, 48, 2)
        struct.pack_into("<H", blob, 54, 1)
        with pytest.raises(BitstreamError, match="out of order"):
            OraBitstream.decode(resign(blob))

    def test_truncated_record(self):
        bs = OraBitstream(profile=PROFILE_ORA_D)
        blob = bytearray(bs.encode())
        # Claim 3 bytes of netlist payload: shorter than one 10-byte edge.
        body = blob[:-4]
        body[54:60] = SECTION_HEAD.pack(2, 3)
        body[60:60] = b"\x00\x00\x00"
        with pytest.raises(BitstreamError, match="truncated record"):
            OraBitstream.decode(resign(body + b"\x00\x00\x00\x00"))


class TestEncoderValidation:
    def test_manifest_counts_must_match(self):
        bs = sample()
        bs.manifest.gle4_count = 2
        with pytest.raises(BitstreamError, match="manifest GLE/PEU counts"):
            bs.encode()

    def test_gle4_truth_table_width(self):
        bs = sample()
        bs.vrb_records[0].lut_init = [0x1_0000]
        with pytest.raises(BitstreamError, match="bits 15:0"):
            bs.encode()

    def test_gle6_needs_two_words(self):
        bs = sample()
        bs.vrb_records[1].lut_init = [0, 0, 0, 0]
        with pytest.raises(BitstreamError, match="2 LUT init"):
            bs.encode()

    def test_input_driven_twice(self):
        bs = sample()
        bs.edges.append(EdgeRecord(2, 1, 0, 0, 1))
        with pytest.raises(BitstreamError, match="driven twice"):
            bs.encode()

    def test_analog_needs_profile(self):
        bs = sample()
        bs.profile = PROFILE_ORA_D | PROFILE_ORA_N
        with pytest.raises(BitstreamError, match="ORA-A profile"):
            bs.encode()

    def test_ora_a_requires_ora_m(self):
        bs = sample()
        bs.profile = PROFILE_ORA_D | PROFILE_ORA_A | PROFILE_ORA_N
        with pytest.raises(BitstreamError, match="requires ORA-M"):
            bs.encode()

    @pytest.mark.parametrize("value", [9_999, 1_000_000_001])
    def test_gm_range(self, value):
        bs = sample()
        bs.analog[0].value = value
        with pytest.raises(BitstreamError, match="CAB_OTA_GM"):
            bs.encode()

    def test_route_tile_bound(self):
        bs = sample()
        bs.routes[1].dst_tile = 16
        with pytest.raises(BitstreamError, match="router_count"):
            bs.encode()


class TestHeaderFlit:
    def test_roundtrip(self):
        word = hdr(chained=True, trans=2, dv=[1, 2, 3, 4, 5])
        assert HeaderFlit.unpack(word) == HeaderFlit(VC0, 5, True, 2, (1, 2, 3, 4, 5))

    def test_first_hop_in_lowest_bits(self):
        assert hdr(dv=[PORT_UP, PORT_WEST]) & 0b111 == PORT_UP

    def test_direction_vector_length_must_match_hop_count(self):
        with pytest.raises(BitstreamError, match="hop_count is 3"):
            hdr(hops=3, dv=[1, 2])

    def test_transition_must_be_inside_segment(self):
        with pytest.raises(BitstreamError, match="vc_transition_hop"):
            hdr(trans=3, dv=[1, 2, 3])

    def test_vc1_header_cannot_request_promotion(self):
        with pytest.raises(BitstreamError, match="already on VC1"):
            hdr(vc=VC1, trans=0, dv=[1])

    def test_stray_direction_bits_rejected(self):
        word = hdr(dv=[1]) | (0b111 << 3)
        with pytest.raises(BitstreamError, match="beyond hop_count"):
            HeaderFlit.unpack(word)


class TestRouterStep:
    def test_forward_consumes_lowest_port_and_zero_fills(self):
        word = hdr(dv=[7, 6, 5, 4, 3, 2, 1])
        d = router_step(word)
        assert (d.action, d.out_port, d.vc_id) == ("forward", 7, VC0)
        nxt = HeaderFlit.unpack(d.word)
        assert nxt.direction_vector == (6, 5, 4, 3, 2, 1)
        assert nxt.hop_count == 6

    def test_seven_hop_packet_without_promotion_stays_on_vc0(self):
        # Regression: comparing the remaining hop count (7) against the
        # 0b111 sentinel promoted this packet on its first hop.
        hops = trace_route([hdr(dv=[1] * 7)])
        assert [vc for _, vc in hops] == [VC0] * 7

    @pytest.mark.parametrize("k", range(7))
    def test_promotion_happens_on_ordinal_hop(self, k):
        hops = trace_route([hdr(trans=k, dv=[1] * 7)])
        assert [vc for _, vc in hops] == [VC0] * k + [VC1] * (7 - k)

    def test_eject_and_chain(self):
        assert router_step(hdr(dv=[])).action == "eject"
        assert router_step(hdr(hops=0, chained=True, dv=[])).action == "chain"

    def test_body_flit_is_not_a_header(self):
        with pytest.raises(BitstreamError, match="not a header"):
            router_step(0b01 << 30)


class TestRouteValidation:
    def test_promotion_survives_chain_boundary(self):
        route = sample().routes[0].headers
        vcs = [vc for _, vc in trace_route(route)]
        assert vcs == [VC0] * 4 + [VC1] * 5
        validate_route_headers(route)

    def test_second_header_must_carry_vc1_after_promotion(self):
        first = hdr(chained=True, trans=0, dv=[1])
        with pytest.raises(BitstreamError, match="promotion state"):
            validate_route_headers([first, hdr(vc=VC0, dv=[1])])

    def test_at_most_one_promotion(self):
        first = hdr(chained=True, trans=0, dv=[1])
        second = hdr(vc=VC1, dv=[1])
        validate_route_headers([first, second])
        with pytest.raises(BitstreamError):
            validate_route_headers([first, hdr(chained=True, trans=0, dv=[1]), second])

    def test_chain_flags(self):
        with pytest.raises(BitstreamError, match="chained=1"):
            validate_route_headers([hdr(dv=[1]), hdr(dv=[1])])
        with pytest.raises(BitstreamError, match="chained=1"):
            validate_route_headers([hdr(chained=True, dv=[1])])

    def test_chained_header_must_advance(self):
        with pytest.raises(BitstreamError, match="advance"):
            validate_route_headers([hdr(hops=0, chained=True, dv=[]), hdr(dv=[1])])

    def test_injection_on_vc0(self):
        with pytest.raises(BitstreamError, match="injected on VC0"):
            validate_route_headers([hdr(vc=VC1, dv=[1])])


class TestAerFlit:
    def test_roundtrip_and_layout(self):
        word = pack_single_flit_aer(hop_count=2, direction_vector=[0b010, 0b011],
                                    neuron_address=0xF4240)
        assert word >> 30 == 0b11
        assert (word >> 28) & 0b11 == VC0
        assert (word >> 26) & 0b11 == 2
        assert (word >> 20) & 0b111 == 0b010
        assert (word >> 23) & 0b111 == 0b011
        assert word & 0xFFFFF == 0xF4240
        assert AerFlit.unpack(word) == AerFlit(2, (0b010, 0b011), 0xF4240)

    def test_address_overflow(self):
        with pytest.raises(BitstreamError, match="20 bits"):
            pack_single_flit_aer(hop_count=1, direction_vector=[0], neuron_address=1 << 20)

    def test_hop_limit(self):
        with pytest.raises(BitstreamError, match="hop_count"):
            pack_single_flit_aer(hop_count=3, direction_vector=[0, 0, 0], neuron_address=0)
