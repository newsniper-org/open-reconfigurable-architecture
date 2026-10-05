"""Unit tests for ORA-N NoCRouter and NetworkInterface (Module M3).

Validates:
  - Table-less microarchitecture (zero lookup memory)
  - 3-bit port decoding and logical right shift (>>> 3)
  - Cycle-accurate 2-phase execution: order-independent simulation
  - Independent (out_port, out_vc) crossbar locking: VC1 packet makes progress during VC0 wormhole
  - Physical link single-flit-per-cycle constraint (link_used)
  - Chained header traversal across hop boundaries with strict destination delivery
  - Monotonic VC promotion countdown and multi-flit VC rewriting
  - Single-flit AER event forwarding on VC0 with 20-bit address preservation
  - End-to-end packet transmission between Network Interfaces
"""
#
from ora_bitstream import (
    FLIT_TYPE_HEADER,
    FLIT_TYPE_BODY,
    FLIT_TYPE_TAIL,
    FLIT_TYPE_SINGLE_AER,
    VC0,
    VC1,
    NO_VC_TRANSITION,
    PORT_LOCAL,
    PORT_NORTH,
    PORT_EAST,
    PORT_SOUTH,
    PORT_WEST,
    pack_header_flit,
    pack_single_flit_aer,
    unpack_header_flit,
)
from ora_fabric.router import (
    NoCRouter,
    NoCNetwork,
    NetworkInterface,
    Packet,
)


class TestTableLessProperties:
    def test_strictly_no_routing_table(self):
        router = NoCRouter(tile_id=0)
        assert not hasattr(router, "routing_table")
        assert not hasattr(router, "route_table")
        assert not hasattr(router, "lookup_table")
        assert not hasattr(router, "forwarding_table")
        assert not hasattr(router, "table")


class TestHeaderProcessingAndShifting:
    def test_port_decode_and_shift(self):
        r0 = NoCRouter(tile_id=0)
        r1 = NoCRouter(tile_id=1)
        r0.connect(PORT_EAST, r1, PORT_WEST)

        flit = pack_header_flit(
            vc_id=VC0,
            hop_count=2,
            chained=False,
            vc_transition_hop=NO_VC_TRANSITION,
            direction_vector=[PORT_EAST, PORT_NORTH],
        )

        r0.receive_flit(PORT_LOCAL, flit)
        r0.step()

        buf_r1 = r1.in_buffers[(PORT_WEST, VC0)]
        assert len(buf_r1) == 1
        f1 = unpack_header_flit(buf_r1[0])
        assert f1.hop_count == 1
        assert f1.direction_vector[0] == PORT_NORTH


class TestOrderIndependentCycleAccuracy:
    def test_forward_order_vs_reverse_order_delivery(self):
        """Cycle-accuracy verification:
        Packets must take the exact same number of cycles to reach the destination
        regardless of whether routers are stepped in forward order (0->1->2) or
        reverse order (2->1->0), thanks to the 2-phase evaluate/commit architecture.
        """
        for reverse in (False, True):
            r0 = NoCRouter(tile_id=0)
            r1 = NoCRouter(tile_id=1)
            r2 = NoCRouter(tile_id=2)
            r0.connect(PORT_EAST, r1, PORT_WEST)
            r1.connect(PORT_EAST, r2, PORT_WEST)

            hdr = pack_header_flit(
                vc_id=VC0, hop_count=2, chained=False,
                vc_transition_hop=NO_VC_TRANSITION, direction_vector=[PORT_EAST, PORT_EAST]
            )
            r0.receive_flit(PORT_LOCAL, hdr)

            routers = [r2, r1, r0] if reverse else [r0, r1, r2]
            net = NoCNetwork(routers=routers)

            # Exactly 2 hops = 2 network cycles to arrive at r2
            cycles = 0
            while not r2.ejection_queue and cycles < 10:
                net.step()
                cycles += 1

            # Exactly 2 inter-router link hops + 1 local crossbar ejection = 3 cycles
            assert cycles == 3
            assert len(r2.ejection_queue) == 1


class TestVirtualChannelIndependence:
    def test_vc1_progress_during_active_vc0_wormhole(self):
        """Cross-VC deadlock freedom verification (Advisor-revised scenario):

        Step 1: Inject the VC0 packet FIRST and step once so the VC0 header
                acquires the (PORT_EAST, VC0) wormhole lock.
        Step 2: Then inject the VC1 packet at another input port.
        Assert:  Both locks coexist simultaneously, and VC1 makes forward
                 progress (delivered) while the VC0 wormhole still holds its lock.
        """
        r0 = NoCRouter(tile_id=0)
        r1 = NoCRouter(tile_id=1)
        r0.connect(PORT_EAST, r1, PORT_WEST)

        # VC0 4-flit wormhole packet on PORT_LOCAL
        vc0_hdr = pack_header_flit(vc_id=VC0, hop_count=1, chained=False,
                                   vc_transition_hop=NO_VC_TRANSITION, direction_vector=[PORT_EAST])
        vc0_b1 = (FLIT_TYPE_BODY << 30) | (VC0 << 28) | 0x11
        vc0_b2 = (FLIT_TYPE_BODY << 30) | (VC0 << 28) | 0x22
        vc0_tail = (FLIT_TYPE_TAIL << 30) | (VC0 << 28) | 0x33
        for f in (vc0_hdr, vc0_b1, vc0_b2, vc0_tail):
            r0.receive_flit(PORT_LOCAL, f)

        # Step 1: VC0 header acquires (PORT_EAST, VC0) lock
        r0.step()
        assert (PORT_EAST, VC0) in r0.crossbar_locks
        assert len(r1.in_buffers[(PORT_WEST, VC0)]) == 1  # VC0 header arrived

        # Step 2: NOW inject the VC1 packet on PORT_NORTH
        vc1_hdr = pack_header_flit(vc_id=VC1, hop_count=1, chained=False,
                                   vc_transition_hop=NO_VC_TRANSITION, direction_vector=[PORT_EAST])
        vc1_tail = (FLIT_TYPE_TAIL << 30) | (VC1 << 28) | 0x99
        r0.receive_flit(PORT_NORTH, vc1_hdr)
        r0.receive_flit(PORT_NORTH, vc1_tail)

        # Cycle: VC1 header acquires the INDEPENDENT (PORT_EAST, VC1) lock!
        r0.step()
        assert (PORT_EAST, VC0) in r0.crossbar_locks   # VC0 lock still held
        assert (PORT_EAST, VC1) in r0.crossbar_locks   # VC1 lock coexists!

        # Both locks coexist: monotonic VC layering has zero cross-VC dependency
        assert r0.crossbar_locks[(PORT_EAST, VC0)].in_port == PORT_LOCAL
        assert r0.crossbar_locks[(PORT_EAST, VC1)].in_port == PORT_NORTH

        # VC1 header made forward progress through the shared physical link
        assert len(r1.in_buffers[(PORT_WEST, VC1)]) == 1

        # Drain: run to completion, both packets fully delivered
        for _ in range(10):
            r0.step()
        assert len(r1.in_buffers[(PORT_WEST, VC0)]) == 4
        assert len(r1.in_buffers[(PORT_WEST, VC1)]) == 2

    def test_vc0_advances_under_saturated_vc1_round_robin(self):
        """Round-robin fairness: sustained VC1 traffic must not starve VC0.
        VC1 is kept saturated (always has a flit ready); VC0 must still advance.
        """
        r0 = NoCRouter(tile_id=0)
        r1 = NoCRouter(tile_id=1)
        r0.connect(PORT_EAST, r1, PORT_WEST)

        vc0_hdr = pack_header_flit(vc_id=VC0, hop_count=1, chained=False,
                                   vc_transition_hop=NO_VC_TRANSITION, direction_vector=[PORT_EAST])
        vc0_tail = (FLIT_TYPE_TAIL << 30) | (VC0 << 28) | 0x55
        r0.receive_flit(PORT_LOCAL, vc0_hdr)
        r0.receive_flit(PORT_LOCAL, vc0_tail)

        # Saturate VC1: many flits always waiting on PORT_NORTH
        vc1_hdr = pack_header_flit(vc_id=VC1, hop_count=1, chained=False,
                                   vc_transition_hop=NO_VC_TRANSITION, direction_vector=[PORT_EAST])
        for _ in range(8):
            r0.receive_flit(PORT_NORTH, vc1_hdr)

        # Run several cycles: VC0 packet (hdr+tail) must still be delivered
        vc0_delivered = 0
        for _ in range(12):
            # Keep VC1 saturated each cycle
            while len(r0.in_buffers[(PORT_NORTH, VC1)]) < 4:
                r0.receive_flit(PORT_NORTH, vc1_hdr)
            r0.step()
            vc0_delivered = len(r1.in_buffers[(PORT_WEST, VC0)])
            if vc0_delivered == 2:
                break

        assert vc0_delivered == 2  # VC0 header AND tail advanced despite VC1 saturation

    def test_single_flit_per_link_constraint(self):
        """Physical link constraint: at most one flit per link per cycle."""
        r0 = NoCRouter(tile_id=0)
        r1 = NoCRouter(tile_id=1)
        r0.connect(PORT_EAST, r1, PORT_WEST)

        f0 = pack_header_flit(vc_id=VC0, hop_count=1, chained=False,
                              vc_transition_hop=NO_VC_TRANSITION, direction_vector=[PORT_EAST])
        f1 = pack_header_flit(vc_id=VC1, hop_count=1, chained=False,
                              vc_transition_hop=NO_VC_TRANSITION, direction_vector=[PORT_EAST])
        r0.receive_flit(PORT_LOCAL, f0)
        r0.receive_flit(PORT_NORTH, f1)

        r0.step()
        total_r1_flits = (
            len(r1.in_buffers[(PORT_WEST, VC0)]) + len(r1.in_buffers[(PORT_WEST, VC1)])
        )
        assert total_r1_flits == 1

    def test_two_inputs_ejecting_same_local_vc_stall(self):
        """Eject-lock contention: two input ports eject onto the same local VC
        in the same cycle. The second header must stall until the first packet's
        Tail releases (PORT_LOCAL, VC0), preventing NI reassembly corruption.
        """
        r0 = NoCRouter(tile_id=0)

        # Packet A on PORT_NORTH: 1-hop route ending in eject at this router
        hdr_a = pack_header_flit(vc_id=VC0, hop_count=1, chained=False,
                                 vc_transition_hop=NO_VC_TRANSITION, direction_vector=[PORT_EAST])
        # Note: PORT_EAST has no link attached; force eject via hop-0 route instead
        hdr_a0 = pack_header_flit(vc_id=VC0, hop_count=0, chained=False,
                                  vc_transition_hop=NO_VC_TRANSITION, direction_vector=[])
        tail_a = (FLIT_TYPE_TAIL << 30) | (VC0 << 28) | 0xAA
        r0.receive_flit(PORT_NORTH, hdr_a0)
        r0.receive_flit(PORT_NORTH, tail_a)

        # Packet B on PORT_SOUTH: also ejects onto (PORT_LOCAL, VC0)
        hdr_b0 = pack_header_flit(vc_id=VC0, hop_count=0, chained=False,
                                  vc_transition_hop=NO_VC_TRANSITION, direction_vector=[])
        tail_b = (FLIT_TYPE_TAIL << 30) | (VC0 << 28) | 0xBB
        r0.receive_flit(PORT_SOUTH, hdr_b0)
        r0.receive_flit(PORT_SOUTH, tail_b)

        # Cycle 1: only ONE packet may hold the (PORT_LOCAL, VC0) ejection lock
        r0.step()
        assert (PORT_LOCAL, VC0) in r0.crossbar_locks
        assert len(r0.ejection_queue) == 1  # Only packet A's header ejected

        # The other packet's header stalls (still in its input buffer)
        remaining = len(r0.in_buffers[(PORT_SOUTH, VC0)])
        assert remaining == 2  # hdr_b0 + tail_b still waiting

        # Cycle 2: packet A's tail streams through and releases the lock; in the
        # same cycle, B (on a later port in the iteration order) acquires the
        # freed (PORT_LOCAL, VC0) lock and ejects its header.
        r0.step()
        assert (PORT_LOCAL, VC0) in r0.crossbar_locks
        assert r0.crossbar_locks[(PORT_LOCAL, VC0)].in_port == PORT_SOUTH  # now B's lock
        assert len(r0.ejection_queue) == 3  # A.hdr, A.tail, then B.hdr

        # Ejection order is strictly non-interleaved: A complete before B
        ejected_payloads = [f & 0xFFFFFFF for f in list(r0.ejection_queue)]
        ejected_types = [(f >> 30) & 0b11 for f in list(r0.ejection_queue)]
        assert ejected_payloads[1] == 0xAA  # A's tail payload
        assert ejected_types[2] == FLIT_TYPE_HEADER  # B's header flit

        # Cycle 3: packet B's tail streams through and fully releases the lock
        r0.step()
        assert (PORT_LOCAL, VC0) not in r0.crossbar_locks
        assert len(r0.ejection_queue) == 4  # A.hdr, A.tail, B.hdr, B.tail
        assert list(r0.ejection_queue)[3] & 0xFFFFFFF == 0xBB  # B's tail payload

class TestChainedHeaderTraversal:
    def test_chained_header_strict_destination_delivery(self):
        """Chained header traversal:
        2-hop route split into 2 chained headers (1 hop each).
        The packet must be delivered STRICTLY at r2, and r1's ejection queue must remain empty.
        """
        r0 = NoCRouter(tile_id=0)
        r1 = NoCRouter(tile_id=1)
        r2 = NoCRouter(tile_id=2)
        r0.connect(PORT_EAST, r1, PORT_WEST)
        r1.connect(PORT_EAST, r2, PORT_WEST)

        hdr1 = pack_header_flit(
            vc_id=VC0, hop_count=1, chained=True,
            vc_transition_hop=NO_VC_TRANSITION, direction_vector=[PORT_EAST]
        )
        hdr2 = pack_header_flit(
            vc_id=VC0, hop_count=1, chained=False,
            vc_transition_hop=NO_VC_TRANSITION, direction_vector=[PORT_EAST]
        )
        body = (FLIT_TYPE_BODY << 30) | (VC0 << 28) | 0x123
        tail = (FLIT_TYPE_TAIL << 30) | (VC0 << 28) | 0x456

        for f in (hdr1, hdr2, body, tail):
            r0.receive_flit(PORT_LOCAL, f)

        net = NoCNetwork(routers=[r0, r1, r2])
        for _ in range(15):
            net.step()

        # r1 is an intermediate transit node: its ejection queue must be completely empty!
        assert len(r1.ejection_queue) == 0
        assert r1.chained_headers_dropped == 1

        # r2 is the final destination: packet delivered with payload preserved!
        assert len(r2.ejection_queue) == 3  # hdr2, body, tail
        types = [(f >> 30) & 0b11 for f in r2.ejection_queue]
        assert types == [FLIT_TYPE_HEADER, FLIT_TYPE_BODY, FLIT_TYPE_TAIL]


class TestMonotonicVcPromotion:
    def test_multi_flit_packet_promotion_and_ni_delivery(self):
        """Core H2 verification: A Header + Body + Tail multi-flit packet
        undergoes Monotonic VC promotion mid-route.
        Subsequent Body and Tail flits must have their VC field rewritten to VC1
        and be delivered at the destination NI without drop or corruption.
        """
        r0 = NoCRouter(tile_id=0)
        r1 = NoCRouter(tile_id=1)
        r2 = NoCRouter(tile_id=2)
        r0.connect(PORT_EAST, r1, PORT_WEST)
        r1.connect(PORT_EAST, r2, PORT_WEST)

        ni0 = NetworkInterface(tile_id=0, router=r0)
        ni2 = NetworkInterface(tile_id=2, router=r2)

        hdr_flit = pack_header_flit(
            vc_id=VC0,
            hop_count=2,
            chained=False,
            vc_transition_hop=1,  # Promotes to VC1 at r1!
            direction_vector=[PORT_EAST, PORT_EAST],
        )
        packet = Packet(
            src_tile=0,
            dst_tile=2,
            headers=[hdr_flit],
            payload=[0xAAAAAAA, 0xBBBBBBB, 0xCCCCCCC],
        )

        ni0.send_packet(packet)

        net = NoCNetwork(routers=[r0, r1, r2])
        for _ in range(25):
            ni0.step()
            net.step()
            ni2.step()

        assert r1.promotions_executed == 1

        # Delivered packet payload must be bit-exact
        assert len(ni2.rx_packets) == 1
        delivered = ni2.rx_packets[0]
        assert delivered.payload == [0xAAAAAAA, 0xBBBBBBB, 0xCCCCCCC]


class TestAerSingleFlit:
    def test_aer_direct_forwarding(self):
        r0 = NoCRouter(tile_id=0)
        r1 = NoCRouter(tile_id=1)
        r0.connect(PORT_NORTH, r1, PORT_SOUTH)

        aer_flit = pack_single_flit_aer(
            hop_count=1, direction_vector=[PORT_NORTH], neuron_address=0xABCDE
        )

        r0.receive_flit(PORT_LOCAL, aer_flit)
        r0.step()

        buf_r1 = r1.in_buffers[(PORT_SOUTH, VC0)]
        assert len(buf_r1) == 1
        received = buf_r1[0]
        assert (received >> 30) == FLIT_TYPE_SINGLE_AER
        assert received & 0xFFFFF == 0xABCDE
        assert ((received >> 26) & 0b11) == 0


class TestPerPortRoundRobin:
    """The RR pointer is per physical output link and is a pure function of
    buffer state + per-port history, not of global iteration order."""

    @staticmethod
    def _hdr(vc: int, port: int) -> int:
        return pack_header_flit(vc_id=vc, hop_count=1, chained=False,
                                vc_transition_hop=NO_VC_TRANSITION,
                                direction_vector=[port])

    @staticmethod
    def _tail(vc: int, data: int) -> int:
        return (FLIT_TYPE_TAIL << 30) | (vc << 28) | data

    def test_rr_alternates_vc_classes_on_one_link(self):
        """Two saturated VC classes on one link must strictly alternate."""
        r0 = NoCRouter(tile_id=0, buffer_depth=16)
        r1 = NoCRouter(tile_id=1, buffer_depth=64)
        r0.connect(PORT_EAST, r1, PORT_WEST)

        # VC0 and VC1 each send a long wormhole on the same East link
        r0.receive_flit(PORT_LOCAL, self._hdr(VC0, PORT_EAST))
        r0.receive_flit(PORT_NORTH, self._hdr(VC1, PORT_EAST))
        for i in range(6):
            r0.receive_flit(PORT_LOCAL, (FLIT_TYPE_BODY << 30) | (VC0 << 28) | i)
            r0.receive_flit(PORT_NORTH, (FLIT_TYPE_BODY << 30) | (VC1 << 28) | i)

        served = []
        for _ in range(10):
            before0 = len(r1.in_buffers[(PORT_WEST, VC0)])
            before1 = len(r1.in_buffers[(PORT_WEST, VC1)])
            r0.step()
            if len(r1.in_buffers[(PORT_WEST, VC0)]) > before0:
                served.append(VC0)
            elif len(r1.in_buffers[(PORT_WEST, VC1)]) > before1:
                served.append(VC1)

        # Fresh link starts with VC1, then strictly alternates
        assert served[0] == VC1
        for a, b in zip(served, served[1:]):
            assert a != b, f"RR did not alternate: {served}"

    def test_rr_pointers_are_independent_per_link(self):
        """Traffic on the North link must not shift the East link's RR state."""
        r0 = NoCRouter(tile_id=0, buffer_depth=16)
        east = NoCRouter(tile_id=1, buffer_depth=64)
        north = NoCRouter(tile_id=2, buffer_depth=64)
        r0.connect(PORT_EAST, east, PORT_WEST)
        r0.connect(PORT_NORTH, north, PORT_SOUTH)

        # Only VC0 uses North for a while: this moves North's pointer only
        r0.receive_flit(PORT_WEST, self._hdr(VC0, PORT_NORTH))
        for i in range(3):
            r0.receive_flit(PORT_WEST, (FLIT_TYPE_BODY << 30) | (VC0 << 28) | i)
        for _ in range(4):
            r0.step()
        assert r0._rr_last_served.get(PORT_NORTH) == VC0
        assert PORT_EAST not in r0._rr_last_served  # East untouched

        # Now both classes contend for East: a fresh East link must still
        # give VC1 the first turn, regardless of North's history.
        r0.receive_flit(PORT_LOCAL, self._hdr(VC0, PORT_EAST))
        r0.receive_flit(PORT_SOUTH, self._hdr(VC1, PORT_EAST))
        r0.step()
        assert len(east.in_buffers[(PORT_WEST, VC1)]) == 1
        assert len(east.in_buffers[(PORT_WEST, VC0)]) == 0

    def test_arbitration_is_deterministic_across_runs(self):
        """Identical stimulus must yield identical per-cycle forwarding,
        proving the order is a function of state, not of dict history."""
        def run() -> list[tuple[int, int]]:
            r0 = NoCRouter(tile_id=0, buffer_depth=16)
            r1 = NoCRouter(tile_id=1, buffer_depth=64)
            r0.connect(PORT_EAST, r1, PORT_WEST)
            for port, vc in ((PORT_LOCAL, VC0), (PORT_NORTH, VC1),
                             (PORT_SOUTH, VC0), (PORT_WEST, VC1)):
                r0.receive_flit(port, self._hdr(vc, PORT_EAST))
                r0.receive_flit(port, self._tail(vc, port))
            trace = []
            for cyc in range(12):
                r0.evaluate_cycle()
                if PORT_EAST in r0.staged_tx:
                    trace.append((cyc, r0.staged_tx[PORT_EAST][2]))
                r0.commit_cycle()
            return trace

        first = run()
        assert len(first) == 8  # 4 packets x (header + tail)
        for _ in range(5):
            assert run() == first
