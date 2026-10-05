"""Channel Dependency Graph (CDG) static deadlock checker for ORA-N (Module M4).

Primary H2 proof: constructs a CDG over the compiled route set and checks acyclicity.

Node (channel) = (directed physical link, VC). A directed link is the ordered pair
(src_router, dst_router). Edges are taken from the consecutive hops of every compiled
route: if a route occupies channel (L1, vc1) and then channel (L2, vc2), the CDG
gains the edge (L1, vc1) -> (L2, vc2).

Deadlock freedom argument (monotonic VC layering):
  - Within VC0, the Up*/Down* spanning tree makes the VC0 sub-graph acyclic.
  - Within VC1, the same holds for the post-promotion segment.
  - Cross-VC edges only run VC0 -> VC1 (monotonic promotion, never VC1 -> VC0),
    so the layered graph cannot contain a cycle.
"""

from __future__ import annotations

from collections import defaultdict
from ora_bitstream import RouteRecord, trace_route
from ora_fabric.topology import PhysicalTopology


class CdgError(ValueError):
    """Raised when the channel dependency graph contains a cycle."""


class ChannelDependencyGraph:
    """Static CDG built from compiled routes over a physical topology."""

    def __init__(self, topology: PhysicalTopology, routes: list[RouteRecord]):
        self.topology = topology
        self.routes = routes

        # CDG nodes: (directed_link, vc) where directed_link = (src, dst)
        self.nodes: set[tuple[tuple[int, int], int]] = set()
        # CDG edges: node -> set of nodes
        self.edges: dict[tuple[tuple[int, int], int], set[tuple[tuple[int, int], int]]] = defaultdict(set)

        self._build()

    def _resolve_link(self, router: int, port: int) -> tuple[int, int] | None:
        """Return the directed link (src, dst) for leaving `router` via `port`."""
        nbr = self.topology.get_neighbor(router, port)
        if nbr is None:
            return None
        nbr_id = nbr[0]
        return (router, nbr_id)

    def _build(self) -> None:
        for route in self.routes:
            hops = trace_route(route.headers)
            prev_channel: tuple[tuple[int, int], int] | None = None
            curr = route.src_tile

            for port, vc in hops:
                link = self._resolve_link(curr, port)
                if link is None:
                    # Dead link: route is not physically realizable; skip this hop's edge
                    prev_channel = None
                    continue
                channel = (link, vc)
                self.nodes.add(channel)
                if prev_channel is not None and prev_channel != channel:
                    self.edges[prev_channel].add(channel)
                prev_channel = channel
                # Advance the router along the link
                curr = link[1]

    def is_acyclic(self) -> bool:
        """Check acyclicity via iterative DFS with a recursion stack."""
        visited: set[tuple[tuple[int, int], int]] = set()
        on_stack: set[tuple[tuple[int, int], int]] = set()

        for start in self.nodes:
            if start in visited:
                continue
            # Iterative DFS
            stack = [(start, iter(self.edges.get(start, ())))]
            visited.add(start)
            on_stack.add(start)
            while stack:
                node, it = stack[-1]
                advanced = False
                for nxt in it:
                    if nxt in on_stack:
                        return False  # Cycle detected
                    if nxt not in visited:
                        visited.add(nxt)
                        on_stack.add(nxt)
                        stack.append((nxt, iter(self.edges.get(nxt, ()))))
                        advanced = True
                        break
                if not advanced:
                    stack.pop()
                    on_stack.discard(node)
        return True

    def find_cycle(self) -> list[tuple[tuple[int, int], int]] | None:
        """Return one cycle as a list of channels, or None if acyclic."""
        visited: set[tuple[tuple[int, int], int]] = set()
        parent: dict[tuple[tuple[int, int], int], tuple[tuple[int, int], int] | None] = {}

        for start in self.nodes:
            if start in visited:
                continue
            stack = [(start, iter(self.edges.get(start, ())))]
            visited.add(start)
            parent[start] = None
            while stack:
                node, it = stack[-1]
                advanced = False
                for nxt in it:
                    if nxt not in visited:
                        visited.add(nxt)
                        parent[nxt] = node
                        stack.append((nxt, iter(self.edges.get(nxt, ()))))
                        advanced = True
                        break
                if not advanced:
                    stack.pop()
        # Second pass: detect back edges to reconstruct a cycle (BFS-based fallback)
        # Simple cycle detection via strongly connected components (Tarjan-lite)
        index_counter = [0]
        indices: dict[tuple[tuple[int, int], int], int] = {}
        lowlink: dict[tuple[tuple[int, int], int], int] = {}
        on_scc_stack: set[tuple[tuple[int, int], int]] = set()
        scc_stack: list[tuple[tuple[int, int], int]] = []

        def strongconnect(v):
            indices[v] = index_counter[0]
            lowlink[v] = index_counter[0]
            index_counter[0] += 1
            scc_stack.append(v)
            on_scc_stack.add(v)

            for w in self.edges.get(v, ()):
                if w not in indices:
                    strongconnect(w)
                    lowlink[v] = min(lowlink[v], lowlink[w])
                elif w in on_scc_stack:
                    lowlink[v] = min(lowlink[v], indices[w])

            if lowlink[v] == indices[v]:
                # Root of an SCC
                component = []
                while True:
                    w = scc_stack.pop()
                    on_scc_stack.discard(w)
                    component.append(w)
                    if w == v:
                        break
                if len(component) > 1:
                    return component
            return None

        import sys
        sys.setrecursionlimit(10000)
        for v in list(self.nodes):
            if v not in indices:
                cyc = strongconnect(v)
                if cyc:
                    return cyc
        return None

    def check(self) -> None:
        """Raise CdgError naming a cycle if the CDG is cyclic."""
        if not self.is_acyclic():
            cycle = self.find_cycle()
            if cycle:
                pretty = " -> ".join(f"({l[0]}->{l[1]},VC{vc})" for (l, vc) in cycle)
                raise CdgError(f"CDG cycle detected: {pretty} -> (cycle closes)")
            raise CdgError("CDG cycle detected (component not reconstructed)")
