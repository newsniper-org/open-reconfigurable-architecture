// ORA-N multi-port table-less router (SpinalHDL)
//
// Implements the arbitration contract of ora_fabric.router.NoCRouter
// (evaluate_cycle docstring) cycle-for-cycle:
//   - Every decision uses start-of-cycle (register) state only: FIFO heads,
//     locks, and downstream credits.
//   - Per (in_port, vc) input FIFO; one wormhole lock per input channel;
//     the (out_port, out_vc) lock table is derived from the channel locks.
//   - Each output port, including port 0 (local ejection), grants at most
//     one flit per cycle.
//   - Per-port round-robin between VC classes by requested out_vc: the class
//     that last won a port yields. Ties: lower channel index (in_port*2+vc).
//   - A lock released by a Tail is re-grantable in the next cycle.
//   - A lone ejected header keeps its (LOCAL, vc) lock until the channel's
//     next header arrives; that cycle only releases the lock.
//   - Chained-header drops consume no port and always happen.
//   - AER uses the VC0 class and may not enter a locked (out, VC0).
//
// Flat interface (bit index of channel/credit k = port*2 + vc):
//   inValid(p), inData(p*32 +: 32)   : flit arriving on input port p
//   inCredit(p*2+vc)                 : input FIFO (p, vc) has space
//   outValid(o), outData(o*32 +: 32) : flit leaving on port o (o=0: eject)
//   outCredit(o*2+vc)                : downstream FIFO behind port o has
//                                      space (ignored for o=0, always ready)
//
// Flit (32 bits):
//   [31:30] type (00 hdr, 01 body, 10 tail, 11 AER)  [29:28] vc
//   header: [27:25] hops [24] chained [23:21] vc_transition [20:0] dir
//   AER   : [27:26] hops [25:20] dir [19:0] neuron address

package ora

import spinal.core._
import spinal.lib._

object OraFlit {
  def headerStep(f: Bits): Bits = {
    val t = f(23 downto 21)
    val promoteNow = t === 0
    val sentinel = t === B"3'h7" // NO_VC_TRANSITION: preserved, never decremented
    val r = Bits(32 bits)
    r(31 downto 30) := f(31 downto 30)
    r(29 downto 28) := promoteNow ? B"2'h1" | f(29 downto 28)
    r(27 downto 25) := (f(27 downto 25).asUInt - 1).asBits
    r(24) := f(24)
    r(23 downto 21) := promoteNow ? B"3'h7" | (sentinel ? t | (t.asUInt - 1).asBits)
    r(20 downto 0) := (f(20 downto 0).asUInt >> 3).asBits.resize(21)
    r
  }

  def aerStep(f: Bits): Bits = {
    val r = Bits(32 bits)
    r := f
    r(29 downto 28) := B"2'h0"
    r(27 downto 26) := (f(27 downto 26).asUInt - 1).asBits
    r(25 downto 20) := (f(25 downto 20).asUInt >> 3).asBits.resize(6)
    r
  }

  def stampVc(f: Bits, vc: Bits): Bits = {
    val r = Bits(32 bits)
    r := f
    r(29 downto 28) := vc
    r
  }
}

class OraRouter(numPorts: Int = 7, depth: Int = 2) extends Component {
  require(numPorts >= 2 && numPorts <= 8, "port id is a 3-bit field")
  require(depth >= 2 && isPow2(depth), "FIFO depth must be a power of two >= 2")

  val NC = numPorts * 2 // input channels (port, vc)
  val ptrW = log2Up(depth)
  val cntW = log2Up(depth + 1)

  val io = new Bundle {
    val inValid = in Bits (numPorts bits)
    val inData = in Bits (numPorts * 32 bits)
    val inCredit = out Bits (NC bits)
    val outValid = out Bits (numPorts bits)
    val outData = out Bits (numPorts * 32 bits)
    val outCredit = in Bits (NC bits)
  }

  // ---------------- registered state ----------------
  val mem = Vec.fill(NC)(Vec.fill(depth)(Reg(Bits(32 bits)) init (0)))
  val rdPtr = Vec.fill(NC)(Reg(UInt(ptrW bits)) init (0))
  val wrPtr = Vec.fill(NC)(Reg(UInt(ptrW bits)) init (0))
  val count = Vec.fill(NC)(Reg(UInt(cntW bits)) init (0))

  val lockValid = Vec.fill(NC)(Reg(Bool()) init (False))
  val lockPort = Vec.fill(NC)(Reg(UInt(3 bits)) init (0))
  val lockVc = Vec.fill(NC)(Reg(Bits(2 bits)) init (0))

  // Per output port: VC class served last (init VC0 -> VC1 gets first turn)
  val lastVc = Vec.fill(numPorts)(Reg(Bits(2 bits)) init (0))

  // ---------------- start-of-cycle derived tables ----------------
  // (out_port, out_vc) is held iff some channel's lock points at it
  def held(o: UInt, v: Bits): Bool =
    (0 until NC).map(k => lockValid(k) && lockPort(k) === o && lockVc(k) === v).reduce(_ || _)

  val outCreditPadded = io.outCredit.resize(16)
  def credit(o: UInt, v: Bits): Bool =
    (o === 0) || outCreditPadded((o @@ v(0 downto 0).asUInt))

  // ---------------- per-channel request decode ----------------
  val reqValid = Vec(Bool(), NC)
  val reqPort = Vec(UInt(3 bits), NC)
  val reqVc = Vec(Bits(2 bits), NC)
  val reqWord = Vec(Bits(32 bits), NC)
  val reqStream = Vec(Bool(), NC) // continues an existing wormhole
  val reqNewLock = Vec(Bool(), NC) // header grant acquires a lock
  val eligible = Vec(Bool(), NC)
  val doChain = Vec(Bool(), NC)
  val doSelfRel = Vec(Bool(), NC)
  val headIsTail = Vec(Bool(), NC)

  for (c <- 0 until NC) {
    val f = mem(c)(rdPtr(c))
    val has = count(c) =/= 0
    val ty = f(31 downto 30)
    val isHdr = ty === B"2'b00"
    val isAer = ty === B"2'b11"
    headIsTail(c) := ty === B"2'b10"
    val hops = f(27 downto 25).asUInt
    val chained = f(24)
    val aerHops = f(27 downto 26).asUInt

    reqValid(c) := False
    reqPort(c) := 0
    reqVc(c) := B"2'h0"
    reqWord(c) := f
    reqStream(c) := False
    reqNewLock(c) := False
    doChain(c) := False
    doSelfRel(c) := False

    when(has) {
      when(lockValid(c)) {
        when(isHdr && lockPort(c) === 0) {
          doSelfRel(c) := True
        } otherwise {
          reqValid(c) := True
          reqPort(c) := lockPort(c)
          reqVc(c) := lockVc(c)
          reqWord(c) := OraFlit.stampVc(f, lockVc(c))
          reqStream(c) := True
        }
      } otherwise {
        when(isHdr) {
          when(hops === 0) {
            when(chained) {
              doChain(c) := True
            } otherwise {
              reqValid(c) := True
              reqPort(c) := 0
              reqVc(c) := f(29 downto 28)
              reqWord(c) := f
              reqNewLock(c) := True
            }
          } otherwise {
            val stepped = OraFlit.headerStep(f)
            reqValid(c) := True
            reqPort(c) := f(2 downto 0).asUInt
            reqVc(c) := stepped(29 downto 28)
            reqWord(c) := stepped
            reqNewLock(c) := True
          }
        } elsewhen (isAer) {
          reqValid(c) := True
          reqVc(c) := B"2'h0"
          when(aerHops === 0) {
            reqPort(c) := 0
            reqWord(c) := f
          } otherwise {
            reqPort(c) := f(22 downto 20).asUInt
            reqWord(c) := OraFlit.aerStep(f)
          }
        }
        // Body/Tail on an idle channel is a protocol error: no request
      }
    }

    eligible(c) := reqValid(c) && credit(reqPort(c), reqVc(c)) &&
      (reqStream(c) || !held(reqPort(c), reqVc(c)))
  }

  // ---------------- per-output-port arbitration ----------------
  val grantMatrix = Vec(Bits(NC bits), numPorts)
  for (o <- 0 until numPorts) {
    val cand = Bits(NC bits)
    val pri = Bits(NC bits)
    for (c <- 0 until NC) {
      cand(c) := eligible(c) && reqPort(c) === o
      pri(c) := eligible(c) && reqPort(c) === o && reqVc(c) =/= lastVc(o)
    }
    val pick = Mux(pri.orR, OHMasking.first(pri), OHMasking.first(cand))
    grantMatrix(o) := pick

    io.outValid(o) := cand.orR
    io.outData(o * 32 + 31 downto o * 32) := MuxOH(pick, reqWord)
    when(cand.orR) {
      lastVc(o) := MuxOH(pick, reqVc)
    }
  }

  // ---------------- channel state update + FIFOs ----------------
  for (c <- 0 until NC) {
    val p = c / 2
    val vc = c % 2
    val granted = (0 until numPorts).map(o => grantMatrix(o)(c)).reduce(_ || _)
    val pop = granted || doChain(c)

    when(doSelfRel(c)) {
      lockValid(c) := False
    }
    when(granted) {
      when(reqStream(c) && headIsTail(c)) {
        lockValid(c) := False
      }
      when(reqNewLock(c)) {
        lockValid(c) := True
        lockPort(c) := reqPort(c)
        lockVc(c) := reqVc(c)
      }
    }

    val inF = io.inData(p * 32 + 31 downto p * 32)
    val inVc = Mux(inF(31 downto 30) === B"2'b11", B"2'h0", inF(29 downto 28))
    val push = io.inValid(p) && inVc === B(vc, 2 bits)

    when(push) {
      mem(c)(wrPtr(c)) := inF
      wrPtr(c) := wrPtr(c) + 1
    }
    when(pop) {
      rdPtr(c) := rdPtr(c) + 1
    }
    when(push && !pop) {
      count(c) := count(c) + 1
    } elsewhen (pop && !push) {
      count(c) := count(c) - 1
    }

    io.inCredit(c) := count(c) < depth
  }
}

object OraRouterVerilog extends App {
  SpinalConfig(targetDirectory = "generated").generateVerilog(new OraRouter(numPorts = 7, depth = 2))
}
