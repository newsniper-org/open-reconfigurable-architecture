// ORA-N table-less router core (SpinalHDL)
//
// Normative single-channel core mirroring ora_bitstream.router_step and
// ora_fabric.router.NoCRouter cycle semantics:
//   IDLE : header with hops>0 -> forward (rewrite header), go ACTIVE
//          header at hops=0, chained=1 -> drop, stay IDLE
//          header at hops=0, chained=0 -> eject, stay IDLE
//          AER at hops=0 -> eject
//   ACTIVE: stream trailing flits with the VC field stamped to outVc;
//           Tail returns to IDLE
//
// Flit (32 bits):
//   [31:30] type  [29:28] vc  [27:25] hops  [24] chained
//   [23:21] vc_transition  [20:0] direction vector
// AER variant: [27:26] hops(2b)  [25:20] dir vector  [19:0] neuron addr

package ora

import spinal.core._
import spinal.lib._

class OraRouterCore(flitWidth: Int = 32) extends Component {
  val fw = flitWidth

  val io = new Bundle {
    val inp = slave Stream (Bits(fw bits))
    val out = master Stream (Bits(fw bits))
    val eject = master Stream (Bits(fw bits))
  }

  // ---- field accessors ----
  def fType(f: Bits): UInt = f(fw - 1 downto fw - 2).asUInt
  def fVc(f: Bits): Bits = f(fw - 3 downto fw - 4)
  def fHops(f: Bits): UInt = f(27 downto 25).asUInt
  def fChained(f: Bits): Bool = f(24)
  def fTrans(f: Bits): Bits = f(23 downto 21)
  def fDir(f: Bits): Bits = f(20 downto 0)

  // ---- normative header math ----
  def headerStep(f: Bits): Bits = {
    val h = fHops(f)
    val t = fTrans(f)
    val promoteNow = t === 0
    val sentinel = t === B"3'h7" // NO_VC_TRANSITION: preserved, never decremented
    val r = Bits(fw bits)
    r(fw - 1 downto fw - 2) := f(fw - 1 downto fw - 2)
    r(fw - 3 downto fw - 4) := promoteNow ? B"2'h1" | fVc(f)
    r(27 downto 25) := (h - 1).asBits.resize(3)
    r(24) := fChained(f)
    r(23 downto 21) := promoteNow ? B"3'h7" |
      (sentinel ? t | (t.asUInt - 1).asBits.resize(3))
    r(20 downto 0) := (fDir(f).asUInt >> 3).asBits.resize(21)
    r
  }

  def stampVc(f: Bits, vc: Bits): Bits = {
    val r = Bits(fw bits)
    r := f
    r(fw - 3 downto fw - 4) := vc
    r
  }

  // ---- wormhole state ----
  val active = RegInit(False)
  val outVc = RegInit(B"2'h0")

  val f = io.inp.payload
  val v = io.inp.valid

  val isHdr = fType(f) === 0
  val isAer = fType(f) === 3
  val isTail = fType(f) === 2
  val hopZero = fHops(f) === 0

  // AER uses bits [27:26] as its 2-bit hop count
  val aerHopZero = f(27 downto 26) === 0

  val doChain = isHdr && hopZero && fChained(f)
  val doEject = (isHdr && hopZero && !fChained(f)) || (isAer && aerHopZero)

  // ---- output selection ----
  val streamFwd = active && v && !doChain // ACTIVE: stream (incl. successor headers)
  val hdrFwd = !active && v && isHdr && !hopZero
  val aerFwd = !active && v && isAer && !aerHopZero

  io.out.valid := hdrFwd || streamFwd
  io.out.payload := Mux(active, stampVc(f, outVc), headerStep(f))

  // AER single-flit has its own field layout: rewrite via when (last
  // assignment wins in SpinalHDL)
  when(aerFwd) {
    io.out.valid := True
    val r = Bits(fw bits)
    r := f
    r(27 downto 26) := (f(27 downto 26).asUInt - 1).asBits // hops-1
    r(25 downto 20) := (f(25 downto 20).asUInt >> 3).asBits.resize(6) // dv >> 3
    io.out.payload := r
  }

  val ejectAct = !active && v && doEject && !isAer
  io.eject.valid := ejectAct
  io.eject.payload := f

  // ---- backpressure (handshake contract) ----
  // The input is consumed only when the selected action's downstream is ready:
  //   chained drop          -> always consume
  //   forward (hdr/aer/stream) -> requires io.out.ready
  //   eject                 -> requires io.eject.ready
  val fwdAct = hdrFwd || streamFwd || aerFwd
  io.inp.ready := doChain || (fwdAct && io.out.ready) || (ejectAct && io.eject.ready)

  // ---- state update (on fire, not just valid) ----
  when(io.inp.fire) {
    when(!active) {
      when(hdrFwd) {
        active := True
        outVc := headerStep(f)(fw - 3 downto fw - 4)
      }
    } otherwise {
      when(isTail) {
        active := False
      }
    }
  }
}

object OraRouterCoreVerilog extends App {
  SpinalConfig(targetDirectory = "generated").generateVerilog(new OraRouterCore(32))
}
