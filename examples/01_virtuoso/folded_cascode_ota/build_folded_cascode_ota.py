#!/usr/bin/env python3
"""Build a folded-cascode OTA schematic in Cadence Virtuoso — programmatically.

A worked example of driving Virtuoso with virtuoso-bridge: it places 11 MOS
devices, wires them purely by **net-label connectivity** (same net name -> same
node, no manual wires), sets per-device W/L through the CDF, and drops the I/O +
bias pins — producing a complete, schematic-checked, saved cellview.

Topology: a PMOS input pair (M1/M2) folded into an NMOS cascode, with a
self-biased PMOS cascode-mirror load (M9/M10 gate = cascode node nA2).
    input/tail : M0 (tail), M1 (VIN+), M2 (VIN-)
    col-1 (ref): M9 (mirror) - M7 (pcasc) - M5 (ncasc) - M3 (sink)
    col-2 (out): M10(mirror) - M8 (pcasc) - M6 (ncasc) - M4 (sink)
    OUT = M8.drain = M6.drain  (single-ended high-impedance node)

>>> ADAPT TO YOUR PDK: change DEV_LIB / PMOS / NMOS to your device cells and the
    W/L in SIZES. The names below are placeholders — building the schematic needs
    NO PDK models (only simulating it does).

Run (with a virtuoso-bridge session up + a .env pointing at your Virtuoso):
    python build_folded_cascode_ota.py
"""
from __future__ import annotations

from virtuoso_bridge import VirtuosoClient
from virtuoso_bridge.virtuoso.schematic.ops import (
    schematic_create_inst_by_master_name,
    schematic_create_pin,
)
from virtuoso_bridge.virtuoso.schematic.params import set_instance_params

# --- target cell + device cells (EDIT for your PDK) --------------------------
LIB, CELL = "myLib", "FC_OTA"
DEV_LIB = "myPdk"                       # <-- library holding your MOS symbols
PMOS, NMOS = "pmos_2v", "nmos_2v"       # <-- your PMOS / NMOS device cell names

# transistor: name, cell, x, y, drain, gate, source, body
# positions are cosmetic — connectivity is purely by net-label name match.
T = [
    # input stage
    ("M0",  PMOS, 4, 9, "ntail", "Vb_tail", "VDD",   "VDD"),
    ("M1",  PMOS, 3, 7, "nA",    "VINP",    "ntail", "VDD"),
    ("M2",  PMOS, 1, 7, "nB",    "VINN",    "ntail", "VDD"),
    # column 1 — reference branch
    ("M9",  PMOS, 6, 9, "nA3",   "nA2",     "VDD",   "VDD"),
    ("M7",  PMOS, 6, 7, "nA2",   "Vb_pc",   "nA3",   "VDD"),
    ("M5",  NMOS, 6, 5, "nA2",   "Vb_nc",   "nA",    "VSS"),
    ("M3",  NMOS, 6, 3, "nA",    "Vb_n",    "VSS",   "VSS"),
    # column 2 — output branch
    ("M10", PMOS, 9, 9, "nB3",   "nA2",     "VDD",   "VDD"),
    ("M8",  PMOS, 9, 7, "OUT",   "Vb_pc",   "nB3",   "VDD"),
    ("M6",  NMOS, 9, 5, "OUT",   "Vb_nc",   "nB",    "VSS"),
    ("M4",  NMOS, 9, 3, "nB",    "Vb_n",    "VSS",   "VSS"),
]

# per-device W/L — a textbook folded-cascode sizing
SIZES = {
    "M0": dict(w="4u", l="1u"),
    "M1": dict(w="3u", l="1u"),   "M2":  dict(w="3u", l="1u"),
    "M3": dict(w="1u", l="1u"),   "M4":  dict(w="1u", l="1u"),
    "M5": dict(w="1u", l="0.5u"), "M6":  dict(w="1u", l="0.5u"),
    "M7": dict(w="2u", l="0.5u"), "M8":  dict(w="2u", l="0.5u"),
    "M9": dict(w="2u", l="0.5u"), "M10": dict(w="2u", l="0.5u"),
}

# pin: name, x, y, direction
PINS = [
    ("VINP", 0, 6, "input"),    ("VINN", 0, 7, "input"),
    ("Vb_tail", 0, 9, "input"), ("Vb_pc", 0, 8, "input"),
    ("Vb_nc", 0, 5, "input"),   ("Vb_n", 0, 3, "input"),
    ("OUT", 11, 6, "output"),
    ("VDD", 6, 11, "inputOutput"), ("VSS", 6, 1, "inputOutput"),
]


def main() -> None:
    c = VirtuosoClient.from_env()
    print(f"building {LIB}/{CELL} ...")

    with c.schematic.edit(LIB, CELL) as sch:
        for name, cell, x, y, d, g, s, b in T:
            sch.add(schematic_create_inst_by_master_name(DEV_LIB, cell, "symbol", name, x, y, "R0"))
            sch.add_net_label_to_transistor(name, drain_net=d, gate_net=g, source_net=s, body_net=b)
        for name, x, y, direction in PINS:
            sch.add(schematic_create_pin(name, x, y, "R0", direction=direction))
    print("  11 devices + net labels + 9 pins placed, schChecked, saved")

    # set W/L (needs an active edit window so the device CDF resolves)
    c.execute_skill(f'geOpen(?lib "{LIB}" ?cell "{CELL}" ?view "schematic" ?mode "a")')
    for name, kw in SIZES.items():
        set_instance_params(c, name, param_filters=None, **kw)
        print(f"  sized {name}: {kw}")
    print("DONE")


if __name__ == "__main__":
    main()
