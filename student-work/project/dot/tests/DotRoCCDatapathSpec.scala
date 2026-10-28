package chipyard

import chisel3._
import chiseltest._
import org.scalatest.flatspec.AnyFlatSpec

class DotRoCCDatapathSpec extends AnyFlatSpec with ChiselScalatestTester {
  behavior of "DotRoCCDatapath"

  it should "preserve responses under backpressure and order accumulator commands" in {
    test(new DotRoCCDatapath) { dut =>
      dut.io.cmd.valid.poke(false.B)
      dut.io.resp.ready.poke(false.B)
      dut.reset.poke(true.B)
      dut.clock.step()
      dut.reset.poke(false.B)
      def command(funct: Int, a: BigInt = 0, b: BigInt = 0,
                  xd: Boolean = false, rd: Int = 0): Unit = {
        dut.io.cmd.bits.funct.poke(funct.U)
        dut.io.cmd.bits.a.poke(a.U)
        dut.io.cmd.bits.b.poke(b.U)
        dut.io.cmd.bits.xd.poke(xd.B)
        dut.io.cmd.bits.rd.poke(rd.U)
        dut.io.cmd.valid.poke(true.B)
      }
      def issue(funct: Int, a: BigInt = 0, b: BigInt = 0,
                xd: Boolean = false, rd: Int = 0): Unit = {
        command(funct,a,b,xd,rd)
        dut.io.cmd.ready.expect(true.B)
        dut.clock.step()
        dut.io.cmd.valid.poke(false.B)
      }
      def response(value: BigInt, rd: Int): Unit = {
        dut.io.resp.valid.expect(true.B)
        dut.io.resp.bits.data.expect((value & ((BigInt(1)<<64)-1)).U)
        dut.io.resp.bits.rd.expect(rd.U)
      }
      def consume(): Unit = {
        dut.io.resp.ready.poke(true.B)
        dut.clock.step()
        dut.io.resp.ready.poke(false.B)
        dut.io.resp.valid.expect(false.B)
      }

      // A blocked output must retain its data AND destination register.
      issue(0,BigInt("04fd02ff",16),BigInt("f807fa05",16),true,17)
      response(-70,17)
      command(2) // CLEAR must not be accepted while the response is blocked.
      for (_ <- 0 until 5) {
        dut.io.cmd.ready.expect(false.B)
        response(-70,17)
        dut.clock.step()
      }
      dut.io.resp.ready.poke(true.B)
      dut.io.cmd.ready.expect(true.B)
      dut.clock.step() // Simultaneously consumes the response and accepts CLEAR.
      dut.io.cmd.valid.poke(false.B)
      dut.io.resp.ready.poke(false.B)
      dut.io.resp.valid.expect(false.B)
      issue(3,BigInt("80808080",16),BigInt("80808080",16))
      issue(4,BigInt("8080808080808080",16),BigInt("7f7f7f7f7f7f7f7f",16))
      issue(5,xd=true,rd=3)
      response(-64512,3)
      consume()

      // Deterministic random streams exercise DOT4/DOT8, MAC new-value
      // responses, CLEAR, READ, ignored upper lanes and response replacement.
      val random = new scala.util.Random(562)
      var accumulator = BigInt(-64512)
      def wrap32(x: BigInt): BigInt = {
        val v = x & ((BigInt(1)<<32)-1)
        if (v.testBit(31)) v-(BigInt(1)<<32) else v
      }
      for (_ <- 0 until 500) {
        val f = random.nextInt(6)
        val a = BigInt(64,random)
        val b = BigInt(64,random)
        val lanes = if (f == 1 || f == 4) 8 else 4
        def lane(x: BigInt, i: Int): Int = {
          val v = ((x >> (8*i)) & 255).toInt
          if (v >= 128) v-256 else v
        }
        val dot = BigInt((0 until lanes).map(i => lane(a,i)*lane(b,i)).sum)
        val result = f match {
          case 0 | 1 => dot
          case 2 => accumulator = 0; BigInt(0)
          case 3 | 4 => accumulator = wrap32(accumulator+dot); accumulator
          case 5 => accumulator
        }
        val xd = random.nextBoolean()
        val rd = 1+random.nextInt(31)
        issue(f,a,b,xd,rd)
        if (xd) {
          for (_ <- 0 to random.nextInt(4)) {
            response(result,rd)
            dut.clock.step()
          }
          consume()
        } else dut.io.resp.valid.expect(false.B)
      }
      // Maximum positive DOT8 requires 19 signed bits before extension.
      issue(1,BigInt("8080808080808080",16),BigInt("8080808080808080",16),true,31)
      response(131072,31)
      // A second response can replace one consumed in the same cycle.
      command(0,BigInt("7f7f7f7f",16),BigInt("7f7f7f7f",16),true,4)
      dut.io.resp.ready.poke(true.B)
      dut.clock.step()
      dut.io.cmd.valid.poke(false.B)
      dut.io.resp.ready.poke(false.B)
      response(64516,4)
      consume()
      dut.io.busy.expect(false.B)
    }
  }
}
