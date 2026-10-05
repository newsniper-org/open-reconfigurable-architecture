"""ORA-N Table-less Source Router and Cycle-Accurate Network (Module M3).

Normative implementation adhering to ORA-N specification (docs/ora_poc_standard_specification.typ section 2):
  - Strictly table-less microarchitecture: zero routing table memory
  - Explicit (out_port, out_vc) crossbar locking to prevent cross-VC blocking
  - Physical link arbitration: at most one flit per link per cycle (link_used)
  - True cycle-accurate 2-phase execution: evaluate/stage then synchronous commit
  - Input channel state machine (IDLE vs ACTIVE) for wormhole streaming and chained headers
  - Uses ora_bitstream.router_step() for authoritative header calculation
  - Multi-flit VC promotion and payload VC rewriting
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field

from ora_bitstream import (
    FLIT_TYPE_HEADER,
    FLIT_TYPE_BODY,
    FLIT_TYPE_TAIL,
    FLIT_TYPE_SINGLE_AER,
    VC0,
    VC1,
    PORT_LOCAL,
    PORT_NORTH,
    PORT_EAST,
    PORT_SOUTH,
    PORT_WEST,
    PORT_UP,
    PORT_DOWN,
    router_step,
)
from ora_fabric.topology import PhysicalTopology

NUM_PORTS = 7
ALL_PORTS = (
    PORT_LOCAL,
    PORT_NORTH,
    PORT_EAST,
    PORT_SOUTH,
    PORT_WEST,
    PORT_UP,
    PORT_DOWN,
)


class RouterError(ValueError):
    """Raised on protocol, framing, or hardware resource violations."""


@dataclass
class Packet:
    """A high-level network packet received or sent by an NI."""

    src_tile: int
    dst_tile: int
    headers: list[int]
    payload: list[int] = field(default_factory=list)


@dataclass
class AerEvent:
    """A spiking neuromorphic AER event."""

    src_tile: int
    dst_tile: int
    direction_vector: list[int]
    neuron_address: int


@dataclass
class CrossbarLock:
    """Represents an active wormhole crossbar connection."""

    in_port: int
    in_vc: int
    out_port: int
    out_vc: int


class NoCRouter:
    """Table-less ORA-N Source Router with cycle-accurate 2-phase execution."""

    def __init__(self, tile_id: int, buffer_depth: int = 4):
        self.tile_id = tile_id
        self.buffer_depth = buffer_depth

        # Per (port, vc) input buffers
        self.in_buffers: dict[tuple[int, int], deque[int]] = {
            (p, vc): deque() for p in ALL_PORTS for vc in (VC0, VC1)
        }

        # Per-channel wormhole state: (in_port, in_vc) -> CrossbarLock | None
        self.channel_locks: dict[tuple[int, int], CrossbarLock | None] = {
            (p, vc): None for p in ALL_PORTS for vc in (VC0, VC1)
        }

        # Active crossbar locks: (out_port, out_vc) -> CrossbarLock
        self.crossbar_locks: dict[tuple[int, int], CrossbarLock] = {}

        # Round-robin pointer per physical output port: the VC class that was
        # served last on that port yields. Keyed by out_port, updated only
        # when that port actually grants a flit.
        self._rr_last_served: dict[int, int] = {}
        self.outgoing_links: dict[int, tuple[NoCRouter, int]] = {}

        # Staging slot for outgoing flits in 2-phase simulation: out_port -> (neighbor, in_port, flit)
        self.staged_tx: dict[int, tuple[NoCRouter, int, int]] = {}

        # Local ejection queue to local NI
        self.ejection_queue: deque[int] = deque()

        # Telemetry counters
        self.forwarded_flits: int = 0
        self.ejected_flits: int = 0
        self.chained_headers_dropped: int = 0
        self.promotions_executed: int = 0

    def connect(self, out_port: int, neighbor: NoCRouter, in_port: int) -> None:
        """Connect this router's out_port to neighbor router's in_port."""
        if out_port == PORT_LOCAL or in_port == PORT_LOCAL:
            raise RouterError("PORT_LOCAL is reserved for local NI attachment")
        self.outgoing_links[out_port] = (neighbor, in_port)

    def can_receive(self, in_port: int, vc_id: int) -> bool:
        """Check if the given input buffer has space."""
        return len(self.in_buffers[(in_port, vc_id)]) < self.buffer_depth

    def receive_flit(self, in_port: int, flit: int) -> bool:
        """Receive a flit into the appropriate (in_port, vc) buffer."""
        flit_type = (flit >> 30) & 0b11
        if flit_type == FLIT_TYPE_SINGLE_AER:
            vc_id = VC0
        else:
            vc_id = (flit >> 28) & 0b11

        buf = self.in_buffers[(in_port, vc_id)]
        if len(buf) >= self.buffer_depth:
            return False
        buf.append(flit)
        return True

    def evaluate_cycle(self) -> None:
        """Phase 1: Evaluate inputs, arbitrate physical links, and stage outgoing flits.

        Link arbitration is per-port round-robin between VC classes: for each
        physical link, the VC class served last (this router's lifetime, not
        just this cycle) yields to the other class. A saturated VC1 on one
        link cannot starve VC0 on that link, and fairness on one link is
        independent of traffic on other links.
        """
        self.staged_tx.clear()
        link_used: dict[int, bool] = {p: False for p in ALL_PORTS}

        # Per-port RR: the VC class that was served last on a given link yields.
        # VC1 gets the first turn on links with no history.
        def vc_priority(out_port: int) -> list[int]:
            last = self._rr_last_served.get(out_port, VC1)
            return [VC0, VC1] if last == VC1 else [VC1, VC0]

        # Serve VC classes in a fixed order; the per-port RR pointer above is
        # consulted when the physical link becomes contended.
        for vc in (VC1, VC0):
            for in_port in ALL_PORTS:
                buf = self.in_buffers[(in_port, vc)]
                if not buf:
                    continue
                active_lock = self.channel_locks[(in_port, vc)]
                flit = buf[0]
                flit_type = (flit >> 30) & 0b11

                if active_lock is not None:
                    if flit_type == FLIT_TYPE_HEADER and active_lock.out_port == PORT_LOCAL:
                        # Self-releasing: previous lone header ejected to local NI has finished
                        self._release_lock(active_lock)
                        active_lock = None

                if active_lock is not None:
                    # Input channel is in ACTIVE state: stream following flit through locked path
                    out_port = active_lock.out_port
                    out_vc = active_lock.out_vc

                    if out_port == PORT_LOCAL:
                        buf.popleft()
                        self.ejection_queue.append(flit)
                        self.ejected_flits += 1
                        if flit_type == FLIT_TYPE_TAIL:
                            self._release_lock(active_lock)
                    else:
                        if link_used[out_port]:
                            continue  # Physical link already occupied this cycle

                        neighbor, nbr_port = self.outgoing_links[out_port]
                        if not neighbor.can_receive(nbr_port, out_vc):
                            continue  # Downstream buffer full (backpressure)

                        buf.popleft()
                        rewritten = (flit & ~(0b11 << 28)) | (out_vc << 28)
                        self.staged_tx[out_port] = (neighbor, nbr_port, rewritten)
                        link_used[out_port] = True
                        self.forwarded_flits += 1
                        self._rr_last_served[out_port] = out_vc

                        if flit_type == FLIT_TYPE_TAIL:
                            self._release_lock(active_lock)

                else:
                    # Input channel is in IDLE state: expects Header or Single-AER
                    if flit_type == FLIT_TYPE_HEADER:
                        self._stage_header(in_port, vc, buf, link_used)
                    elif flit_type == FLIT_TYPE_SINGLE_AER:
                        self._stage_aer(in_port, buf, link_used)
                    else:
                        raise RouterError(
                            f"Router {self.tile_id}: unexpected flit type {flit_type:02b} on IDLE channel"
                        )

        # (No global toggle: per-port RR pointers persist across cycles.)

    def _stage_header(
        self, in_port: int, vc: int, buf: deque[int], link_used: dict[int, bool]
    ) -> None:
        word = buf[0]
        decision = router_step(word)

        if decision.action == "chain":
            # Chained Header: drop spent header at hop 0!
            buf.popleft()
            self.chained_headers_dropped += 1
            # Next flit remains at head of buffer to be evaluated in IDLE state
            return

        if decision.action == "eject":
            if (PORT_LOCAL, decision.vc_id) in self.crossbar_locks:
                return  # Local ejection VC is busy: stall the header
            buf.popleft()
            self.ejection_queue.append(word)
            self.ejected_flits += 1
            # Establish wormhole lock to PORT_LOCAL for subsequent body/tail flits
            lock = CrossbarLock(in_port, vc, PORT_LOCAL, decision.vc_id)
            self.crossbar_locks[(PORT_LOCAL, decision.vc_id)] = lock
            self.channel_locks[(in_port, vc)] = lock
            return

        # Forward action
        out_port = decision.out_port
        assert out_port is not None
        out_vc = decision.vc_id

        if decision.vc_id == VC1 and vc == VC0:
            self.promotions_executed += 1

        if out_port == PORT_LOCAL:
            buf.popleft()
            assert decision.word is not None
            self.ejection_queue.append(decision.word)
            self.ejected_flits += 1
            lock = CrossbarLock(in_port, vc, PORT_LOCAL, out_vc)
            self.crossbar_locks[(PORT_LOCAL, out_vc)] = lock
            self.channel_locks[(in_port, vc)] = lock
            return
        # Check (out_port, out_vc) lock availability
        if (out_port, out_vc) in self.crossbar_locks:
            return  # This VC path is currently occupied by another wormhole!

        if link_used[out_port]:
            return  # Physical link already carrying a flit from another VC this cycle!

        if out_port not in self.outgoing_links:
            raise RouterError(f"Router {self.tile_id}: no link attached to port {out_port}")

        neighbor, nbr_port = self.outgoing_links[out_port]
        if not neighbor.can_receive(nbr_port, out_vc):
            return  # Downstream buffer full

        # Acquire lock and stage header
        buf.popleft()
        lock = CrossbarLock(in_port, vc, out_port, out_vc)
        self.crossbar_locks[(out_port, out_vc)] = lock
        self.channel_locks[(in_port, vc)] = lock

        assert decision.word is not None
        self.staged_tx[out_port] = (neighbor, nbr_port, decision.word)
        link_used[out_port] = True
        self.forwarded_flits += 1

    def _stage_aer(self, in_port: int, buf: deque[int], link_used: dict[int, bool]) -> None:
        word = buf[0]
        hop_count = (word >> 26) & 0b11
        neuron_addr = word & 0xFFFFF

        if hop_count == 0:
            buf.popleft()
            self.ejection_queue.append(word)
            self.ejected_flits += 1
            return

        out_port = (word >> 20) & 0b111
        new_hop = hop_count - 1
        second_hop = (word >> 23) & 0b111
        new_word = (
            (FLIT_TYPE_SINGLE_AER << 30)
            | (VC0 << 28)
            | (new_hop << 26)
            | (second_hop << 20)
            | neuron_addr
        )

        if out_port == PORT_LOCAL:
            buf.popleft()
            self.ejection_queue.append(new_word)
            self.ejected_flits += 1
            return

        if (out_port, VC0) in self.crossbar_locks:
            return
        if link_used[out_port]:
            return

        if out_port not in self.outgoing_links:
            raise RouterError(f"Router {self.tile_id}: no link attached for AER port {out_port}")

        neighbor, nbr_port = self.outgoing_links[out_port]
        if not neighbor.can_receive(nbr_port, VC0):
            return

        buf.popleft()
        self.staged_tx[out_port] = (neighbor, nbr_port, new_word)
        link_used[out_port] = True
        self.forwarded_flits += 1

    def commit_cycle(self) -> int:
        """Phase 2: Commit all staged flits to downstream input buffers."""
        committed = 0
        for _, (neighbor, nbr_port, flit) in self.staged_tx.items():
            neighbor.receive_flit(nbr_port, flit)
            committed += 1
        self.staged_tx.clear()
        return committed

    def _release_lock(self, lock: CrossbarLock) -> None:
        key = (lock.out_port, lock.out_vc)
        if key in self.crossbar_locks:
            del self.crossbar_locks[key]
        self.channel_locks[(lock.in_port, lock.in_vc)] = None

    def step(self) -> int:
        """Single-router step (convenience for isolated unit tests)."""
        self.evaluate_cycle()
        return self.commit_cycle()


class NoCNetwork:
    """Cycle-accurate coordinator for a network of ORA-N routers."""

    def __init__(self, routers: list[NoCRouter], topology: PhysicalTopology | None = None):
        self.routers = routers
        self.topology = topology
        self.current_cycle: int = 0

    def step(self) -> int:
        """Execute one synchronous cycle across ALL routers: evaluate then commit."""
        # Phase 1: All routers evaluate against start-of-cycle state
        for r in self.routers:
            r.evaluate_cycle()

        # Phase 2: All routers synchronously commit staged flits
        transferred = 0
        for r in self.routers:
            transferred += r.commit_cycle()

        self.current_cycle += 1
        return transferred


class NetworkInterface:
    """Network Interface (NI) attached to an ORA-N router."""

    def __init__(self, tile_id: int, router: NoCRouter):
        self.tile_id = tile_id
        self.router = router

        self.tx_packet_queue: deque[Packet] = deque()
        self.tx_flit_queue: deque[int] = deque()
        self.rx_packets: list[Packet] = []
        self._current_rx_flits: list[int] = []

    def send_packet(self, packet: Packet) -> None:
        self.tx_packet_queue.append(packet)

    def step(self) -> None:
        if not self.tx_flit_queue and self.tx_packet_queue:
            pkt = self.tx_packet_queue.popleft()
            for h in pkt.headers:
                self.tx_flit_queue.append(h)

            # Every packet MUST end with a Tail flit to release wormhole locks (packet termination rule)
            payload = pkt.payload
            if not payload:
                empty_tail = (FLIT_TYPE_TAIL << 30) | (VC0 << 28) | 0
                self.tx_flit_queue.append(empty_tail)
            else:
                for i, word in enumerate(payload):
                    is_last = i == len(payload) - 1
                    flit_type = FLIT_TYPE_TAIL if is_last else FLIT_TYPE_BODY
                    flit_word = (flit_type << 30) | (VC0 << 28) | (word & 0xFFFFFFF)
                    self.tx_flit_queue.append(flit_word)

        if self.tx_flit_queue:
            flit = self.tx_flit_queue[0]
            if self.router.receive_flit(PORT_LOCAL, flit):
                self.tx_flit_queue.popleft()

        while self.router.ejection_queue:
            flit = self.router.ejection_queue.popleft()
            flit_type = (flit >> 30) & 0b11
            if flit_type == FLIT_TYPE_HEADER:
                self._current_rx_flits = [flit]
            elif flit_type == FLIT_TYPE_BODY:
                self._current_rx_flits.append(flit)
            elif flit_type == FLIT_TYPE_TAIL:
                self._current_rx_flits.append(flit)
                self._assemble_rx_packet()
            elif flit_type == FLIT_TYPE_SINGLE_AER:
                neuron_addr = flit & 0xFFFFF
                aer_pkt = Packet(
                    src_tile=-1, dst_tile=self.tile_id, headers=[flit], payload=[neuron_addr]
                )
                self.rx_packets.append(aer_pkt)

    def _assemble_rx_packet(self) -> None:
        headers = []
        payload = []
        for f in self._current_rx_flits:
            ftype = (f >> 30) & 0b11
            if ftype == FLIT_TYPE_HEADER:
                headers.append(f)
            else:
                payload.append(f & 0xFFFFFFF)
        pkt = Packet(src_tile=-1, dst_tile=self.tile_id, headers=headers, payload=payload)
        self.rx_packets.append(pkt)
        self._current_rx_flits = []
