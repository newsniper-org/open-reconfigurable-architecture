"""H2 integration test: fault -> recompile -> CDG static check -> packet simulation.

The full H2 pipeline on a 4x4 mesh:
  1. Build a physical 4x4 mesh with injected link faults.
  2. Verify connectivity survives the faults.
  3. Recompute the Up*/Down* spanning tree and recompile all routes.
  4. Static CDG check: the channel dependency graph over the recompiled route
     set must be acyclic (primary H2 proof).
  5. Instantiate table-less routers wired per the physical topology, inject
     packets from every source NI, and run the cycle-accurate network to
     quiescence (secondary confirmation: zero deadlock, full delivery).
"""
from ora_fabric.topology import PhysicalTopology
from ora_fabric.routing import UpDownRouteCompiler
from ora_fabric.cdg import ChannelDependencyGraph
from ora_fabric.router import NoCRouter, NoCNetwork, NetworkInterface, Packet


def build_network(topo: PhysicalTopology) -> tuple[NoCNetwork, list[NetworkInterface]]:
    """Wire table-less routers according to the physical topology."""
    routers = [NoCRouter(tile_id=i) for i in range(topo.num_routers)]
    for (src, sport), (dst, dport) in topo.links.items():
        routers[src].connect(sport, routers[dst], dport)
    net = NoCNetwork(routers=routers, topology=topo)
    nis = [NetworkInterface(tile_id=i, router=routers[i]) for i in range(topo.num_routers)]
    return net, nis


class TestH2FullPipeline:
    def test_mesh4x4_faults_recompile_cdg_and_simulation(self):
        # 1. Physical 4x4 mesh with two severed links
        topo = PhysicalTopology.mesh(4, 4)
        topo.remove_link(5, 6)
        topo.remove_link(1, 5)

        # 2. Connectivity check
        assert topo.is_connected(0, 15) is True

        # 3. Recompile routes after fault injection
        routes = UpDownRouteCompiler(topo, root=0).compile_all()
        assert len(routes) == 16 * 15
        for r in routes:
            assert topo.verify_route(r) is True, (
                f"route {r.src_tile}->{r.dst_tile} crosses a dead link"
            )

        # 4. Primary H2 proof: static CDG acyclicity
        cdg = ChannelDependencyGraph(topo, routes)
        assert cdg.is_acyclic() is True
        cdg.check()  # must not raise

        # 5. Secondary confirmation: cycle-accurate simulation with delivery
        net, nis = build_network(topo)
        route_map = {(r.src_tile, r.dst_tile): r for r in routes}

        # Inject one packet from every source to a far destination
        sent = 0
        for src in range(16):
            dst = (src + 7) % 16
            if src == dst:
                continue
            route = route_map[(src, dst)]
            pkt = Packet(src_tile=src, dst_tile=dst,
                        headers=list(route.headers), payload=[src * 1000 + dst])
            nis[src].send_packet(pkt)
            sent += 1

        # Run to quiescence (bounded)
        for _ in range(200):
            for ni in nis:
                ni.step()
            net.step()
            delivered = sum(len(ni.rx_packets) for ni in nis)
            if delivered == sent:
                break

        delivered = sum(len(ni.rx_packets) for ni in nis)
        assert delivered == sent, f"delivered {delivered} of {sent}: stalled (deadlock?)"

        # Payload integrity: each NI received exactly its own packets
        total_checked = 0
        for src in range(16):
            dst = (src + 7) % 16
            if src == dst:
                continue
            expected = src * 1000 + dst
            got = [p for p in nis[dst].rx_packets if expected in p.payload]
            assert got, f"packet {src}->{dst} (payload {expected}) missing at NI {dst}"
            total_checked += 1
        assert total_checked == sent

    def test_hotspot_traffic_no_deadlock(self):
        """Hotspot: every router sends to router 0 simultaneously."""
        topo = PhysicalTopology.mesh(4, 4)
        routes = UpDownRouteCompiler(topo, root=0).compile_all()
        cdg = ChannelDependencyGraph(topo, routes)
        assert cdg.is_acyclic() is True

        net, nis = build_network(topo)
        route_map = {(r.src_tile, r.dst_tile): r for r in routes}

        sent = 0
        for src in range(1, 16):
            route = route_map[(src, 0)]
            pkt = Packet(src_tile=src, dst_tile=0,
                         headers=list(route.headers), payload=[src])
            nis[src].send_packet(pkt)
            sent += 1

        for _ in range(300):
            for ni in nis:
                ni.step()
            net.step()
            if sum(len(ni.rx_packets) for ni in nis) == sent:
                break

        delivered = sum(len(ni.rx_packets) for ni in nis)
        assert delivered == sent, f"hotspot deadlock: delivered {delivered} of {sent}"
        got_sources = sorted(p.payload[0] for p in nis[0].rx_packets)
        assert got_sources == list(range(1, 16))
