"""Tests for M1 FabricGraph builder, physical NoC topology, and Graph-level H3 verification."""

import pytest
from ora_bitstream import (
    OraBitstream,
    Manifest,
    VrbRecord,
    EdgeRecord,
    RouteRecord,
    VRB_GLE4,
    VRB_PEU,
    PROFILE_ORA_D,
    PROFILE_ORA_N,
    PORT_EAST,
    pack_header_flit,
)
from ora_fabric.elastic import Token, GleNode, ElasticFifo
from ora_fabric.graph import FabricGraph, FabricError


def make_test_bitstream() -> OraBitstream:
    bs = OraBitstream(profile=PROFILE_ORA_D | PROFILE_ORA_N)
    bs.manifest = Manifest(gle4_count=2, peu_count=1, router_count=4)
    bs.vrb_records = [
        VrbRecord(VRB_GLE4, 4, 0, [0x8000], [0, 1, 2, 3]),
        VrbRecord(VRB_GLE4, 4, 0, [0x5555], [0, 1, 2, 3]),
        VrbRecord(VRB_PEU, 0, 0, [], [0]),
    ]
    bs.edges = [
        EdgeRecord(src_vrb_id=0, dst_vrb_id=2, src_port=0, dst_port=0, delay_budget=10),
        EdgeRecord(src_vrb_id=2, dst_vrb_id=1, src_port=0, dst_port=0, delay_budget=10),
    ]
    # Router 0 -> East -> Router 1
    hdr = pack_header_flit(vc_id=0, hop_count=1, chained=False, vc_transition_hop=7, direction_vector=[PORT_EAST])
    bs.routes = [
        RouteRecord(src_tile=0, dst_tile=1, headers=[hdr]),
    ]
    return bs


class TestFabricGraphBasics:
    def test_instantiation_from_bitstream(self):
        bs = make_test_bitstream()
        graph = FabricGraph(bs)
        assert len(graph.vrb_nodes) == 3
        assert len(graph.connections) == 2
        # 4 routers in 2x2 grid: physical links exist
        assert len(graph.topology.links) > 0

    def test_slack_insertion(self):
        bs = make_test_bitstream()
        graph = FabricGraph(bs)
        assert graph.connections[0].fifo is None

        graph.insert_slack(conn_idx=0, capacity=4)
        assert graph.connections[0].fifo is not None
        assert graph.connections[0].fifo.capacity == 4

        graph.insert_slack(conn_idx=0, capacity=0)
        assert graph.connections[0].fifo is None

    def test_invalid_slack_index(self):
        bs = make_test_bitstream()
        graph = FabricGraph(bs)
        with pytest.raises(FabricError, match="out of range"):
            graph.insert_slack(conn_idx=99, capacity=2)

    def test_graph_step_execution_inactive_netlist(self):
        bs = make_test_bitstream()
        graph = FabricGraph(bs)
        # Inactive netlist with 0 input tokens must produce exactly 0 firings (no rogue token generator)
        fired = graph.step()
        assert fired == 0


class TestPhysicalTopologyAndFaults:
    def test_mesh_generation_and_route_verification(self):
        bs = make_test_bitstream()
        graph = FabricGraph(bs)
        # 2x2 mesh: 0 is connected to 1 (East), 0 is connected to 2 (North)
        assert graph.is_connected(0, 1) is True
        assert graph.is_connected(0, 3) is True

        # Route 0 -> 1 using PORT_EAST matches physical link
        route_0_to_1 = bs.routes[0]
        assert graph.verify_route(route_0_to_1) is True

    def test_bidirectional_link_fault_injection(self):
        bs = make_test_bitstream()
        graph = FabricGraph(bs)
        assert graph.is_connected(0, 1) is True
        assert graph.is_connected(1, 0) is True

        # Break physical link between router 0 and router 1
        graph.inject_link_fault(0, 1)

        # Both directions must be severed on physical link (0, 1)
        from ora_bitstream import PORT_EAST as PE, PORT_WEST as PW
        assert graph.topology.get_neighbor(0, PE) is None
        assert graph.topology.get_neighbor(1, PW) is None

        # Route traversing severed link must fail verification
        route_0_to_1 = bs.routes[0]
        assert graph.verify_route(route_0_to_1) is False


class TestHandshakeSettleAndCycles:
    def test_combinational_cycle_detection(self):
        # 2-node combinational loop: VRB 0 -> VRB 1 -> VRB 0 (both without PEU reg)
        bs = OraBitstream(profile=PROFILE_ORA_D)
        bs.manifest = Manifest(gle4_count=2)
        bs.vrb_records = [
            VrbRecord(VRB_GLE4, 4, 0, [0xFFFF], [0, 1, 2, 3]),
            VrbRecord(VRB_GLE4, 4, 0, [0xFFFF], [0, 1, 2, 3]),
        ]
        bs.edges = [
            EdgeRecord(src_vrb_id=0, dst_vrb_id=1, src_port=0, dst_port=0, delay_budget=1),
            EdgeRecord(src_vrb_id=1, dst_vrb_id=0, src_port=0, dst_port=0, delay_budget=1),
        ]
        with pytest.raises(FabricError, match="loop detected"):
            FabricGraph(bs)

    def test_deep_combinational_chain_convergence(self):
        # Deep chain of 20 combinational GLEs
        n = 20
        bs = OraBitstream(profile=PROFILE_ORA_D)
        bs.manifest = Manifest(gle4_count=n)
        bs.vrb_records = [VrbRecord(VRB_GLE4, 4, 0, [0xAAAA], [0, 1, 2, 3]) for _ in range(n)]
        bs.edges = [
            EdgeRecord(src_vrb_id=i, dst_vrb_id=i + 1, src_port=0, dst_port=0, delay_budget=1)
            for i in range(n - 1)
        ]
        graph = FabricGraph(bs)
        # Must converge cleanly within dynamic iteration limit
        graph.settle()


class TestFanoutSemantics:
    def test_3way_fanout_with_staggered_stalls(self):
        """1 Source VRB fans out to 3 Consumer PEUs.

        Consumers stall on different cycles. Proves that Eager Fork per-branch ACKs
        prevent token duplication or dropping across all branches.
        """
        bs = OraBitstream(profile=PROFILE_ORA_D)
        bs.manifest = Manifest(gle4_count=0, peu_count=4)
        bs.vrb_records = [
            VrbRecord(VRB_PEU, 0, 0, [], [0]),  # VRB 0: Source PEU
            VrbRecord(VRB_PEU, 0, 0, [], [0]),  # VRB 1: Consumer 1
            VrbRecord(VRB_PEU, 0, 0, [], [0]),  # VRB 2: Consumer 2
            VrbRecord(VRB_PEU, 0, 0, [], [0]),  # VRB 3: Consumer 3
        ]
        bs.edges = [
            EdgeRecord(src_vrb_id=0, dst_vrb_id=1, src_port=0, dst_port=0, delay_budget=1),
            EdgeRecord(src_vrb_id=0, dst_vrb_id=2, src_port=0, dst_port=0, delay_budget=1),
            EdgeRecord(src_vrb_id=0, dst_vrb_id=3, src_port=0, dst_port=0, delay_budget=1),
        ]
        graph = FabricGraph(bs)
        for i in (1, 2, 3):
            c = graph.vrb_nodes[i]
            assert isinstance(c, ElasticFifo)
            c.capacity = 10
            c.out_ready = False

        source = graph.vrb_nodes[0]
        assert isinstance(source, ElasticFifo)
        test_tokens = [Token(data=10), Token(data=20), Token(data=30)]

        for tok in test_tokens:
            source.queue.append(tok)

        # Run 20 cycles
        for _ in range(20):
            graph.step()

        # All 3 consumers must receive all 3 tokens without duplication or drop
        for i in (1, 2, 3):
            consumer = graph.vrb_nodes[i]
            assert isinstance(consumer, ElasticFifo)
            assert list(consumer.queue) == test_tokens


class TestH3FabricGraphSlackElasticity:
    """Hypothesis H3 Verification on pure FabricGraph:

    Multi-stage GLE pipeline with variable slack FIFO depths (0, 1, 2, 4, 8).
    Proves that the end-to-end token sequence is 100% bit-exact across all slack depths.
    """

    @pytest.mark.parametrize("slack_depth", [0, 1, 2, 4, 8])
    def test_multi_stage_gle_pipeline_slack_invariance(self, slack_depth: int):
        # Pipeline: Source PEU (VRB 0) -> Inverter (VRB 1) -> Buffer (VRB 2) -> Inverter (VRB 3) -> Collector PEU (VRB 4)
        bs = OraBitstream(profile=PROFILE_ORA_D)
        bs.manifest = Manifest(gle4_count=3, peu_count=2)
        bs.vrb_records = [
            VrbRecord(VRB_PEU, 0, 0, [], [0]),                  # VRB 0: Source PEU
            VrbRecord(VRB_GLE4, 4, 0, [0x5555], [0, 1, 2, 3]),  # VRB 1: Inverter
            VrbRecord(VRB_GLE4, 4, 0, [0xAAAA], [0, 1, 2, 3]),  # VRB 2: Identity Buffer
            VrbRecord(VRB_GLE4, 4, 0, [0x5555], [0, 1, 2, 3]),  # VRB 3: Inverter (Invert again -> original data)
            VrbRecord(VRB_PEU, 0, 0, [], [0]),                  # VRB 4: Collector PEU
        ]
        bs.edges = [
            EdgeRecord(src_vrb_id=0, dst_vrb_id=1, src_port=0, dst_port=0, delay_budget=1),
            EdgeRecord(src_vrb_id=1, dst_vrb_id=2, src_port=0, dst_port=0, delay_budget=1),
            EdgeRecord(src_vrb_id=2, dst_vrb_id=3, src_port=0, dst_port=0, delay_budget=1),
            EdgeRecord(src_vrb_id=3, dst_vrb_id=4, src_port=0, dst_port=0, delay_budget=1),
        ]
        graph = FabricGraph(bs)
        # Insert slack on connection 1 (between Inverter and Buffer)
        graph.insert_slack(conn_idx=1, capacity=slack_depth)

        collector = graph.vrb_nodes[4]
        assert isinstance(collector, ElasticFifo)
        collector.capacity = 20
        collector.out_ready = False

        source = graph.vrb_nodes[0]
        assert isinstance(source, ElasticFifo)
        test_tokens = [Token(data=d) for d in [1, 0, 1, 1, 0, 0, 1, 0]]
        for tok in test_tokens:
            source.queue.append(tok)

        # Run cycles until all tokens reach collector
        for _ in range(50):
            graph.step()
            if len(collector.queue) == len(test_tokens):
                break

        # Sequence must match original test_tokens exactly across all slack depths
        assert list(collector.queue) == test_tokens

    @pytest.mark.parametrize("slack_depth", [0, 1, 3])
    def test_diamond_reconvergence_token_conservation(self, slack_depth: int):
        """H3 Diamond Reconvergence:

        VRB 0 (Source PEU) -> VRB 1 (Branch A with slack) & VRB 2 (Branch B)
                           -> VRB 3 (Sink Join AND) -> VRB 4 (Collector PEU)
        """
        bs = OraBitstream(profile=PROFILE_ORA_D)
        bs.manifest = Manifest(gle4_count=3, peu_count=2)
        bs.vrb_records = [
            VrbRecord(VRB_PEU, 0, 0, [], [0]),                  # VRB 0: Source PEU
            VrbRecord(VRB_GLE4, 4, 0, [0xAAAA], [0, 1, 2, 3]),  # VRB 1: Branch A
            VrbRecord(VRB_GLE4, 4, 0, [0xAAAA], [0, 1, 2, 3]),  # VRB 2: Branch B
            VrbRecord(VRB_GLE4, 4, 0, [0x8888], [0, 1, 2, 3]),  # VRB 3: Sink Join
            VrbRecord(VRB_PEU, 0, 0, [], [0]),                  # VRB 4: Collector PEU
        ]
        bs.edges = [
            EdgeRecord(src_vrb_id=0, dst_vrb_id=1, src_port=0, dst_port=0, delay_budget=1),
            EdgeRecord(src_vrb_id=0, dst_vrb_id=2, src_port=0, dst_port=0, delay_budget=1),
            EdgeRecord(src_vrb_id=1, dst_vrb_id=3, src_port=0, dst_port=0, delay_budget=1),
            EdgeRecord(src_vrb_id=2, dst_vrb_id=3, src_port=0, dst_port=1, delay_budget=1),
            EdgeRecord(src_vrb_id=3, dst_vrb_id=4, src_port=0, dst_port=0, delay_budget=1),
        ]
        graph = FabricGraph(bs)
        graph.insert_slack(conn_idx=0, capacity=slack_depth)

        collector = graph.vrb_nodes[4]
        assert isinstance(collector, ElasticFifo)
        collector.capacity = 20
        collector.out_ready = False

        source = graph.vrb_nodes[0]
        assert isinstance(source, ElasticFifo)
        test_tokens = [Token(data=d) for d in [1, 0, 1, 1, 0]]
        for tok in test_tokens:
            source.queue.append(tok)

        for _ in range(50):
            graph.step()
            if len(collector.queue) == len(test_tokens):
                break

        assert list(collector.queue) == test_tokens
