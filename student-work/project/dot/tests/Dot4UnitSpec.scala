package chipyard

import chisel3._
import chiseltest._
import org.scalatest.flatspec.AnyFlatSpec

class Dot4UnitSpec extends AnyFlatSpec with ChiselScalatestTester {

  behavior of "Dot4Unit"

  it should "compute signed INT8 dot products correctly" in {

    test(new Dot4Unit) { dut =>

      // Test 1:
      // [1,2,3,4] dot [5,6,7,8] = 70
      dut.io.a.poke("h04030201".U)
      dut.io.b.poke("h08070605".U)

      dut.io.result.expect(70.S)

      // Test 2:
      // [-1,2,-3,4] dot [5,-6,7,-8] = -70
      dut.io.a.poke("h04FD02FF".U)
      dut.io.b.poke("hF807FA05".U)

      dut.io.result.expect((-70).S)

      // Test 3:
      // [127,127,127,127] dot same = 64516
      dut.io.a.poke("h7F7F7F7F".U)
      dut.io.b.poke("h7F7F7F7F".U)

      dut.io.result.expect(64516.S)

      dut.io.a.poke("h80808080".U)
      dut.io.b.poke("h80808080".U)
      dut.io.result.expect(65536.S)

      dut.io.b.poke("h7F7F7F7F".U)
      dut.io.result.expect((-65024).S)

      val random = new scala.util.Random(562)
      for (_ <- 0 until 1000) {
        val a = BigInt(32, random)
        val b = BigInt(32, random)
        def lane(value: BigInt, i: Int): Int = {
          val byte = ((value >> (8*i)) & 255).toInt
          if (byte >= 128) byte - 256 else byte
        }
        val expected = (0 until 4).map(i => lane(a,i)*lane(b,i)).sum
        dut.io.a.poke(a.U)
        dut.io.b.poke(b.U)
        dut.io.result.expect(expected.S)
      }
    }
  }
}
