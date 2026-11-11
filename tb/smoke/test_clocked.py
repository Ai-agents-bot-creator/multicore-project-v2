import cocotb
from cocotb.triggers import Timer, RisingEdge
from cocotb.clock import Clock

@cocotb.test()
async def test_dff_async(dut):
    """Test DFF with async active-low reset"""
    clock_gen = Clock(dut.clk, 10, units="ns")
    cocotb.start_soon(clock_gen.start())
    
    await Timer(1, units="ns")
    
    # Hold reset low, verify q==0
    dut.rst_n.value = 0
    dut.d.value = 1
    await Timer(22, units="ns")
    assert int(dut.q.value) == 0, f"Expected q=0 during reset, got {dut.q.value}"
    
    # Release reset, wait for next rising edge, then a delta cycle
    dut.rst_n.value = 1
    await RisingEdge(dut.clk)
    await Timer(1, units="ps")
    assert int(dut.q.value) == 1, f"Expected q=1 after d=1, got {dut.q.value}"
    
    # Drive d=0, wait next posedge
    dut.d.value = 0
    await RisingEdge(dut.clk)
    await Timer(1, units="ps")
    assert int(dut.q.value) == 0, f"Expected q=0 after d=0, got {dut.q.value}"
    
    # Assert reset low mid-cycle, verify q==0 (async reset)
    await Timer(7, units="ns")
    dut.d.value = 1
    dut.rst_n.value = 0
    await Timer(5, units="ns")
    assert int(dut.q.value) == 0, f"Expected q=0 after async reset, got {dut.q.value}"

    dut._log.info("All assertions passed")