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

        # Flits popped from each input buffer during the current evaluate
        # phase. Added back in can_receive() so credit checks see the
        # start-of-cycle occupancy (RTL: registered count < depth),
        # independent of the order in which routers are evaluated.
        self._pops: dict[tuple[int, int], int] = {
            (p, vc): 0 for p in ALL_PORTS for vc in (VC0, VC1)
        }

        # (out_port, out_vc) locks held at the start of the current cycle.
        # A lock released by a Tail is re-grantable only in the next cycle.
        self._locks_at_start: frozenset[tuple[int, int]] = frozenset()

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
        """Start-of-cycle credit check for the given input buffer.

        Pops already made by this router in the current evaluate phase are
        counted back, so a sender sees the same answer whether this router
        evaluated before or after it (RTL: registered occupancy < depth).
        """
        key = (in_port, vc_id)
        return len(self.in_buffers[key]) + self._pops[key] < self.buffer_depth

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

    def _pop(self, in_port: int, vc: int) -> int:
        self._pops[(in_port, vc)] += 1
        return self.in_buffers[(in_port, vc)].popleft()

    def _lock_free(self, key: tuple[int, int]) -> bool:
        """A lock is grantable only if it was free at the start of the cycle
        and nobody acquired it earlier in this cycle."""
        return key not in self._locks_at_start and key not in self.crossbar_locks

    def _request(self, in_port: int, vc: int) -> tuple[int, int] | None:
        """Side-effect-free probe: the (out_port, out_vc) this channel's head
        flit competes for this cycle. PORT_LOCAL (ejection) is a port like any
        other. Returns None for an empty buffer, a chained-header drop, a
        self-releasing lone header, or a protocol error (raised later).
        """
        buf = self.in_buffers[(in_port, vc)]
        if not buf:
            return None
        flit = buf[0]
        flit_type = (flit >> 30) & 0b11
        lock = self.channel_locks[(in_port, vc)]

        if lock is not None:
            if flit_type == FLIT_TYPE_HEADER and lock.out_port == PORT_LOCAL:
                return None
            return (lock.out_port, lock.out_vc)

        if flit_type == FLIT_TYPE_HEADER:
            decision = router_step(flit)
            if decision.action == "chain":
                return None
            if decision.action == "eject":
                return (PORT_LOCAL, decision.vc_id)
            assert decision.out_port is not None
            return (decision.out_port, decision.vc_id)
        if flit_type == FLIT_TYPE_SINGLE_AER:
            if (flit >> 26) & 0b11 == 0:
                return (PORT_LOCAL, VC0)
            return ((flit >> 20) & 0b111, VC0)
        return None

    def _arbitration_order(self) -> list[tuple[int, int]]:
        """Order input channels so each output port is offered first to its
        round-robin winner.

        Requests are grouped by output port. Within a port, channels whose
        requested out_vc differs from the class served last on that port go
        first; ties are broken by (in_port, in_vc) ascending. Channels with no
        port request (chain drop, self-release) are appended afterwards; they
        touch no shared resource. The order is a pure function of buffer
        state, locks, and the per-port RR pointers.
        """
        wants: dict[int, list[tuple[int, int, int]]] = {}
        for in_port in sorted(ALL_PORTS):
            for vc in (VC0, VC1):
                req = self._request(in_port, vc)
                if req is not None:
                    wants.setdefault(req[0], []).append((in_port, vc, req[1]))

        order: list[tuple[int, int]] = []
        for out_port in sorted(wants):
            last = self._rr_last_served.get(out_port, VC0)  # VC1 first on fresh ports
            cands = wants[out_port]
            order.extend((p, v) for p, v, ovc in cands if ovc != last)
            order.extend((p, v) for p, v, ovc in cands if ovc == last)

        seen = set(order)
        for in_port in sorted(ALL_PORTS):
            for vc in (VC0, VC1):
                if (in_port, vc) not in seen and self.in_buffers[(in_port, vc)]:
                    order.append((in_port, vc))
        return order

    def evaluate_cycle(self) -> None:
        """Phase 1: Evaluate inputs, arbitrate output ports, and stage outgoing flits.

        Arbitration contract (normative; the SpinalHDL OraRouter implements
        the same rules):
          - Every decision uses start-of-cycle state: buffer heads, locks
            held at cycle start, and downstream occupancy (credits).
          - Each output port, including PORT_LOCAL (ejection), grants at
            most one flit per cycle.
          - Per-port round-robin between VC classes (by requested out_vc):
            the class that last won a port yields on that port. The pointer
            moves only when that port grants a flit.
          - Within a class, lower (in_port, in_vc) wins.
          - A lock released by a Tail this cycle is re-grantable next cycle.
          - A lone header that ejected locally keeps its (LOCAL, vc) lock
            until the channel's next header arrives; that cycle only releases
            the lock, and the new header is processed in the following cycle.
          - Chained-header drops consume no port and happen unconditionally.
        """
        self.staged_tx.clear()
        link_used: dict[int, bool] = {p: False for p in ALL_PORTS}
        self._locks_at_start = frozenset(self.crossbar_locks)

        for in_port, vc in self._arbitration_order():
            buf = self.in_buffers[(in_port, vc)]
            if not buf:
                continue
            active_lock = self.channel_locks[(in_port, vc)]
            flit = buf[0]
            flit_type = (flit >> 30) & 0b11

            if active_lock is not None:
                if flit_type == FLIT_TYPE_HEADER and active_lock.out_port == PORT_LOCAL:
                    # Self-release of a lone ejected header; no grant this cycle
                    self._release_lock(active_lock)
                    continue

                # ACTIVE: stream the next flit through the locked path
                out_port = active_lock.out_port
                out_vc = active_lock.out_vc
                if link_used[out_port]:
                    continue  # Port already granted to another channel this cycle

                rewritten = (flit & ~(0b11 << 28)) | (out_vc << 28)
                if out_port == PORT_LOCAL:
                    self._pop(in_port, vc)
                    self.ejection_queue.append(rewritten)
                    self.ejected_flits += 1
                else:
                    neighbor, nbr_port = self.outgoing_links[out_port]
                    if not neighbor.can_receive(nbr_port, out_vc):
                        continue  # Downstream buffer full (backpressure)
                    self._pop(in_port, vc)
                    self.staged_tx[out_port] = (neighbor, nbr_port, rewritten)
                    self.forwarded_flits += 1

                link_used[out_port] = True
                self._rr_last_served[out_port] = out_vc
                if flit_type == FLIT_TYPE_TAIL:
                    self._release_lock(active_lock)

            else:
                # IDLE: expects Header or Single-AER
                if flit_type == FLIT_TYPE_HEADER:
                    self._stage_header(in_port, vc, link_used)
                elif flit_type == FLIT_TYPE_SINGLE_AER:
                    self._stage_aer(in_port, link_used)
                else:
                    raise RouterError(
                        f"Router {self.tile_id}: unexpected flit type {flit_type:02b} on IDLE channel"
                    )

    def _stage_header(self, in_port: int, vc: int, link_used: dict[int, bool]) -> None:
        word = self.in_buffers[(in_port, vc)][0]
        decision = router_step(word)

        if decision.action == "chain":
            # Chained Header: drop the spent header; the successor header is
            # evaluated at this router from the next cycle on.
            self._pop(in_port, vc)
            self.chained_headers_dropped += 1
            return

        if decision.action == "eject":
            out_port, out_vc, out_word = PORT_LOCAL, decision.vc_id, word
        else:
            assert decision.out_port is not None and decision.word is not None
            out_port, out_vc, out_word = decision.out_port, decision.vc_id, decision.word

        if not self._lock_free((out_port, out_vc)):
            return  # This (port, VC) path is occupied by another wormhole
        if link_used[out_port]:
            return  # Port already granted this cycle

        if out_port == PORT_LOCAL:
            self._pop(in_port, vc)
            self.ejection_queue.append(out_word)
            self.ejected_flits += 1
        else:
            if out_port not in self.outgoing_links:
                raise RouterError(f"Router {self.tile_id}: no link attached to port {out_port}")
            neighbor, nbr_port = self.outgoing_links[out_port]
            if not neighbor.can_receive(nbr_port, out_vc):
                return  # Downstream buffer full
            self._pop(in_port, vc)
            self.staged_tx[out_port] = (neighbor, nbr_port, out_word)
            self.forwarded_flits += 1

        if out_vc == VC1 and vc == VC0:
            self.promotions_executed += 1

        lock = CrossbarLock(in_port, vc, out_port, out_vc)
        self.crossbar_locks[(out_port, out_vc)] = lock
        self.channel_locks[(in_port, vc)] = lock
        link_used[out_port] = True
        self._rr_last_served[out_port] = out_vc

    def _stage_aer(self, in_port: int, link_used: dict[int, bool]) -> None:
        word = self.in_buffers[(in_port, VC0)][0]
        hop_count = (word >> 26) & 0b11
        neuron_addr = word & 0xFFFFF

        if hop_count == 0:
            out_port, out_word = PORT_LOCAL, word
        else:
            out_port = (word >> 20) & 0b111
            second_hop = (word >> 23) & 0b111
            out_word = (
                (FLIT_TYPE_SINGLE_AER << 30)
                | (VC0 << 28)
                | ((hop_count - 1) << 26)
                | (second_hop << 20)
                | neuron_addr
            )

        # AER shares the VC0 class: it must not interleave into a VC0 wormhole
        if not self._lock_free((out_port, VC0)):
            return
        if link_used[out_port]:
            return

        if out_port == PORT_LOCAL:
            self._pop(in_port, VC0)
            self.ejection_queue.append(out_word)
            self.ejected_flits += 1
        else:
            if out_port not in self.outgoing_links:
                raise RouterError(f"Router {self.tile_id}: no link attached for AER port {out_port}")
            neighbor, nbr_port = self.outgoing_links[out_port]
            if not neighbor.can_receive(nbr_port, VC0):
                return
            self._pop(in_port, VC0)
            self.staged_tx[out_port] = (neighbor, nbr_port, out_word)
            self.forwarded_flits += 1

        link_used[out_port] = True
        self._rr_last_served[out_port] = VC0

    def commit_cycle(self) -> int:
        """Phase 2: Commit all staged flits to downstream input buffers."""
        committed = 0
        for _, (neighbor, nbr_port, flit) in self.staged_tx.items():
            if not neighbor.receive_flit(nbr_port, flit):
                raise RouterError(
                    f"Router {self.tile_id}: downstream neighbor {neighbor.tile_id} buffer overflow on port {nbr_port}"
                )
            committed += 1
        self.staged_tx.clear()
        for key in self._pops:
            self._pops[key] = 0
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
        # One reassembly buffer per VC: the single ejection port may
        # interleave a VC0 and a VC1 wormhole flit by flit. Ejected stream
        # flits carry their lock's VC in bits [29:28].
        self._current_rx_flits: dict[int, list[int]] = {VC0: [], VC1: []}

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
            vc = (flit >> 28) & 0b11
            if flit_type == FLIT_TYPE_HEADER:
                self._current_rx_flits[vc] = [flit]
            elif flit_type == FLIT_TYPE_BODY:
                self._current_rx_flits[vc].append(flit)
            elif flit_type == FLIT_TYPE_TAIL:
                self._current_rx_flits[vc].append(flit)
                self._assemble_rx_packet(vc)
            elif flit_type == FLIT_TYPE_SINGLE_AER:
                neuron_addr = flit & 0xFFFFF
                aer_pkt = Packet(
                    src_tile=-1, dst_tile=self.tile_id, headers=[flit], payload=[neuron_addr]
                )
                self.rx_packets.append(aer_pkt)

    def _assemble_rx_packet(self, vc: int) -> None:
        headers = []
        payload = []
        for f in self._current_rx_flits[vc]:
            ftype = (f >> 30) & 0b11
            if ftype == FLIT_TYPE_HEADER:
                headers.append(f)
            else:
                payload.append(f & 0xFFFFFFF)
        pkt = Packet(src_tile=-1, dst_tile=self.tile_id, headers=headers, payload=payload)
        self.rx_packets.append(pkt)
        self._current_rx_flits[vc] = []
