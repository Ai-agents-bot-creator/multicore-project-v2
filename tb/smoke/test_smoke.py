import cocotb
from cocotb.triggers import Timer

@cocotb.test()
async def test_add(dut):
    """Test 2 + 3 == 5"""
    dut.a.value = 2
    dut.b.value = 3
    dut.op.value = 0  # add
    await Timer(1, units="ns")
    assert dut.y.value == 5, f"Expected 5, got {dut.y.value}"
    dut._log.info(f"PASS: 2 + 3 = {dut.y.value}")