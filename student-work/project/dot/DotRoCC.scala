package chipyard

import chisel3._
import chisel3.util._
import org.chipsalliance.cde.config.{Config, Parameters}
import org.chipsalliance.diplomacy.lazymodule.LazyModule
import freechips.rocketchip.tile._

// Kept independent of Rocket parameters so command ordering and backpressure
// can be verified with the exact datapath used by the accelerator.
class DotCommand extends Bundle {
  val a = UInt(64.W)
  val b = UInt(64.W)
  val funct = UInt(7.W)
  val xd = Bool()
  val rd = UInt(5.W)
}

class DotResponse extends Bundle {
  val data = UInt(64.W)
  val rd = UInt(5.W)
}

class DotRoCCDatapath extends Module {
  val io = IO(new Bundle {
    val cmd = Flipped(Decoupled(new DotCommand))
    val resp = Decoupled(new DotResponse)
    val busy = Output(Bool())
  })

  val low = Module(new Dot4Unit)
  val high = Module(new Dot4Unit)
  low.io.a := io.cmd.bits.a(31, 0)
  low.io.b := io.cmd.bits.b(31, 0)
  high.io.a := io.cmd.bits.a(63, 32)
  high.io.b := io.cmd.bits.b(63, 32)

  // funct 0: DOT4, 1: DOT8, 2: CLEAR, 3: MAC4, 4: MAC8, 5: READ.
  // DOT operations leave the accumulator unchanged. MAC returns the NEW sum
  // when xd=1; xd=0 permits a stream followed by one blocking READ.
  val accum = RegInit(0.S(32.W))
  val useEight = io.cmd.bits.funct === 1.U || io.cmd.bits.funct === 4.U
  val dot = Wire(SInt(32.W))
  dot := low.io.result + Mux(useEight, high.io.result, 0.S(32.W))
  val nextAccum = Wire(SInt(32.W))
  nextAccum := accum + dot // Defined modulo 2^32 outside benchmark bounds.
  val result = WireDefault(0.S(32.W))
  switch(io.cmd.bits.funct) {
    is(0.U, 1.U) { result := dot }
    is(3.U, 4.U) { result := nextAccum }
    is(5.U) { result := accum }
  }

  val pending = RegInit(false.B)
  val response = Reg(new DotResponse)
  io.cmd.ready := !pending || io.resp.ready
  io.resp.valid := pending
  io.resp.bits := response
  io.busy := pending || io.cmd.valid

  when(io.resp.fire) { pending := false.B }
  when(io.cmd.fire) {
    when(io.cmd.bits.funct === 2.U) { accum := 0.S }
    when(io.cmd.bits.funct === 3.U || io.cmd.bits.funct === 4.U) {
      accum := nextAccum
    }
    when(io.cmd.bits.xd) {
      response.rd := io.cmd.bits.rd
      response.data := result.pad(64).asUInt
      pending := true.B
    }
  }
}

class DotRoCC(opcodes: OpcodeSet)(implicit p: Parameters) extends LazyRoCC(opcodes) {
  override lazy val module = new DotRoCCModuleImp(this)
}

class DotRoCCModuleImp(outer: DotRoCC)(implicit p: Parameters)
    extends LazyRoCCModuleImp(outer) with HasCoreParameters {
  require(xLen == 64, "DotRoCC uses two RV64 packed operands")
  val datapath = Module(new DotRoCCDatapath)
  datapath.io.cmd.valid := io.cmd.valid
  io.cmd.ready := datapath.io.cmd.ready
  datapath.io.cmd.bits.a := io.cmd.bits.rs1
  datapath.io.cmd.bits.b := io.cmd.bits.rs2
  datapath.io.cmd.bits.funct := io.cmd.bits.inst.funct
  datapath.io.cmd.bits.xd := io.cmd.bits.inst.xd
  datapath.io.cmd.bits.rd := io.cmd.bits.inst.rd
  io.resp.valid := datapath.io.resp.valid
  datapath.io.resp.ready := io.resp.ready
  io.resp.bits.rd := datapath.io.resp.bits.rd
  io.resp.bits.data := datapath.io.resp.bits.data
  io.busy := datapath.io.busy
  io.interrupt := false.B
  io.mem.req.valid := false.B
  io.mem.req.bits := 0.U.asTypeOf(io.mem.req.bits)
  io.mem.s1_kill := false.B
  io.mem.s2_kill := false.B
  io.mem.s1_data := 0.U.asTypeOf(io.mem.s1_data)
  io.mem.keep_clock_enabled := false.B
  io.mem.uncached_resp.foreach(_.ready := true.B)
  io.fpu_req.valid := false.B
  io.fpu_resp.ready := true.B
}

class WithDotRoCC extends Config((site, here, up) => {
  case BuildRoCC => up(BuildRoCC) ++ Seq((p: Parameters) =>
    LazyModule(new DotRoCC(OpcodeSet.custom0)(p)))
})

// Reserve custom1 for the independent DP accelerator. CPU-native custom
// instructions are evaluated in a separate configuration owned by Role 1.
class DotRoCCConfig extends Config(new WithDotRoCC ++ new BaselineConfig)
