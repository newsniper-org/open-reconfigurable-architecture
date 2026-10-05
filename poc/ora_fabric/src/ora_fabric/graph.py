"""ORA Fabric Graph - Instantiates an executable graph from an OraBitstream.

Module M1 of the ORA PoC architecture:
  - Takes decoded OraBitstream IR
  - Instantiates GleNode, ElasticFifo, and ElasticChannel connections
  - Eager Fork semantics with settled branch-fire detection and per-branch ACK tracking
  - Bounded settle-then-commit cycle engine with combinational loop detection
  - Physical router grid topology with bidirectional link fault injection and route verification
  - Dynamic slack FIFO insertion for H3 elasticity validation
"""

from __future__ import annotations

import math
from collections import defaultdict, deque
from dataclasses import dataclass, field

from ora_bitstream import (
    OraBitstream,
    RouteRecord,
    VRB_GLE4,
    VRB_GLE6,
    VRB_PEU,
    VRB_FLAG_PEU_OUT,
    PORT_LOCAL,
    PORT_NORTH,
    PORT_EAST,
    PORT_SOUTH,
    PORT_WEST,
    trace_route,
)
from ora_fabric.topology import PhysicalTopology
from ora_fabric.elastic import (
    Token,
    ElasticChannel,
    ElasticFifo,
    GleNode,
)


class FabricError(ValueError):
    """Raised on graph instantiation, combinational loop, or netlist structural violations."""


@dataclass(eq=False)
class ChannelConnection:
    """Represents a connection between VRB output and VRB input, with optional slack FIFO."""

    src_vrb_id: int
    dst_vrb_id: int
    src_port: int
    dst_port: int
    delay_budget: int
    channel: ElasticChannel = field(default_factory=ElasticChannel)
    fifo: ElasticFifo | None = None  # Inserted slack buffer if any
    acked: bool = False  # Per-branch acknowledgment for eager fork


class FabricGraph:
    """An executable ORA fabric graph instantiated from an OraBitstream."""

    def __init__(self, bitstream: OraBitstream, topology: PhysicalTopology | None = None):
        self.bitstream = bitstream
        dim = max(1, math.ceil(math.sqrt(bitstream.manifest.router_count)))
        self.topology = topology if topology is not None else PhysicalTopology.mesh(dim, dim)

        self.vrb_nodes: dict[int, GleNode | ElasticFifo] = {}
        self.connections: list[ChannelConnection] = []
        self.outgoing_conns: dict[int, list[ChannelConnection]] = defaultdict(list)

        self._build_nodes()
        self._build_connections()
        self._detect_combinational_loops()
        self._tie_unconnected_inputs()

    def _build_nodes(self) -> None:
        for idx, rec in enumerate(self.bitstream.vrb_records):
            if rec.record_type in (VRB_GLE4, VRB_GLE6):
                has_reg = bool(rec.flags & VRB_FLAG_PEU_OUT)
                node = GleNode(
                    node_id=idx,
                    lut_width=rec.lut_width,
                    lut_init=rec.lut_init,
                    has_peu_reg=has_reg,
                    name=f"GLE_{idx}",
                )
                self.vrb_nodes[idx] = node
            elif rec.record_type == VRB_PEU:
                fifo = ElasticFifo(capacity=1, name=f"PEU_{idx}")
                self.vrb_nodes[idx] = fifo
            else:
                raise FabricError(f"Unsupported record_type 0x{rec.record_type:02x}")

    def _build_connections(self) -> None:
        driven_inputs: set[tuple[int, int]] = set()

        for edge_idx, edge in enumerate(self.bitstream.edges):
            if edge.src_vrb_id not in self.vrb_nodes:
                raise FabricError(f"Edge {edge_idx}: src_vrb_id {edge.src_vrb_id} not found")
            if edge.dst_vrb_id not in self.vrb_nodes:
                raise FabricError(f"Edge {edge_idx}: dst_vrb_id {edge.dst_vrb_id} not found")

            inp_key = (edge.dst_vrb_id, edge.dst_port)
            if inp_key in driven_inputs:
                raise FabricError(f"Input {inp_key} driven twice in netlist")
            driven_inputs.add(inp_key)

            conn = ChannelConnection(
                src_vrb_id=edge.src_vrb_id,
                dst_vrb_id=edge.dst_vrb_id,
                src_port=edge.src_port,
                dst_port=edge.dst_port,
                delay_budget=edge.delay_budget,
            )
            self.connections.append(conn)
            self.outgoing_conns[edge.src_vrb_id].append(conn)

    def _detect_combinational_loops(self) -> None:
        """Detect combinational feedback cycles with no registers or FIFOs."""
        # Build combinational adjacency graph
        comb_adj: dict[int, list[int]] = defaultdict(list)
        for conn in self.connections:
            src_node = self.vrb_nodes[conn.src_vrb_id]
            # If source is a combinational GLE (no PEU register) and connection has no FIFO
            is_comb_src = isinstance(src_node, GleNode) and not src_node.has_peu_reg
            if is_comb_src and conn.fifo is None:
                comb_adj[conn.src_vrb_id].append(conn.dst_vrb_id)

        # Cycle detection via DFS
        visited: set[int] = set()
        rec_stack: set[int] = set()

        def dfs(u: int) -> bool:
            visited.add(u)
            rec_stack.add(u)
            for v in comb_adj.get(u, []):
                if v not in visited:
                    if dfs(v):
                        return True
                elif v in rec_stack:
                    return True
            rec_stack.remove(u)
            return False

        for node_id in self.vrb_nodes:
            if node_id not in visited:
                if dfs(node_id):
                    raise FabricError("Combinational handshake loop detected")
    def _tie_unconnected_inputs(self) -> None:
        """Tie unconnected inputs on active GLE nodes to ground (Token(0), valid=True).

        If a GLE has ZERO driven inputs in the netlist, it is left inactive (all in_valid=False)
        so it does not become an unintended unbounded token generator.
        """
        driven_ports: dict[int, set[int]] = defaultdict(set)
        for conn in self.connections:
            driven_ports[conn.dst_vrb_id].add(conn.dst_port)

        for node_id, node in self.vrb_nodes.items():
            if isinstance(node, GleNode):
                num_driven = len(driven_ports[node_id])
                if num_driven > 0:
                    # At least one real input feeds this node: tie unused sibling ports to ground
                    for p in range(node.lut_width):
                        if p not in driven_ports[node_id]:
                            node.in_valid[p] = True
                            node.in_tokens[p] = Token(data=0)

    def insert_slack(self, conn_idx: int, capacity: int) -> None:
        """Insert an Elastic FIFO of the given capacity into connection conn_idx."""
        if not 0 <= conn_idx < len(self.connections):
            raise FabricError(f"Connection index {conn_idx} out of range")
        conn = self.connections[conn_idx]
        if capacity <= 0:
            conn.fifo = None
        else:
            conn.fifo = ElasticFifo(capacity=capacity, name=f"SlackFIFO_{conn_idx}")

    def inject_link_fault(self, r1: int, r2: int) -> None:
        """Inject a bidirectional physical link fault between router r1 and router r2."""
        self.topology.remove_link(r1, r2)

    def is_connected(self, src: int, dst: int) -> bool:
        """Check if a physical path exists between router src and dst over live links."""
        return self.topology.is_connected(src, dst)

    def verify_route(self, route: RouteRecord) -> bool:
        """Verify that a compiled source route successfully traverses live physical links to dst."""
        return self.topology.verify_route(route)



    def settle(self, max_iterations: int | None = None) -> None:
        """Propagate signals until fixed point or raise FabricError on combinational cycle."""
        if max_iterations is None:
            max_iterations = len(self.vrb_nodes) + len(self.connections) + 2

        for _ in range(max_iterations):
            c1 = self._settle_forward()
            c2 = self._settle_backward()
            if not (c1 or c2):
                return
        raise FabricError("Combinational handshake loop did not converge")

    def _settle_forward(self) -> bool:
        changed = False
        for src_id, conns in self.outgoing_conns.items():
            src_node = self.vrb_nodes[src_id]
            val, tok = src_node.out_valid, src_node.out_token
            for conn in conns:
                branch_val = val and (not conn.acked)
                if conn.fifo is not None:
                    if conn.fifo.in_valid != branch_val or conn.fifo.in_token != tok:
                        conn.fifo.in_valid, conn.fifo.in_token = branch_val, tok
                        changed = True
                else:
                    if conn.channel.valid != branch_val or conn.channel.token != tok:
                        conn.channel.valid, conn.channel.token = branch_val, tok
                        changed = True
        for conn in self.connections:
            val = conn.fifo.out_valid if conn.fifo is not None else conn.channel.valid
            tok = conn.fifo.out_token if conn.fifo is not None else conn.channel.token
            dst = self.vrb_nodes[conn.dst_vrb_id]
            if isinstance(dst, GleNode):
                if dst.in_valid[conn.dst_port] != val or dst.in_tokens[conn.dst_port] != tok:
                    dst.in_valid[conn.dst_port], dst.in_tokens[conn.dst_port] = val, tok
                    changed = True
            elif isinstance(dst, ElasticFifo):
                if dst.in_valid != val or dst.in_token != tok:
                    dst.in_valid, dst.in_token = val, tok
                    changed = True

        for node in self.vrb_nodes.values():
            node.evaluate()
        return changed

    def _settle_backward(self) -> bool:
        changed = False
        for conn in self.connections:
            dst = self.vrb_nodes[conn.dst_vrb_id]
            r = dst.in_ready[conn.dst_port] if isinstance(dst, GleNode) else (dst.in_ready if isinstance(dst, ElasticFifo) else False)
            if conn.fifo is not None:
                if conn.fifo.out_ready != r:
                    conn.fifo.out_ready = r
                    conn.fifo.evaluate_ready()
                    changed = True
            else:
                if conn.channel.ready != r:
                    conn.channel.ready = r
                    changed = True

        for src_id, conns in self.outgoing_conns.items():
            all_ready = all(
                (c.acked or (c.fifo.in_ready if c.fifo is not None else c.channel.ready))
                for c in conns
            )
            src_node = self.vrb_nodes[src_id]
            if src_node.out_ready != all_ready:
                src_node.out_ready = all_ready
                src_node.evaluate()
                changed = True
        return changed

    def step(self) -> int:
        """Execute one simulation cycle with precise commit ordering."""
        self.settle()
        branch_fired = self._record_branch_fires()
        fired_count = self._step_all_components()
        self._apply_branch_acks(branch_fired)
        self.settle()
        return fired_count

    def _record_branch_fires(self) -> dict[ChannelConnection, bool]:
        res = {}
        for conn in self.connections:
            if conn.fifo is not None:
                res[conn] = conn.fifo.in_valid and conn.fifo.in_ready
            else:
                res[conn] = conn.channel.valid and conn.channel.ready
        return res

    def _step_all_components(self) -> int:
        fired = 0
        for conn in self.connections:
            if conn.fifo is not None:
                inf, outf = conn.fifo.step()
                if inf or outf:
                    fired += 1
        for node in self.vrb_nodes.values():
            if isinstance(node, GleNode):
                if node.step():
                    fired += 1
            elif isinstance(node, ElasticFifo):
                inf, outf = node.step()
                if inf or outf:
                    fired += 1
        return fired

    def _apply_branch_acks(self, branch_fired: dict[ChannelConnection, bool]) -> None:
        for conns in self.outgoing_conns.values():
            for conn in conns:
                if branch_fired.get(conn, False):
                    conn.acked = True
            if all(c.acked for c in conns):
                for c in conns:
                    c.acked = False
