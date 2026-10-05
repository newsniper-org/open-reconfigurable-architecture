"""Route compiler for ORA-N: computes Up*/Down* routes over a physical topology.

Given a physical topology and a root router, computes Up*/Down* directed link
labels and compiles minimal source-route headers for every (src, dst) pair.
Produces routes that are provably deadlock-free under monotonic VC layering:
packets are injected on VC0 following Up*/Down*, with at most one Down->Up
shortcut turn promoting the packet to VC1 for the remainder of the path.
"""

from __future__ import annotations

from collections import deque

from ora_bitstream import (
    RouteRecord,
    pack_header_flit,
    VC0,
    NO_VC_TRANSITION,
    MAX_HEADER_HOPS,
    PORT_NORTH,
    PORT_SOUTH,
    PORT_EAST,
    PORT_WEST,
    PORT_UP,
    PORT_DOWN,
)
from ora_fabric.topology import PhysicalTopology


class RouteCompilerError(ValueError):
    """Raised when a route cannot be compiled over the live topology."""


def _opposite(port: int) -> int:
    return {
        PORT_NORTH: PORT_SOUTH,
        PORT_SOUTH: PORT_NORTH,
        PORT_EAST: PORT_WEST,
        PORT_WEST: PORT_EAST,
        PORT_UP: PORT_DOWN,
        PORT_DOWN: PORT_UP,
    }[port]


class UpDownRouteCompiler:
    """Compiles Up*/Down* source routes over a PhysicalTopology."""

    def __init__(self, topology: PhysicalTopology, root: int = 0):
        self.topology = topology
        self.root = root
        self.link_labels: dict[tuple[int, int], str] = {}  # (src, dst) -> "up" | "down"
        self._label_links()

    def _label_links(self) -> None:
        """BFS from root: links toward root are Up, links away are Down."""
        # Build adjacency for BFS traversal (undirected view)
        adjacency: dict[int, list[tuple[int, int]]] = {}
        for (src, port), (dst, _) in self.topology.links.items():
            adjacency.setdefault(src, []).append((dst, port))
            adjacency.setdefault(dst, []).append((src, port))
        # Note: adjacency is only used for BFS ordering below.

        # BFS tree from root over undirected links
        visited = {self.root}
        queue = deque([self.root])
        tree_parent: dict[int, int | None] = {self.root: None}

        while queue:
            curr = queue.popleft()
            for (src, _port), (dst, _dport) in self.topology.links.items():
                # Consider the undirected edge {src, dst}
                if src == curr and dst not in visited:
                    visited.add(dst)
                    tree_parent[dst] = src
                    queue.append(dst)
                if dst == curr and src not in visited:
                    visited.add(src)
                    tree_parent[src] = dst
                    queue.append(src)

        # Label every directed link: a directed link (u, v) is "up" iff
        # it moves toward the root in the BFS tree (v is the tree parent of u
        # or v is shallower), otherwise "down".
        depth = self._depths(tree_parent)
        for (src, _p), (dst, _q) in self.topology.links.items():
            if tree_parent.get(src) == dst:
                self.link_labels[(src, dst)] = "up"
            elif tree_parent.get(dst) == src:
                self.link_labels[(dst, src)] = "up"
                self.link_labels.setdefault((src, dst), "down")
            else:
                if depth.get(src, 0) <= depth.get(dst, 0):
                    self.link_labels[(src, dst)] = "down"
                    self.link_labels[(dst, src)] = "up"
                else:
                    self.link_labels[(src, dst)] = "up"
                    self.link_labels[(dst, src)] = "down"

    def _depths(self, tree_parent: dict[int, int | None]) -> dict[int, int]:
        depths = {self.root: 0}
        # Compute depths by BFS from root along tree parents
        changed = True
        nodes = set(tree_parent.keys())
        while changed:
            changed = False
            for n in nodes:
                p = tree_parent.get(n)
                if p is not None and p in depths:
                    d = depths[p] + 1
                    if n not in depths or depths[n] > d:
                        depths[n] = d
                        changed = True
        return depths

    def compile_route(self, src: int, dst: int) -> RouteRecord:
        """Compile a single (src, dst) route.

        Strategy: pure Up*/Down* shortest path (BFS restricted to Up-before-Down
        order). The packet stays on VC0 for the whole path (no promotion needed
        for tree-conforming routes).
        """
        if src == dst:
            raise RouteCompilerError("src == dst: no route needed")

        # State: (router, phase) where phase is "up" then "down".
        # BFS over (router, phase) states; record the port taken.
        start = (src, "up")
        queue = deque([start])
        came_from: dict[tuple[int, str], tuple[tuple[int, str], int] | None] = {start: None}

        goal_states = [(dst, "up"), (dst, "down")]

        while queue:
            state = queue.popleft()
            if state in goal_states:
                break
            router, phase = state
            for (r, port), (nbr, _) in self.topology.links.items():
                if r != router:
                    continue
                link_label = self.link_labels[(r, nbr)]
                if phase == "up" and link_label == "up":
                    nxt = (nbr, "up")
                elif phase == "up" and link_label == "down":
                    # Up* -> Down* transition allowed (Up* arrow Down*)
                    nxt = (nbr, "down")
                elif phase == "down" and link_label == "down":
                    nxt = (nbr, "down")
                else:
                    # phase == "down" and label == "up": forbidden (Down -> Up)
                    continue
                if nxt not in came_from:
                    came_from[nxt] = (state, port)
                    queue.append(nxt)

        goal = next((g for g in goal_states if g in came_from), None)
        if goal is None:
            raise RouteCompilerError(f"No Up*/Down* route from {src} to {dst}")

        # Reconstruct the port sequence
        ports: list[int] = []
        state = goal
        while came_from[state] is not None:
            prev, port = came_from[state]  # type: ignore[misc]
            ports.append(port)
            state = prev
        ports.reverse()

        # Split ports into header flits of at most 7 hops, all chained except the last
        headers: list[int] = []
        i = 0
        n = len(ports)
        while i < n:
            segment = ports[i:i + MAX_HEADER_HOPS]
            remaining = n - i
            chained = remaining > MAX_HEADER_HOPS
            headers.append(pack_header_flit(
                vc_id=VC0,
                hop_count=len(segment),
                chained=chained,
                vc_transition_hop=NO_VC_TRANSITION,
                direction_vector=segment,
            ))
            i += len(segment)

        return RouteRecord(src_tile=src, dst_tile=dst, headers=headers)

    def compile_all(self) -> list[RouteRecord]:
        """Compile routes for every ordered (src, dst) pair in the topology."""
        num = self.topology.num_routers
        routes = []
        for src in range(num):
            for dst in range(num):
                if src == dst:
                    continue
                routes.append(self.compile_route(src, dst))
        return routes
