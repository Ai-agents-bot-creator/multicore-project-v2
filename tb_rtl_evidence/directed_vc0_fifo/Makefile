SIM ?= icarus
MODULE ?= directed_vc0_fifo
TOPLEVEL ?= tb_directed_vc0_fifo

L1_MESI ?= ../../rtl/l1/l1_mesi_ctrl.sv
DIR_CTRL ?= ../../rtl/directory/dir_ctrl.sv
SIM_BUILD ?= sim_build

VERILOG_SOURCES = \
    ../../rtl/pkg/tile_pkg.sv \
    $(L1_MESI) \
    $(DIR_CTRL) \
    tb_directed_vc0_fifo.sv

include $(shell cocotb-config --makefiles)/Makefile.sim
