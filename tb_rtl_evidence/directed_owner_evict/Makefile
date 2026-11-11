SIM ?= icarus
MODULE ?= directed_owner_evict
TOPLEVEL ?= tb_directed_owner_evict

# DIR_CTRL selects the directory under test. The negative control compiles the
# mutated copy instead: make DIR_CTRL=dir_ctrl_mut.sv SIM_BUILD=sim_build_mut
DIR_CTRL ?= ../../rtl/directory/dir_ctrl.sv
SIM_BUILD ?= sim_build

VERILOG_SOURCES = \
    ../../rtl/pkg/tile_pkg.sv \
    ../../rtl/l1/l1_mesi_ctrl.sv \
    $(DIR_CTRL) \
    tb_directed_owner_evict.sv

include $(shell cocotb-config --makefiles)/Makefile.sim
