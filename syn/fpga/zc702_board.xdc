# -----------------------------------------------------------------------------
# zc702_board.xdc - BOARD constraints for the AMD ZedBoard (XC7Z020-CLG484)
#
# Scope: BOARD. Everything here is a property of the physical board, not of
# this design. The design-specific constraints (clock period, false paths,
# design wiring) live in design.xdc and are kept separate so the board file
# can be reused unchanged for any design targeting the same board.
#
# Pin provenance: every LOC below was verified against the Avnet
# ZedBoard master XDC, revision C/D v2
#   https://github.com/Avnet/hdl/blob/master/Boards/ZEDBOARD/zedboard_master_XDC_RevC_D_v2.xdc
# The board file itself is the normative statement of the board's pinout for
# schematic rev C/D (UG937). Each constraint below carries the net name used
# by that master file so the mapping can be re-checked line by line.
#
# Bank voltages on the ZedBoard (from the master XDC):
#   bank 13 -> 3.3 V fixed
#   bank 33 -> 3.3 V fixed
#   bank 34 -> 1.8 V default (Vadj jumper J18; 2.5 V / 3.3 V selectable)
#   bank 35 -> 1.8 V default (Vadj jumper J18; 2.5 V / 3.3 V selectable)
# -----------------------------------------------------------------------------

# -----------------------------------------------------------------------------
# Clock Source - Bank 13
# Master XDC: set_property PACKAGE_PIN Y9 [get_ports {GCLK}];  # "GCLK"
# -----------------------------------------------------------------------------
set_property PACKAGE_PIN Y9 [get_ports {clk_100mhz}]        ;# "GCLK"  (verified: Avnet master XDC RevC/D v2)

# -----------------------------------------------------------------------------
# User LEDs - Bank 33  (master XDC nets LD0..LD3)
# -----------------------------------------------------------------------------
set_property PACKAGE_PIN T22 [get_ports {led[0]}]           ;# "LD0"   (verified: Avnet master XDC RevC/D v2)
set_property PACKAGE_PIN T21 [get_ports {led[1]}]           ;# "LD1"   (verified: Avnet master XDC RevC/D v2)
set_property PACKAGE_PIN U22 [get_ports {led[2]}]           ;# "LD2"   (verified: Avnet master XDC RevC/D v2)
set_property PACKAGE_PIN U21 [get_ports {led[3]}]           ;# "LD3"   (verified: Avnet master XDC RevC/D v2)

# -----------------------------------------------------------------------------
# Reset inputs - Bank 34 (BTNC, center push button) and Bank 35 (SW0)
#
# Two candidate reset sources are provided because the SRS v2 names both
# (P16 / F22). Both are verified against the master XDC:
#   P16 -> "BTNC" (center push button)   bank 34
#   F22 -> "SW0"  (DIP switch 0)         bank 35
# Exactly one of them is connected in a given build; see design.xdc.
# -----------------------------------------------------------------------------
set_property PACKAGE_PIN P16 [get_ports {reset_btn}]        ;# "BTNC"  (verified: Avnet master XDC RevC/D v2)
set_property PACKAGE_PIN F22 [get_ports {reset_sw}]         ;# "SW0"   (verified: Avnet master XDC RevC/D v2)

# -----------------------------------------------------------------------------
# JTAG - NOT CONSTRAINED
#
# The JTAG pins (TCK/TDI/TMS/TDO) are deliberately left unconstrained:
#   <UNCONFIRMED_TCK_PIN> / <UNCONFIRMED_TDI_PIN>
#   <UNCONFIRMED_TMS_PIN> / <UNCONFIRMED_TDO_PIN>
#
# Reason: on the ZedBoard the PS JTAG signals are on the dedicated Zynq
# PS JTAG pins, which the board master XDC does not assign as PL package
# pins. The JTAG TCK period is also an open item in the white paper
# (the TCK frequency is a function of the JTAG chain topology, which is
# not fixed by this board file). No LOC is asserted that has not been
# verified against the board master XDC.
# -----------------------------------------------------------------------------

# -----------------------------------------------------------------------------
# IOSTANDARD constraints
#
# Placed AFTER the PACKAGE_PIN constraints on purpose: a bank-wide
# IOSTANDARD evaluated before the PACKAGE_PIN constraints of that bank are
# applied will not take effect (this is called out in the master XDC).
# -----------------------------------------------------------------------------

# Bank 33 (user LEDs, HDMI, VGA): fixed 3.3 V on the ZedBoard.
set_property IOSTANDARD LVCMOS33 [get_ports -of_objects [get_iobanks 33]];

# Bank 13 (clock source, Pmod JA/JB/JC/JD): fixed 3.3 V on the ZedBoard.
set_property IOSTANDARD LVCMOS33 [get_ports -of_objects [get_iobanks 13]];

# Bank 34 (push buttons, reset_btn): 1.8 V by default (Vadj jumper J18).
set_property IOSTANDARD LVCMOS18 [get_ports -of_objects [get_iobanks 34]];

# Bank 35 (DIP switches, reset_sw): 1.8 V by default (Vadj jumper J18).
set_property IOSTANDARD LVCMOS18 [get_ports -of_objects [get_iobanks 35]];
