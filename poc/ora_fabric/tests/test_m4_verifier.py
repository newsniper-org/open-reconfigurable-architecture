"""M4 verifier tests: CDG static deadlock check (H2 primary) and H1 fuzz round-trip."""

import pytest
from ora_bitstream import VC0
from ora_fabric.topology import PhysicalTopology
from ora_fabric.routing import UpDownRouteCompiler
from ora_fabric.cdg import ChannelDependencyGraph, CdgError
from ora_fabric.fuzz import fuzz_roundtrip


class TestCdgStaticCheck:
    def test_mesh_4x4_full_route_set_acyclic(self):
        """H2 primary proof: the full compiled route set of a 4x4 mesh
        yields an acyclic channel dependency graph."""
        topo = PhysicalTopology.mesh(4, 4)
        routes = UpDownRouteCompiler(topo, root=0).compile_all()
        assert len(routes) == 16 * 15  # every ordered pair

        cdg = ChannelDependencyGraph(topo, routes)
        assert cdg.is_acyclic() is True
        cdg.check()  # must not raise

    @pytest.mark.parametrize("root", [0, 5, 15])
    def test_mesh_different_roots_acyclic(self, root: int):
        """Deadlock freedom must hold regardless of the spanning-tree root."""
        topo = PhysicalTopology.mesh(4, 4)
        routes = UpDownRouteCompiler(topo, root=root).compile_all()
        cdg = ChannelDependencyGraph(topo, routes)
        assert cdg.is_acyclic() is True

    def test_fault_injected_topology_recompiled_acyclic(self):
        """Fault -> connectivity check -> recompile -> CDG stays acyclic."""
        topo = PhysicalTopology.mesh(4, 4)
        topo.remove_link(5, 6)
        topo.remove_link(1, 5)

        # Connectivity check (both pairs still connected in a 4x4 mesh)
        assert topo.is_connected(0, 15) is True

        routes = UpDownRouteCompiler(topo, root=0).compile_all()
        cdg = ChannelDependencyGraph(topo, routes)
        assert cdg.is_acyclic() is True
        cdg.check()

    def test_irregular_topology_acyclic(self):
        """Topology independence: an irregular (non-mesh) graph with a hub."""
        topo = PhysicalTopology.from_links(7, [
            (0, 2, 1, 4),  # 0 <-> 1 (East/West)
            (1, 2, 2, 4),  # 1 <-> 2
            (2, 2, 3, 4),  # 2 <-> 3
            (3, 2, 4, 4),  # 3 <-> 4
            (4, 2, 5, 4),  # 4 <-> 5
            (5, 2, 6, 4),  # 5 <-> 6
        ])
        routes = UpDownRouteCompiler(topo, root=3).compile_all()
        cdg = ChannelDependencyGraph(topo, routes)
        assert cdg.is_acyclic() is True

    def test_cyclic_cdg_detected(self):
        """Negative control: a deliberately cyclic route set must be detected."""
        topo = PhysicalTopology.from_links(4, [
            (0, 2, 1, 4),
            (1, 2, 2, 4),
            (2, 2, 3, 4),
            (3, 2, 0, 4),  # ring 0-1-2-3-0
        ])
        # Hand-craft routes forming a dependency cycle on VC0:
        # 0->1, 1->2, 2->3, 3->0 each uses the ring link; consecutive dependency
        # alone is not cyclic per route, but wrap-around usage in a full
        # permutation creates the ring: (0->1)->(1->2)->(2->3)->(3->0).
        from ora_bitstream import RouteRecord, pack_header_flit, NO_VC_TRANSITION, PORT_EAST
        routes = [
            RouteRecord(0, 1, [pack_header_flit(vc_id=VC0, hop_count=1, chained=False,
                                               vc_transition_hop=NO_VC_TRANSITION,
                                               direction_vector=[PORT_EAST])]),
            RouteRecord(1, 2, [pack_header_flit(vc_id=VC0, hop_count=1, chained=False,
                                               vc_transition_hop=NO_VC_TRANSITION,
                                               direction_vector=[PORT_EAST])]),
            RouteRecord(2, 3, [pack_header_flit(vc_id=VC0, hop_count=1, chained=False,
                                               vc_transition_hop=NO_VC_TRANSITION,
                                               direction_vector=[PORT_EAST])]),
            RouteRecord(3, 0, [pack_header_flit(vc_id=VC0, hop_count=1, chained=False,
                                               vc_transition_hop=NO_VC_TRANSITION,
                                               direction_vector=[PORT_EAST])]),
        ]
        # Each single-hop route alone does not create edges; add a route that
        # traverses the full ring to create the dependency chain.
        routes.append(RouteRecord(0, 2, [pack_header_flit(
            vc_id=VC0, hop_count=2, chained=False, vc_transition_hop=NO_VC_TRANSITION,
            direction_vector=[PORT_EAST, PORT_EAST])]))
        routes.append(RouteRecord(1, 3, [pack_header_flit(
            vc_id=VC0, hop_count=2, chained=False, vc_transition_hop=NO_VC_TRANSITION,
            direction_vector=[PORT_EAST, PORT_EAST])]))
        routes.append(RouteRecord(2, 0, [pack_header_flit(
            vc_id=VC0, hop_count=2, chained=False, vc_transition_hop=NO_VC_TRANSITION,
            direction_vector=[PORT_EAST, PORT_EAST])]))
        routes.append(RouteRecord(3, 1, [pack_header_flit(
            vc_id=VC0, hop_count=2, chained=False, vc_transition_hop=NO_VC_TRANSITION,
            direction_vector=[PORT_EAST, PORT_EAST])]))

        cdg = ChannelDependencyGraph(topo, routes)
        assert cdg.is_acyclic() is False
        with pytest.raises(CdgError):
            cdg.check()


class TestH1FuzzRoundTrip:
    def test_fuzz_2000_samples(self):
        """H1: 2,000 random bitstreams round-trip with zero loss."""
        passed, failed = fuzz_roundtrip(n_samples=2000, seed=20261005)
        assert failed == 0
        assert passed == 2000
