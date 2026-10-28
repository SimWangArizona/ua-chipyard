package chipyard

import chisel3._

class Dot4Unit extends Module {

  val io = IO(new Bundle {
    val a = Input(UInt(32.W))
    val b = Input(UInt(32.W))

    val result = Output(SInt(32.W))
  })

  // Extract four signed INT8 values from input A
  val a0 = io.a(7, 0).asSInt
  val a1 = io.a(15, 8).asSInt
  val a2 = io.a(23, 16).asSInt
  val a3 = io.a(31, 24).asSInt

  // Extract four signed INT8 values from input B
  val b0 = io.b(7, 0).asSInt
  val b1 = io.b(15, 8).asSInt
  val b2 = io.b(23, 16).asSInt
  val b3 = io.b(31, 24).asSInt

  // Four parallel signed INT8 multipliers
  val p0 = Wire(SInt(16.W))
  val p1 = Wire(SInt(16.W))
  val p2 = Wire(SInt(16.W))
  val p3 = Wire(SInt(16.W))

  p0 := a0 * b0
  p1 := a1 * b1
  p2 := a2 * b2
  p3 := a3 * b3

  // Adder tree
  val sum01 = Wire(SInt(17.W))
  val sum23 = Wire(SInt(17.W))

  sum01 := p0 +& p1
  sum23 := p2 +& p3

  val total = Wire(SInt(18.W))
  total := sum01 +& sum23

  // Sign-extend the result to 32 bits
  io.result := total
}