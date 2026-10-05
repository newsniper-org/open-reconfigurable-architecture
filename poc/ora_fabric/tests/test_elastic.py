"""Unit and property tests for ORA-D Elastic Core (M2).

Validates:
  - 2-wire distributed handshake semantics (Valid / Ready)
  - Elastic Join & Elastic Fork primitive behavior
  - GLE 4-LUT / 6-LUT truth table evaluation
  - H3 hypothesis: Slack elasticity (identical token sequences under variable FIFO slack depths)
"""

import pytest
from ora_fabric.elastic import (
    Token,
    ElasticFifo,
    ElasticFork,
    ElasticJoin,
    ElasticBranch,
    ElasticMerge,
    GleNode,
)


class TestHandshakeAndFifo:
    def test_fifo_basic_buffering(self):
        fifo = ElasticFifo(capacity=2)
        fifo.in_valid = True
        fifo.in_token = Token(data=42)
        fifo.out_ready = False

        in_f, out_f = fifo.step()
        assert in_f is True
        assert out_f is False
        assert len(fifo.queue) == 1
        assert fifo.out_valid is True
        assert fifo.out_token == Token(data=42)

    def test_fifo_full_backpressure(self):
        fifo = ElasticFifo(capacity=1)
        fifo.in_valid = True
        fifo.in_token = Token(data=1)
        fifo.out_ready = False
        fifo.step()

        # FIFO is full -> in_ready must be False
        assert fifo.in_ready is False
        fifo.in_token = Token(data=2)
        in_f, _ = fifo.step()
        assert in_f is False
        assert len(fifo.queue) == 1
        assert fifo.queue[0].data == 1


class TestJoinAndFork:
    def test_join_requires_all_inputs(self):
        join = ElasticJoin(num_inputs=2)
        join.out_ready = True

        # Only input 0 valid
        join.in_valid[0] = True
        join.in_tokens[0] = Token(data=0b10)
        join.in_valid[1] = False
        join.evaluate()
        assert join.out_valid is False

        # Both inputs valid -> fires
        join.in_valid[1] = True
        join.in_tokens[1] = Token(data=0b01)
        join.evaluate()
        assert join.out_valid is True
        assert join.out_token.data == 0b11
        assert join.in_ready == [True, True]

    def test_join_backpressure(self):
        join = ElasticJoin(num_inputs=2)
        join.in_valid = [True, True]
        join.in_tokens = [Token(1), Token(2)]
        join.out_ready = False
        join.evaluate()
        assert join.out_valid is True
        assert join.in_ready == [False, False]

    def test_fork_eager_acknowledgment(self):
        fork = ElasticFork(num_outputs=2)
        fork.in_valid = True
        fork.in_token = Token(data=99)
        fork.out_ready = [True, False]  # Branch 0 accepts, branch 1 stalls

        fork.evaluate()
        assert fork.out_valid == [True, True]
        assert fork.in_ready is False  # Cannot accept new token yet

        fork.step()
        # Branch 0 is now acked, branch 1 still needs to accept
        fork.evaluate()
        assert fork.out_valid == [False, True]
        assert fork.in_ready is False

        # Branch 1 finally ready
        fork.out_ready = [False, True]
        fork.evaluate()
        assert fork.in_ready is True  # Both branches now satisfied
        fired = fork.step()
        assert fired is True


class TestGleNode:
    def test_gle4_boolean_lut(self):
        # 4-input XOR between bit 0 and bit 1: truth table 0b0110_0110_0110_0110 (0x6666)
        gle = GleNode(node_id=0, lut_width=4, lut_init=[0x6666])
        assert gle.evaluate_lut([0, 0, 0, 0]) == 0
        assert gle.evaluate_lut([1, 0, 0, 0]) == 1
        assert gle.evaluate_lut([0, 1, 0, 0]) == 1
        assert gle.evaluate_lut([1, 1, 0, 0]) == 0

    def test_gle6_boolean_lut(self):
        # 6-input LUT parity check or bit testing
        gle = GleNode(node_id=1, lut_width=6, lut_init=[0x00000000, 0x80000000])
        # Bit 63 should be 1
        assert gle.evaluate_lut([1, 1, 1, 1, 1, 1]) == 1
        assert gle.evaluate_lut([0, 1, 1, 1, 1, 1]) == 0


class TestH3SlackElasticity:
    """Hypothesis H3 Verification:

    Adding arbitrary elastic FIFO buffers on channels must preserve the functional
    token sequence exactly (bit-level equality).
    """

    @pytest.mark.parametrize("slack_depth", [0, 1, 2, 4, 8])
    def test_linear_pipeline_token_invariance(self, slack_depth: int):
        # Pipelined inverter GLE with output elastic register (has_peu_reg=True)
        gle = GleNode(node_id=0, lut_width=4, lut_init=[0x5555], has_peu_reg=True)
        fifo = ElasticFifo(capacity=slack_depth) if slack_depth > 0 else None

        input_sequence = [Token(data=d) for d in [1, 0, 1, 1, 0, 0, 1, 0, 1, 1]]
        expected_output = [Token(data=d ^ 1) for d in [1, 0, 1, 1, 0, 0, 1, 0, 1, 1]]

        produced_idx = 0
        collected_output: list[Token] = []

        # Run cycle-by-cycle simulation
        for _ in range(100):
            has_input = produced_idx < len(input_sequence)
            prod_token = input_sequence[produced_idx] if has_input else None

            # Setup consumer ready
            gle.out_ready = True

            # Record if consumer fires this step
            consumer_fires = gle.out_valid and gle.out_ready
            current_out_token = gle.out_token

            if fifo is not None:
                fifo.in_valid = has_input
                fifo.in_token = prod_token
                fifo.out_ready = gle.in_ready[0]
                fifo.evaluate()

                gle.in_valid[0] = fifo.out_valid
                gle.in_tokens[0] = fifo.out_token
                for p in range(1, 4):
                    gle.in_valid[p] = True
                    gle.in_tokens[p] = Token(0)
                gle.evaluate()

                in_fired, _ = fifo.step()
                if in_fired:
                    produced_idx += 1
            else:
                gle.in_valid[0] = has_input
                gle.in_tokens[0] = prod_token
                for p in range(1, 4):
                    gle.in_valid[p] = True
                    gle.in_tokens[p] = Token(0)
                gle.evaluate()

                if has_input and gle.in_ready[0]:
                    produced_idx += 1
            gle.step()

            if consumer_fires and current_out_token is not None:
                collected_output.append(current_out_token)

            if len(collected_output) == len(expected_output):
                break

        # Invariance check: output sequence must be 100% bit-exact regardless of slack depth
        assert collected_output == expected_output


class TestBranchAndMerge:
    def test_branch_routing(self):
        branch = ElasticBranch(num_outputs=2)
        branch.out_ready = [True, True]

        # Condition = 1 -> routes to branch 1
        branch.in_valid = True
        branch.in_token = Token(data=42)
        branch.cond_valid = True
        branch.cond_token = Token(data=1)
        branch.evaluate()

        assert branch.out_valid == [False, True]
        assert branch.out_tokens[0] is None
        assert branch.out_tokens[1] == Token(data=42)
        assert branch.in_ready is True
        assert branch.cond_ready is True

        fired = branch.step()
        assert fired is True

        # Condition = 0 -> routes to branch 0
        branch.in_token = Token(data=100)
        branch.cond_token = Token(data=0)
        branch.evaluate()
        assert branch.out_valid == [True, False]
        assert branch.out_tokens[0] == Token(data=100)

    def test_branch_backpressure(self):
        branch = ElasticBranch(num_outputs=2)
        branch.in_valid = True
        branch.in_token = Token(data=7)
        branch.cond_valid = True
        branch.cond_token = Token(data=0)
        # Target branch 0 is stalled, branch 1 is ready
        branch.out_ready = [False, True]
        branch.evaluate()

        assert branch.out_valid == [True, False]
        assert branch.in_ready is False
        assert branch.cond_ready is False

    def test_merge_selection(self):
        merge = ElasticMerge(num_inputs=2)
        merge.out_ready = True

        merge.in_valid = [True, True]
        merge.in_tokens = [Token(data=10), Token(data=20)]

        # Select input 0
        merge.cond_valid = True
        merge.cond_token = Token(data=0)
        merge.evaluate()

        assert merge.out_valid is True
        assert merge.out_token == Token(data=10)
        assert merge.in_ready == [True, False]  # Input 0 accepted, input 1 stalls!
        assert merge.cond_ready is True

        fired = merge.step()
        assert fired is True

        # Select input 1
        merge.cond_token = Token(data=1)
        merge.evaluate()
        assert merge.out_valid is True
        assert merge.out_token == Token(data=20)
        assert merge.in_ready == [False, True]

    def test_merge_unselected_input_stalls(self):
        merge = ElasticMerge(num_inputs=2)
        merge.out_ready = True
        # Input 0 is valid, but input 1 is selected and invalid
        merge.in_valid = [True, False]
        merge.in_tokens = [Token(data=99), None]
        merge.cond_valid = True
        merge.cond_token = Token(data=1)
        merge.evaluate()

        assert merge.out_valid is False
        assert merge.in_ready == [False, False]
        assert merge.cond_ready is False

    def test_gle_multi_producer_lazy_join_no_token_loss(self):
        # 2-input AND GLE: port 0 and port 1
        gle = GleNode(node_id=0, lut_width=4, lut_init=[0x8888], has_peu_reg=True)
        # Unused ports 2 and 3 are tied to constant 0 (or valid)
        gle.in_valid[2] = True
        gle.in_tokens[2] = Token(0)
        gle.in_valid[3] = True
        gle.in_tokens[3] = Token(0)
        gle.out_ready = True

        # Producer 0 provides token at cycle 0
        gle.in_valid[0] = True
        gle.in_tokens[0] = Token(1)
        # Producer 1 has NO token yet
        gle.in_valid[1] = False
        gle.in_tokens[1] = None
        gle.evaluate()

        # CRUCIAL: Producer 0 must NOT be accepted yet because sibling port 1 is not valid!
        assert gle.in_ready[0] is False
        # Sibling port 1 is ready to accept when its token arrives
        assert gle.in_ready[1] is True
        # Producer 0 holds token (no cancellation), Producer 1 now provides token at cycle 1
        gle.in_valid[1] = True
        gle.in_tokens[1] = Token(1)
        gle.evaluate()

        # Now both inputs are valid -> both ready and fires!
        assert gle.in_ready[0] is True
        assert gle.in_ready[1] is True

        fired = gle.step()
        assert fired is True
        # Next step emits output Token(1)
        gle.evaluate()
        assert gle.out_valid is True
        assert gle.out_token == Token(1)
