#!/usr/bin/env python3
"""
Generate static color RF commands for all colors from IR definitions.
Outputs Python code ready for pixmob_hackrf.py.

Strategy: For each color, find the nearest known working (G,R,B) combination
and reuse its D[0] and D[8] values. Change only the G,R,B payload bytes.
"""

from rf_codec import (
    ENCODING_MAP, UNIT, SYNC_PREAMBLE,
    encode_payload_to_raw, payload_to_timing_str, KNOWN_COMMANDS, ANIM,
)

# All IR-defined colors from the factory reset in pixmob_ir_protocol_examples.py
# Format: (name, red_8bit, green_8bit, blue_8bit)
# These are the 8 default factory colors plus white
IR_COLORS = [
    ("red",         0xBF, 0x00, 0x00),
    ("rose",        0xBF, 0x00, 0x60),
    ("purple",      0x60, 0x00, 0xBF),
    ("blue",        0x00, 0x00, 0xBF),
    ("cyan",        0x00, 0xBF, 0xBF),
    ("green",       0x00, 0xBF, 0x00),
    ("yellow",      0xBF, 0xBF, 0x00),
    ("orange",      0xBF, 0x60, 0x00),
    ("white",       0xBF, 0xBF, 0xBF),
]

# Additional colors from IR examples
EXTRA_COLORS = [
    # Eras tour colors (from pixmob_ir_protocol_examples.py)
    ("eras_warm",   0xC0, 0x64, 0x64),
    ("eras_lime",   0x98, 0xC0, 0x30),
    ("eras_teal",   0x64, 0xC0, 0xC0),
    ("eras_sky",    0x7C, 0xC0, 0xC0),
    ("eras_jade",   0x18, 0xC0, 0x18),
    ("eras_magenta",0xC0, 0x64, 0xC0),
    ("eras_royal",  0x00, 0x28, 0xC0),
    ("eras_grey",   0x38, 0x38, 0x38),
    # Full saturation colors
    ("full_red",    0xFF, 0x00, 0x00),
    ("full_lime",   0x00, 0xFF, 0x00),
    ("full_blue",   0x00, 0x00, 0xFF),
    ("full_yellow", 0xFF, 0xFF, 0x00),
    ("full_cyan",   0x00, 0xFF, 0xFF),
    ("full_magenta",0xFF, 0x00, 0xFF),
    ("full_white",  0xFF, 0xFF, 0xFF),
    # Half brightness
    ("half_red",    0x80, 0x00, 0x00),
    ("half_green",  0x00, 0x80, 0x00),
    ("half_blue",   0x00, 0x00, 0x80),
    ("half_white",  0x80, 0x80, 0x80),
    # Dim
    ("dim_red",     0x40, 0x00, 0x00),
    ("dim_blue",    0x00, 0x00, 0x40),
    ("dim_white",   0x40, 0x40, 0x40),
    # Common theme colors
    ("pink",        0xE0, 0x40, 0x80),
    ("gold",        0xD0, 0xA0, 0x00),
    ("amber",       0xFF, 0x80, 0x00),
    ("indigo",      0x40, 0x00, 0xC0),
    ("violet",      0x80, 0x00, 0xFF),
    ("turquoise",   0x00, 0xE0, 0xE0),
    ("coral",       0xFF, 0x60, 0x60),
    ("salmon",      0xE0, 0x80, 0x70),
]

def rgb12_to_6bit(r8, g8, b8):
    """Convert 8-bit RGB to 6-bit values (>>2)."""
    return (r8 >> 2) & 0x3F, (g8 >> 2) & 0x3F, (b8 >> 2) & 0x3F

def find_nearest_color(g, r, b):
    """Find the closest known color by RGB Euclidean distance."""
    best = None
    best_dist = 99999
    for (cg, cr, cb, ca), (d0, d5, d6, d8) in KNOWN_COMMANDS.items():
        dist = ((g - cg) ** 2 + (r - cr) ** 2 + (b - cb) ** 2) ** 0.5
        if dist < best_dist:
            best_dist = dist
            best = (cg, cr, cb, ca, d0, d5, d6, d8)
    return best

def generate_static_color_cmds(colors, anim_name="blink"):
    """Generate static color commands for a list of colors."""
    d5, d6 = ANIM[anim_name]
    cmds = []
    for name, r8, g8, b8 in colors:
        r6, g6, b6 = rgb12_to_6bit(r8, g8, b8)
        nearest = find_nearest_color(g6, r6, b6)
        if nearest is None:
            print(f"  SKIP {name}: no nearest color found")
            continue
        cg, cr, cb, ca, d0, _d5, _d6, d8 = nearest
        decoded = [d0, 0, g6, r6, b6, d5, d6, 0, d8]
        raw = encode_payload_to_raw(decoded)
        timing_str = payload_to_timing_str(raw)
        cmds.append((name, timing_str, decoded))
    return cmds

def escape_quotes(s):
    return s.replace("'", "\\'")

print("=" * 80)
print("GENERATING STATIC COLOR COMMANDS FOR HACKRF CONTROLLER")
print("=" * 80)

for anim_name in ["blink", "fade"]:
    print(f"\n\n=== Animation: {anim_name} ===")
    d5, d6 = ANIM[anim_name]
    print(f"Animation bytes: D5={d5}, D6={d6}")
    
    all_colors = IR_COLORS + EXTRA_COLORS
    
    print(f"\nGenerating {len(all_colors)} colors...")
    cmds = generate_static_color_cmds(all_colors, anim_name)
    
    print(f"\nSuccessfully generated {len(cmds)} commands.")
    
    # Print as a Python dict for easy pasting into pixmob_hackrf.py
    print(f"\nPython code for pixmob_hackrf.py:\n")
    print(f"# --- Auto-generated {anim_name} static colors ---")
    
    # Group by nearest source color
    by_source = {}
    for name, timing_str, decoded in cmds:
        nearest = find_nearest_color(decoded[2], decoded[3], decoded[4])
        source_key = f"{nearest[0]:02x}{nearest[1]:02x}{nearest[2]:02x}_{nearest[3]}" if nearest else "unknown"
        if source_key not in by_source:
            by_source[source_key] = []
        by_source[source_key].append((name, timing_str, decoded))
    
    for source_key, group in sorted(by_source.items()):
        # Parse the source color for comment
        parts = source_key.split('_')
        src_g = int(parts[0][:2], 16)
        src_r = int(parts[0][2:4], 16)
        src_b = int(parts[0][4:6], 16)
        src_anim = parts[1]
        print(f"\n# Source: G={src_g} R={src_r} B={src_b} anim={src_anim}")
        for name, timing_str, decoded in group:
            r6, g6, b6 = decoded[3], decoded[2], decoded[4]
            print(f"CMD_{name}_{anim_name} = [{timing_str}]")
    
    # Also print command table entries
    print(f"\n# Command table entries (add to COMMANDS):")
    for name, _, _ in cmds:
        label = name.replace('_', ' ').title()
        print(f'  {{ "{name}_{anim_name}", "{label}", "static", CMD_{name}_{anim_name}, sizeof(CMD_{name}_{anim_name})/sizeof(int16_t) }},')

# Also output the raw timing for the HackRF Python controller
print("\n\n" + "=" * 80)
print("PYTHON LIST FORMAT (for pixmob_hackrf.py)")
print("=" * 80)

for anim_name in ["blink", "fade"]:
    all_colors = IR_COLORS + EXTRA_COLORS
    cmds = generate_static_color_cmds(all_colors, anim_name)
    
    for name, timing_str, decoded in cmds[:5]:  # First 5 only as example
        r6, g6, b6 = decoded[3], decoded[2], decoded[4]
        print(f"\n# {name} ({anim_name}): R={r6} G={g6} B={b6}")
        print(f"# Decoded bytes: {decoded}")
        print(f"CMD_STATIC_{name}_{anim_name} = {timing_str}")
