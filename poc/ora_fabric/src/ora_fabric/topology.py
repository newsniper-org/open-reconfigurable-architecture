"""Physical NoC Topology module for ORA-N.

Models actual physical links between routers:
  - (router_id, port) <-> (neighbor_router_id, opposite_port)
  - Factory for 2D mesh grids: PhysicalTopology.mesh(w, h)
  - Support for arbitrary irregular, 3D chiplet, and fault-injected topologies
  - Route traversal verification using physical links and trace_route
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field

from ora_bitstream import (
    PORT_LOCAL,
    PORT_NORTH,
    PORT_EAST,
    PORT_SOUTH,
    PORT_WEST,
    PORT_UP,
    PORT_DOWN,
    RouteRecord,
    trace_route,
)

OPPOSITE_PORTS = {
    PORT_NORTH: PORT_SOUTH,
    PORT_SOUTH: PORT_NORTH,
    PORT_EAST: PORT_WEST,
    PORT_WEST: PORT_EAST,
    PORT_UP: PORT_DOWN,
    PORT_DOWN: PORT_UP,
}


class TopologyError(ValueError):
    """Raised on invalid topology definitions or port mismatch."""


@dataclass
class PhysicalTopology:
    """Explicit physical link topology for an ORA-N router network."""

    # (r_id, port) -> (neighbor_id, neighbor_port)
    links: dict[tuple[int, int], tuple[int, int]] = field(default_factory=dict)
    num_routers: int = 0

    def add_bidirectional_link(self, r1: int, p1: int, r2: int, p2: int) -> None:
        """Add a bidirectional physical link between (r1, p1) and (r2, p2)."""
        if p1 == PORT_LOCAL or p2 == PORT_LOCAL:
            raise TopologyError("PORT_LOCAL cannot be used for inter-router links")
        if OPPOSITE_PORTS.get(p1) != p2:
            raise TopologyError(f"Port {p1} and port {p2} are not complementary opposite ports")

        self.links[(r1, p1)] = (r2, p2)
        self.links[(r2, p2)] = (r1, p1)
        self.num_routers = max(self.num_routers, r1 + 1, r2 + 1)

    def remove_link(self, r1: int, r2: int) -> None:
        """Sever the physical link between r1 and r2 in both directions."""
        to_del = []
        for (src, p), (dst, _) in self.links.items():
            if (src == r1 and dst == r2) or (src == r2 and dst == r1):
                to_del.append((src, p))
        for key in to_del:
            del self.links[key]

    def has_link(self, r1: int, p: int) -> bool:
        return (r1, p) in self.links

    def get_neighbor(self, r1: int, p: int) -> tuple[int, int] | None:
        return self.links.get((r1, p))

    def is_connected(self, src: int, dst: int) -> bool:
        """Check reachability from src to dst over live physical links."""
        if src == dst:
            return True
        visited = set()
        queue = deque([src])
        while queue:
            curr = queue.popleft()
            if curr == dst:
                return True
            for (r, _), (nbr, _) in self.links.items():
                if r == curr and nbr not in visited:
                    visited.add(nbr)
                    queue.append(nbr)
        return False

    def verify_route(self, route: RouteRecord) -> bool:
        """Verify that a compiled source route can traverse live physical links to dst."""
        hops = trace_route(route.headers)
        curr = route.src_tile
        for port, _ in hops:
            if port == PORT_LOCAL:
                break
            link = self.get_neighbor(curr, port)
            if link is None:
                return False  # Dead or non-existent physical link!
            nbr, _ = link
            curr = nbr
        return curr == route.dst_tile

    @classmethod
    def mesh(cls, width: int, height: int) -> PhysicalTopology:
        """Construct a regular 2D mesh topology of width x height routers."""
        topo = cls(num_routers=width * height)
        for y in range(height):
            for x in range(width):
                r = y * width + x
                # East link (+X)
                if x + 1 < width:
                    nbr_east = y * width + (x + 1)
                    topo.add_bidirectional_link(r, PORT_EAST, nbr_east, PORT_WEST)
                # North link (+Y)
                if y + 1 < height:
                    nbr_north = (y + 1) * width + x
                    topo.add_bidirectional_link(r, PORT_NORTH, nbr_north, PORT_SOUTH)
        return topo

    @classmethod
    def from_links(cls, num_routers: int, link_list: list[tuple[int, int, int, int]]) -> PhysicalTopology:
        """Construct topology from an explicit list of (r1, p1, r2, p2) links."""
        topo = cls(num_routers=num_routers)
        for r1, p1, r2, p2 in link_list:
            topo.add_bidirectional_link(r1, p1, r2, p2)
        return topo
