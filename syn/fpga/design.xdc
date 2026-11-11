# -----------------------------------------------------------------------------
# design.xdc - DESIGN constraints for the 2x2 (4-tile) FPGA configuration
#
# Scope: DESIGN. Everything here belongs to THIS design, not to the board.
# The board's pinout is in zc702_board.xdc and is reused unchanged.
#
# Target: AMD ZedBoard, XC7Z020-CLG484 (schematic rev C/D).
# Configuration: WP 3.2 - the 2x2 (4-tile) mesh, evaluated at 100 MHz.
# -----------------------------------------------------------------------------

# -----------------------------------------------------------------------------
# Clocking
#
# The ZedBoard's GCLK (Y9) is a 100 MHz oscillator (verified LOC, see
# zc702_board.xdc). The design targets 100 MHz, so the period is 10 ns.
# -----------------------------------------------------------------------------
create_clock -period 10.000 -name sys_clk_pin -waveform {0.000 5.000} [get_ports {clk_100mhz}]

# -----------------------------------------------------------------------------
# Reset
#
# The SRS v2 names two reset candidates: P16 (BTNC, the center push button)
# and F22 (SW0, DIP switch 0). Both LOCs are verified in zc702_board.xdc.
#
# The design uses the push button as the active-low reset input; the DIP
# switch is left in the board file as an alternative source and is NOT
# wired to a port of this design. If the DIP switch is wanted instead,
# change the port below and the corresponding constraint.
# -----------------------------------------------------------------------------
set_property IOSTANDARD LVCMOS18 [get_ports {reset_btn}]

# -----------------------------------------------------------------------------
# JTAG
#
# The JTAG pins (TCK/TDI/TMS/TDO) and the JTAG TCK period are left
# unconstrained - see the note in zc702_board.xdc and the open item in the
# white paper. No unverified LOC is asserted.
#
#   <UNCONFIRMED_TCK_PIN> / <UNCONFIRMED_TDI_PIN>
#   <UNCONFIRMED_TMS_PIN> / <UNCONFIRMED_TDO_PIN>
# -----------------------------------------------------------------------------
