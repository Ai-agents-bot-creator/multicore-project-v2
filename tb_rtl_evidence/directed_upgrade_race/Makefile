SIM ?= icarus
MODULE ?= directed_upgrade_race
TOPLEVEL ?= tb_directed_upgrade_race

# L1_MESI selects the L1 under test. The negative control compiles the
# defer-INV mutant instead: make L1_MESI=l1_mesi_ctrl_defer_inv.sv SIM_BUILD=sim_build_mut
L1_MESI ?= ../../rtl/l1/l1_mesi_ctrl.sv
DIR_CTRL ?= ../../rtl/directory/dir_ctrl.sv
SIM_BUILD ?= sim_build

VERILOG_SOURCES = \
    ../../rtl/pkg/tile_pkg.sv \
    $(L1_MESI) \
    $(DIR_CTRL) \
    tb_directed_upgrade_race.sv

include $(shell cocotb-config --makefiles)/Makefile.sim
