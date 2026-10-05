"""ORA Elastic Core - Event-driven / Cycle-accurate Elastic Pipeline Simulator.

Implements the normative ORA-D specification (docs/ora_poc_standard_specification.typ section 1):
  - 2-wire distributed handshake (Valid / Ready)
  - No-cancellation rule
  - Slack elasticity via insert_slack(channel, depth)
  - GLE Boolean evaluation (4-LUT / 6-LUT)
  - Elastic Join / Fork / Branch / Merge primitives with backpressure propagation
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import Callable, Protocol


@dataclass(frozen=True)
class Token:
    """A dataflow token carrying payload and control tag."""

    data: int
    control: int = 0  # 00: normal, 01: start, 10: end, 11: reset


class ElasticEndpoint(Protocol):
    """Protocol for an object that can push to or pop from an elastic channel."""


class ElasticChannel:
    """A 2-wire distributed handshake channel between a producer and consumer.

    Signals:
      valid: producer has stable data available
      ready: consumer is ready to accept data
      token: the Token payload (valid when valid is True)

    Transaction fires if and only if (valid and ready) are both True in the same step.
    """

    def __init__(self, name: str = ""):
        self.name = name
        self.valid: bool = False
        self.ready: bool = False
        self.token: Token | None = None

        self._fifo: deque[Token] = deque()
        self._fifo_capacity: int = 0

    @property
    def fifo_depth(self) -> int:
        return self._fifo_capacity

    def set_slack_depth(self, depth: int) -> None:
        if depth < 0:
            raise ValueError("slack depth cannot be negative")
        self._fifo_capacity = depth

    def is_full(self) -> bool:
        if self._fifo_capacity == 0:
            return False
        return len(self._fifo) >= self._fifo_capacity

    def has_buffered_token(self) -> bool:
        return len(self._fifo) > 0


class ElasticFifo:
    """An explicit parameterizable Elastic Buffer (FIFO) inserted into a channel.

    Provides slack elasticity: buffers tokens up to capacity, decoupling producer
    and consumer timing while preserving exact token sequence.
    """

    def __init__(self, capacity: int, name: str = ""):
        if capacity <= 0:
            raise ValueError("FIFO capacity must be > 0")
        self.capacity = capacity
        self.name = name
        self.queue: deque[Token] = deque()

        # Producer interface (input)
        self.in_valid: bool = False
        self.in_ready: bool = True
        self.in_token: Token | None = None

        # Consumer interface (output)
        self.out_valid: bool = False
        self.out_ready: bool = False
        self.out_token: Token | None = None

    def evaluate_ready(self) -> bool:
        self.in_ready = len(self.queue) < self.capacity
        return self.in_ready

    def evaluate_valid(self) -> bool:
        if self.queue:
            self.out_valid = True
            self.out_token = self.queue[0]
        else:
            self.out_valid = False
            self.out_token = None
        return self.out_valid

    def evaluate(self) -> None:
        self.evaluate_valid()
        self.evaluate_ready()

    def step(self) -> tuple[bool, bool]:
        in_fired = False
        out_fired = False

        if self.out_valid and self.out_ready:
            self.queue.popleft()
            out_fired = True

        if self.in_valid and self.in_ready and self.in_token is not None:
            self.queue.append(self.in_token)
            in_fired = True

        self.evaluate()
        return in_fired, out_fired


class ElasticFork:
    """Elastic Fork primitive (1 input -> N outputs).

    Eager fork with acknowledgment tracking: emits valid token to all outputs,
    maintains backpressure until every output channel has accepted the token.
    """

    def __init__(self, num_outputs: int = 2, name: str = ""):
        self.num_outputs = num_outputs
        self.name = name
        self.in_valid: bool = False
        self.in_ready: bool = False
        self.in_token: Token | None = None

        self.out_valid: list[bool] = [False] * num_outputs
        self.out_ready: list[bool] = [False] * num_outputs
        self.out_tokens: list[Token | None] = [None] * num_outputs

        self._acked: list[bool] = [False] * num_outputs

    def evaluate(self) -> None:
        if self.in_valid and self.in_token is not None:
            for i in range(self.num_outputs):
                if not self._acked[i]:
                    self.out_valid[i] = True
                    self.out_tokens[i] = self.in_token
                else:
                    self.out_valid[i] = False
                    self.out_tokens[i] = None
        else:
            for i in range(self.num_outputs):
                self.out_valid[i] = False
                self.out_tokens[i] = None

        all_done = True
        for i in range(self.num_outputs):
            branch_done = self._acked[i] or (self.out_valid[i] and self.out_ready[i])
            if not branch_done:
                all_done = False
                break
        self.in_ready = all_done

    def step(self) -> bool:
        fired = False
        if self.in_valid and self.in_token is not None:
            for i in range(self.num_outputs):
                if self.out_valid[i] and self.out_ready[i]:
                    self._acked[i] = True

            if all(self._acked):
                self._acked = [False] * self.num_outputs
                fired = True

        self.evaluate()
        return fired


class ElasticJoin:
    """Elastic Join primitive (N inputs -> 1 output).

    Lazy join: fires only when ALL input channels present a valid token simultaneously.
    """

    def __init__(self, num_inputs: int = 2, name: str = ""):
        self.num_inputs = num_inputs
        self.name = name

        self.in_valid: list[bool] = [False] * num_inputs
        self.in_ready: list[bool] = [False] * num_inputs
        self.in_tokens: list[Token | None] = [None] * num_inputs

        self.out_valid: bool = False
        self.out_ready: bool = False
        self.out_token: Token | None = None

        self.combiner: Callable[[list[Token]], Token] = self._default_combiner

    @staticmethod
    def _default_combiner(tokens: list[Token]) -> Token:
        res = 0
        for t in tokens:
            res |= t.data
        return Token(data=res, control=tokens[0].control if tokens else 0)

    def evaluate(self) -> None:
        all_valid = all(self.in_valid)
        self.out_valid = all_valid
        if all_valid:
            valid_tokens = [t for t in self.in_tokens if t is not None]
            self.out_token = self.combiner(valid_tokens)
        else:
            self.out_token = None

        # Lazy join: input i is ready iff output is ready AND all other siblings are valid
        for i in range(self.num_inputs):
            siblings_valid = all(self.in_valid[j] for j in range(self.num_inputs) if j != i)
            self.in_ready[i] = self.out_ready and siblings_valid

    def step(self) -> bool:
        fired = False
        all_valid = all(self.in_valid)
        if all_valid and self.out_ready:
            fired = True
        self.evaluate()
        return fired


class GleNode:
    """Generic Logic Element (GLE) execution model.

    Evaluates Boolean truth table (4-LUT / 6-LUT) and optionally latches into an elastic output register.
    Implements standard Lazy-Join input semantics: input i is ready iff the node can accept and all
    other sibling inputs are valid.
    """

    def __init__(
        self,
        node_id: int,
        lut_width: int,
        lut_init: list[int],
        has_peu_reg: bool = False,
        name: str = "",
    ):
        self.node_id = node_id
        self.lut_width = lut_width
        self.lut_init = lut_init
        self.has_peu_reg = has_peu_reg
        self.name = name or f"GLE_{node_id}"

        self.in_valid: list[bool] = [False] * lut_width
        self.in_ready: list[bool] = [False] * lut_width
        self.in_tokens: list[Token | None] = [None] * lut_width

        self.out_valid: bool = False
        self.out_ready: bool = False
        self.out_token: Token | None = None

        # Internal elastic register state if has_peu_reg is True
        self._reg_valid: bool = False
        self._reg_token: Token | None = None

        self.evaluate()

    def evaluate_lut(self, inputs: list[int]) -> int:
        addr = 0
        for i, val in enumerate(inputs):
            if val & 1:
                addr |= 1 << i

        if self.lut_width == 4:
            word = self.lut_init[0] if self.lut_init else 0
            return (word >> (addr & 0xF)) & 1
        elif self.lut_width == 6:
            word_idx = (addr >> 5) & 1
            bit_idx = addr & 0x1F
            word = self.lut_init[word_idx] if word_idx < len(self.lut_init) else 0
            return (word >> bit_idx) & 1
        return 0

    def evaluate(self) -> None:
        if self.has_peu_reg:
            self.out_valid = self._reg_valid
            self.out_token = self._reg_token
            can_accept = not self._reg_valid or (self.out_valid and self.out_ready)

            for i in range(self.lut_width):
                siblings_valid = all(self.in_valid[j] for j in range(self.lut_width) if j != i)
                self.in_ready[i] = can_accept and siblings_valid
        else:
            all_in_valid = all(self.in_valid)
            self.out_valid = all_in_valid
            if all_in_valid:
                in_bits = [(t.data & 1) if t is not None else 0 for t in self.in_tokens]
                out_bit = self.evaluate_lut(in_bits)
                ctrl = self.in_tokens[0].control if self.in_tokens and self.in_tokens[0] else 0
                self.out_token = Token(data=out_bit, control=ctrl)
            else:
                self.out_token = None

            for i in range(self.lut_width):
                siblings_valid = all(self.in_valid[j] for j in range(self.lut_width) if j != i)
                self.in_ready[i] = self.out_ready and siblings_valid

    def step(self) -> bool:
        fired = False
        if self.has_peu_reg:
            # 1. Output firing
            if self.out_valid and self.out_ready:
                self._reg_valid = False
                self._reg_token = None
                fired = True

            # 2. Input latching
            all_in_valid = all(self.in_valid)
            can_accept = not self._reg_valid
            if all_in_valid and can_accept:
                in_bits = [(t.data & 1) if t is not None else 0 for t in self.in_tokens]
                out_bit = self.evaluate_lut(in_bits)
                ctrl = self.in_tokens[0].control if self.in_tokens and self.in_tokens[0] else 0
                self._reg_token = Token(data=out_bit, control=ctrl)
                self._reg_valid = True
                fired = True
        else:
            all_in_valid = all(self.in_valid)
            if all_in_valid and self.out_ready:
                fired = True

        self.evaluate()
        return fired


class ElasticBranch:
    """Elastic Branch primitive (Conditional Demux / Router)."""

    def __init__(self, num_outputs: int = 2, name: str = ""):
        self.num_outputs = num_outputs
        self.name = name

        self.in_valid: bool = False
        self.in_ready: bool = False
        self.in_token: Token | None = None

        self.cond_valid: bool = False
        self.cond_ready: bool = False
        self.cond_token: Token | None = None

        self.out_valid: list[bool] = [False] * num_outputs
        self.out_ready: list[bool] = [False] * num_outputs
        self.out_tokens: list[Token | None] = [None] * num_outputs

        self.evaluate()

    def evaluate(self) -> None:
        has_cond = self.cond_valid and self.cond_token is not None
        both_valid = self.in_valid and has_cond
        sel = (self.cond_token.data % self.num_outputs) if (both_valid and self.cond_token is not None) else -1
        for i in range(self.num_outputs):
            if i == sel and both_valid:
                self.out_valid[i] = True
                self.out_tokens[i] = self.in_token
            else:
                self.out_valid[i] = False
                self.out_tokens[i] = None

        if both_valid and 0 <= sel < self.num_outputs:
            branch_ready = self.out_ready[sel]
            self.in_ready = branch_ready
            self.cond_ready = branch_ready
        else:
            self.in_ready = False
            self.cond_ready = False

    def step(self) -> bool:
        fired = False
        has_cond = self.cond_valid and self.cond_token is not None
        both_valid = self.in_valid and has_cond
        if both_valid and self.cond_token is not None:
            sel = self.cond_token.data % self.num_outputs
            if self.out_ready[sel]:
                fired = True
        self.evaluate()
        return fired


class ElasticMerge:
    """Elastic Merge primitive (Conditional Multiplexer)."""

    def __init__(self, num_inputs: int = 2, name: str = ""):
        self.num_inputs = num_inputs
        self.name = name

        self.in_valid: list[bool] = [False] * num_inputs
        self.in_ready: list[bool] = [False] * num_inputs
        self.in_tokens: list[Token | None] = [None] * num_inputs

        self.cond_valid: bool = False
        self.cond_ready: bool = False
        self.cond_token: Token | None = None

        self.out_valid: bool = False
        self.out_ready: bool = False
        self.out_token: Token | None = None

        self.evaluate()

    def evaluate(self) -> None:
        if self.cond_valid and self.cond_token is not None:
            sel = self.cond_token.data % self.num_inputs
            sel_valid = self.in_valid[sel] and (self.in_tokens[sel] is not None)
            self.out_valid = sel_valid
            self.out_token = self.in_tokens[sel] if sel_valid else None

            for i in range(self.num_inputs):
                if i == sel:
                    self.in_ready[i] = sel_valid and self.out_ready
                else:
                    self.in_ready[i] = False
            self.cond_ready = sel_valid and self.out_ready
        else:
            self.out_valid = False
            self.out_token = None
            for i in range(self.num_inputs):
                self.in_ready[i] = False
            self.cond_ready = False

    def step(self) -> bool:
        fired = False
        if self.cond_valid and self.cond_token is not None:
            sel = self.cond_token.data % self.num_inputs
            if self.in_valid[sel] and self.out_ready:
                fired = True
        self.evaluate()
        return fired
