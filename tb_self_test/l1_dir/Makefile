SIM ?= icarus
MODULE ?= test_f1_forward
TOPLEVEL ?= tb_l1_dir

VERILOG_SOURCES = \
    ../../rtl/pkg/tile_pkg.sv \
    ../../rtl/l1/l1_mesi_ctrl.sv \
    ../../rtl/directory/dir_ctrl.sv \
    ../../rtl/l2/l2_bank.sv \
    tb_l1_dir.sv

include $(shell cocotb-config --makefiles)/Makefile.sim