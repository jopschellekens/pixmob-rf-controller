#!/usr/bin/env python3
"""
PixMob Experimental Command Explorer
Test unverified commands, CRC algorithms, and IR-to-RF color translations
without modifying the proven controller.

Usage:
    python3 pixmob_experiment.py              # Interactive mode
    python3 pixmob_experiment.py list          # List experimental commands
    python3 pixmob_experiment.py compare       # Compare IR colors with working RF
    python3 pixmob_experiment.py test-crc      # Test CRC algorithms (no TX)
    python3 pixmob_experiment.py gen-colors    # Generate experimental color commands
    python3 pixmob_experiment.py send <name>   # Send an experimental command
"""

import sys
import os
import time
import datetime
import math
import termios
import tty
import select

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from rf_codec import (
    ENCODING_MAP, DECODING_MAP, ANIM, KNOWN_COMMANDS,
    encode_payload_to_raw, payload_to_timing_str
)
from pixmob_hackrf import (
    generate_iq8, transmit, COMMANDS, CompositeCmd,
    current_freq, current_gain, amp_enabled
)

RESULTS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "experiment_results.txt")


# ====================== REFERENCE DATA ======================

WORKING_RF_COMMANDS = {
    # (name, D0, D1, G, R, B, D5, D6, D7, D8)
    "gold_fade":    [43, 0, 51, 57,  0, 36, 19, 0, 30],
    "gold_blink":   [22, 0, 51, 57,  0, 63,  8, 0,  9],
    "gold_fade_in": [ 7, 0, 51, 57,  0, 41, 35, 0, 24],
    "red_fade":     [55, 0,  0, 57,  0, 36, 36, 0, 18],
    "red_fade_in":  [ 3, 0,  0, 57,  0, 41, 35, 0, 44],
    "blue_fade":    [ 0, 0, 16,  0, 57, 36, 36, 0, 29],
    "white_blink":  [43, 0, 57, 57, 57, 63,  8, 0, 36],
    "white_fade":   [18, 0, 57, 57, 57, 36, 36, 0, 24],
    "turq_blink":   [29, 0, 57,  0, 60,  6, 12, 0, 51],
    "wine_fade_in": [ 3, 0,  0, 57,  0, 41, 35, 0, 44],
    "magenta_fade": [41, 0,  0, 57, 57, 58, 35, 0, 34],
}

ANIMATION_PAIRS = {
    "blink":     (63,  8),
    "fade":      (36, 36),
    "fade_in":   (41, 35),
    "fast_fade":  (9, 35),
    "nothing":   (25, 29),
}


# ====================== IR COLOR DEFINITIONS ======================

IR_COLORS_8BIT = [
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

EXTRA_COLORS_8BIT = [
    ("eras_warm",   0xC0, 0x64, 0x64),
    ("eras_lime",   0x98, 0xC0, 0x30),
    ("eras_teal",   0x64, 0xC0, 0xC0),
    ("eras_sky",    0x7C, 0xC0, 0xC0),
    ("eras_jade",   0x18, 0xC0, 0x18),
    ("eras_magenta",0xC0, 0x64, 0xC0),
    ("eras_royal",  0x00, 0x28, 0xC0),
    ("full_red",    0xFF, 0x00, 0x00),
    ("full_lime",   0x00, 0xFF, 0x00),
    ("full_blue",   0x00, 0x00, 0xFF),
    ("full_yellow", 0xFF, 0xFF, 0x00),
    ("full_magenta",0xFF, 0x00, 0xFF),
    ("full_white",  0xFF, 0xFF, 0xFF),
    ("gold",        0xD0, 0xA0, 0x00),
    ("amber",       0xFF, 0x80, 0x00),
    ("indigo",      0x40, 0x00, 0xC0),
    ("violet",      0x80, 0x00, 0xFF),
    ("pink",        0xE0, 0x40, 0x80),
    ("coral",       0xFF, 0x60, 0x60),
]


def rgb8_to_6(r8, g8, b8):
    return (r8 >> 2) & 0x3F, (g8 >> 2) & 0x3F, (b8 >> 2) & 0x3F


def find_nearest_rf_color(g, r, b):
    best_dist = 99999
    best = None
    for name, dec in WORKING_RF_COMMANDS.items():
        cg, cr, cb = dec[2], dec[3], dec[4]
        dist = math.sqrt((g - cg)**2 + (r - cr)**2 + (b - cb)**2)
        if dist < best_dist:
            best_dist = dist
            best = (name, dec)
    return best


# ====================== IR vs RF COMPARISON ======================

def compare_ir_with_rf():
    print("\n" + "=" * 70)
    print("  IR COLOR vs WORKING RF COMMAND COMPARISON")
    print("=" * 70)
    print(f"  {'IR Color':<16} {'IR (R,G,B) 6bit':<20} {'Nearest RF':<16} {'RF (G,R,B)':<16} {'Dist':<6} {'Match?':<8}")
    print("-" * 82)
    
    matches = []
    for name, r8, g8, b8 in IR_COLORS_8BIT + EXTRA_COLORS_8BIT:
        r6, g6, b6 = rgb8_to_6(r8, g8, b8)
        rf_name, rf_dec = find_nearest_rf_color(g6, r6, b6)
        dist = math.sqrt((g6 - rf_dec[2])**2 + (r6 - rf_dec[3])**2 + (b6 - rf_dec[4])**2)
        match_str = "SAME!" if dist < 5 else ""
        print(f"  {name:<16} ({r6:2d},{g6:2d},{b6:2d}){'':<8} {rf_name:<16} ({rf_dec[3]:2d},{rf_dec[2]:2d},{rf_dec[4]:2d}){'':<4} {dist:.1f}  {match_str}")
        if dist < 5:
            matches.append((name, r6, g6, b6, rf_name, rf_dec))
    
    print(f"\n  Close matches (dist < 5): {len(matches)}")
    for ir_name, r6, g6, b6, rf_name, rf_dec in matches:
        print(f"    {ir_name:12s} ({r6:2d},{g6:2d},{b6:2d}) -> {rf_name} ({rf_dec[3]:2d},{rf_dec[2]:2d},{rf_dec[4]:2d})")
    
    return matches


# ====================== CRC ALGORITHM IMPLEMENTATIONS ======================

ONE_BIT_CRC_TABLE = []
for val in range(64):
    crc = val
    for _ in range(6):
        if crc & 0x20:
            crc = ((crc << 1) ^ 0x25) & 0x3F
        else:
            crc = (crc << 1) & 0x3F
    ONE_BIT_CRC_TABLE.append(crc)

TWO_BIT_CRC_TABLE = []
for val in range(64):
    crc = val
    for _ in range(6):
        if crc & 0x30:
            crc = ((crc << 2) ^ 0x29) & 0x3F
        else:
            crc = (crc << 2) & 0x3F
    TWO_BIT_CRC_TABLE.append(crc)


def crc_sum_weighted(decoded, weights):
    s = 0
    for i, w in enumerate(weights):
        if i < len(decoded):
            s += decoded[i] * w
    return s % 64


def crc_xor_based(decoded, indices):
    x = 0
    for i in indices:
        x ^= decoded[i]
    return x


def crc_encoded_xor(decoded):
    encoded = [ENCODING_MAP[d & 0x3F] for d in decoded]
    x = 0
    for b in encoded[:8]:
        x ^= b
    return x % 64


def crc_encoded_sum(decoded):
    encoded = [ENCODING_MAP[d & 0x3F] for d in decoded]
    return sum(encoded[:8]) % 64


def crc_one_bit_table(decoded):
    x = 0
    for d in decoded[:8]:
        x ^= ONE_BIT_CRC_TABLE[d & 0x3F]
    return x & 0x3F


def crc_two_bit_table(decoded):
    x = 0
    for d in decoded[:8]:
        x ^= TWO_BIT_CRC_TABLE[d & 0x3F]
    return x & 0x3F


CRC_FORMULAS = {
    "D8 = sum(D[0:8]) % 64": lambda d: sum(d[:8]) % 64,
    "D8 = sum(D[2:8]) % 64": lambda d: sum(d[2:8]) % 64,
    "D8 = D0 ^ D5 ^ D6": lambda d: d[0] ^ d[5] ^ d[6],
    "D8 = D0 ^ D2 ^ D3 ^ D4 ^ D5 ^ D6": lambda d: d[0] ^ d[2] ^ d[3] ^ d[4] ^ d[5] ^ d[6],
    "D8 = (sum(D[0:8]) >> 2) & 0x3F": lambda d: (sum(d[:8]) >> 2) & 0x3F,
    "D8 = xor(ENCODED[0:8]) % 64": lambda d: crc_encoded_xor(d),
    "D8 = sum(ENCODED[0:8]) % 64": lambda d: crc_encoded_sum(d),
    "D8 = one_bit_CRC(D[0:8])": lambda d: crc_one_bit_table(d),
    "D8 = two_bit_CRC(D[0:8])": lambda d: crc_two_bit_table(d),
    "D8 = D0 + D5 + D6 % 64": lambda d: (d[0] + d[5] + d[6]) % 64,
    "D8 = D0 + 27 % 64": lambda d: (d[0] + 27) % 64,
    "D8 = D0 + 41 % 64": lambda d: (d[0] + 41) % 64,
    "D8 = D5 + D6 % 64": lambda d: (d[5] + d[6]) % 64,
    "D8 = D0 + 2*D5 + 3*D6 % 64": lambda d: (d[0] + 2*d[5] + 3*d[6]) % 64,
    "D8 = 2*D0 + D5 + D6 % 64": lambda d: (2*d[0] + d[5] + d[6]) % 64,
    "D8 = 3*D0 + 2*D5 + D6 % 64": lambda d: (3*d[0] + 2*d[5] + d[6]) % 64,
}


def test_crc_formulas():
    print("\n" + "=" * 70)
    print("  CRC FORMULA TEST — Checking which formulas predict D8 correctly")
    print("=" * 70)
    
    for fname, formula in CRC_FORMULAS.items():
        correct = 0
        total = 0
        for name, dec in WORKING_RF_COMMANDS.items():
            total += 1
            predicted = formula(dec)
            actual = dec[8]
            if predicted == actual:
                correct += 1
        pct = correct * 100 / total
        marker = "✓" if correct == total else "✗"
        print(f"  {marker} {fname:<40s}: {correct}/{total} ({pct:.0f}%)")
    
    print("\n  Testing D0 prediction (D0 from D8 and animation bytes):")
    for fname, formula in CRC_FORMULAS.items():
        correct = 0
        total = 0
        for name, dec in WORKING_RF_COMMANDS.items():
            d0_formula = lambda d, f=formula: f(d)
            total += 1
        if total > 0:
            pass

    print("\n  Best formulas will be used to generate experimental commands.")


def test_crc_vs_known():
    print("\n" + "=" * 70)
    print("  CRC: Detailed per-command prediction")
    print("=" * 70)
    
    formulas = [
        ("SUM[0:8] % 64", lambda d: sum(d[:8]) % 64),
        ("XOR D0^D5^D6", lambda d: d[0] ^ d[5] ^ d[6]),
        ("D0 + 2*D5 + 3*D6", lambda d: (d[0] + 2*d[5] + 3*d[6]) % 64),
        ("enc XOR % 64", lambda d: crc_encoded_xor(d)),
        ("SUM enc % 64", lambda d: crc_encoded_sum(d)),
        ("1-bit CRC table", lambda d: crc_one_bit_table(d)),
        ("(sum>>2)&0x3F", lambda d: (sum(d[:8]) >> 2) & 0x3F),
    ]
    
    header = f"  {'Command':<16}"
    for name, _ in formulas:
        header += f" {name[:12]:>12}"
    header += f" {'Actual':>6}"
    print(header)
    print("  " + "-" * (16 + len(formulas) * 13 + 7))
    
    for name, dec in WORKING_RF_COMMANDS.items():
        line = f"  {name:<16}"
        for fname, formula in formulas:
            pred = formula(dec)
            actual = dec[8]
            if pred == actual:
                line += f" {pred:5d}✓  "
            else:
                line += f" {pred:5d}✗  "
        line += f" {dec[8]:5d}"
        print(line)


# ====================== EXPERIMENTAL COMMAND GENERATION ======================

def generate_color_commands():
    """
    For each IR-defined color, generate RF commands using:
    1. Nearest-neighbor (G,R,B) matching for D0/D8
    2. Various animation parameters
    3. Multiple CRC formula predictions for D8
    """
    cmds = []
    
    fmt_anim = {
        "blink": (63, 8),
        "fade": (36, 36),
        "fade_in": (41, 35),
        "fast_fade": (9, 35),
    }
    
    for ir_name, r8, g8, b8 in IR_COLORS_8BIT + EXTRA_COLORS_8BIT:
        r6, g6, b6 = rgb8_to_6(r8, g8, b8)
        nearest_name, nearest_dec = find_nearest_rf_color(g6, r6, b6)
        
        for anim_name, (d5, d6) in fmt_anim.items():
            d0 = nearest_dec[0]
            crcs_to_try = [
                ("sum%64", sum([d0, 0, g6, r6, b6, d5, d6, 0]) % 64),
                ("xor_D0_D5_D6", d0 ^ d5 ^ d6),
                ("enc_xor", crc_encoded_xor([d0, 0, g6, r6, b6, d5, d6, 0, 0])),
                ("1bit_crc", crc_one_bit_table([d0, 0, g6, r6, b6, d5, d6, 0, 0])),
            ]
            
            for crc_label, d8 in crcs_to_try:
                decoded = [d0, 0, g6, r6, b6, d5, d6, 0, d8 & 0x3F]
                try:
                    raw = encode_payload_to_raw(decoded)
                    cmd_name = f"{ir_name}_{anim_name}_d0={d0}_{crc_label}"
                    cmds.append((cmd_name, raw, decoded))
                except Exception:
                    pass
    
    return cmds


def generate_d0_sweep_commands(color, anim_pair):
    """Generate commands sweeping D0 with various D8 formulas."""
    g, r, b = color
    d5, d6 = anim_pair
    cmds = []
    
    for d0 in range(0, 64, 4):
        for d8 in [d0, (d0 + 27) % 64, (d0 + 41) % 64, d0 ^ d5 ^ d6, (d0 + d5 + d6) % 64]:
            decoded = [d0, 0, g, r, b, d5, d6, 0, d8 & 0x3F]
            try:
                raw = encode_payload_to_raw(decoded)
                name = f"sweep_G{g}R{r}B{b}_d0={d0}_d8={d8 & 0x3F}"
                cmds.append((name, raw))
            except Exception:
                pass
    
    return cmds


# ====================== BRUTE FORCE RESULTS INTEGRATION ======================
# Parse the brute-force results file if it exists
BF_RESULTS_FILE = "/tmp/pixmob_bruteforce_results.txt"

def load_bruteforce_results():
    cmds = []
    if os.path.exists(BF_RESULTS_FILE):
        with open(BF_RESULTS_FILE) as f:
            for line in f:
                line = line.strip()
                if line.startswith("D0=") and "MARKED" in line:
                    try:
                        parts = {}
                        for part in line.split():
                            if "=" in part:
                                k, v = part.split("=")
                                parts[k] = int(v) if v.lstrip("-").isdigit() else v
                        d0 = parts.get("D0", 0)
                        d8 = parts.get("D8", 0)
                        g = parts.get("G", 0)
                        r = parts.get("R", 0)
                        b = parts.get("B", 0)
                        d5 = parts.get("D5", 0)
                        d6 = parts.get("D6", 0)
                        decoded = [d0, 0, g, r, b, d5, d6, 0, d8]
                        raw = encode_payload_to_raw(decoded)
                        name = f"bf_G{g}R{r}B{b}_D0{d0}_D8{d8}"
                        cmds.append((name, raw, decoded))
                    except Exception:
                        pass
    return cmds


# ====================== TEST HARNESS ======================

def _getkey(prompt="  > "):
    """Read a single keypress (y/n/s/q) without requiring Enter."""
    print(prompt, end="", flush=True)
    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        ch = sys.stdin.read(1)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)
    print(ch)
    return ch.strip().lower()


def _wait_with_interrupt(seconds, prompt=" auto-advance"):
    """Count down `seconds`, return True if user pressed any key to pause."""
    remaining = seconds
    print(f"  [{prompt}] next in {int(remaining)}s  press any key to pause", end="", flush=True)
    while remaining > 0:
        r, _, _ = select.select([sys.stdin], [], [], 0.25)
        if r:
            ch = sys.stdin.read(1)
            print()
            return True
        remaining = max(0, remaining - 0.25)
        bar = "#" * int((seconds - remaining) / seconds * 20) + "-" * (20 - int((seconds - remaining) / seconds * 20))
        print(f"\r  [{prompt}] [{bar}] {int(remaining)}s  press any key to pause", end="", flush=True)
    print()
    return False


class ExperimentHarness:
    RESULTS_FILE = RESULTS_FILE
    
    def __init__(self):
        self.working = []
        self.failing = []
    
    def send_and_test(self, name, raw_timing, repeats=3):
        iq8 = generate_iq8(raw_timing, repeats=repeats)
        print(f"\n  TX: {name}  (x{repeats})")
        transmit(iq8)
        
        print(f"  Did the bracelet respond?")
        print(f"  [y] Yes — mark as WORKING")
        print(f"  [n] No — mark as FAILING")
        print(f"  [s] Skip")
        print(f"  [q] Quit test session")
        
        while True:
            try:
                response = _getkey()
                if response == 'y':
                    self.mark_working(name, raw_timing)
                    return True
                if response == 'n':
                    self.mark_failing(name, raw_timing)
                    return False
                if response == 's':
                    return None
                if response == 'q':
                    return 'quit'
            except (EOFError, KeyboardInterrupt):
                return 'quit'
    
    def mark_working(self, name, raw_timing):
        self.working.append(name)
        self._log("WORKING", name, raw_timing)
        print(f"  ✓ Marked '{name}' as WORKING")
    
    def mark_failing(self, name, raw_timing):
        self.failing.append(name)
        self._log("FAILING", name, raw_timing)
        print(f"  ✗ Marked '{name}' as FAILING")
    
    def _log(self, status, name, raw_timing):
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        raw_str = ' '.join(str(v) for v in raw_timing)
        with open(self.RESULTS_FILE, "a") as f:
            f.write(f"[{timestamp}] {status}: {name}\n")
            f.write(f"  RAW: {raw_str}\n\n")
    
    def run_batch(self, cmds, repeats=3, auto=True):
        total = len(cmds)
        for i, item in enumerate(cmds, 1):
            if len(item) == 3:
                name, raw, decoded = item
            else:
                name, raw = item
                decoded = None
            
            print(f"\n  --- [{i}/{total}] {name} ---")
            if decoded:
                print(f"  Payload: D0={decoded[0]} G={decoded[2]} R={decoded[3]} B={decoded[4]} D5={decoded[5]} D6={decoded[6]} D8={decoded[8]}")
            
            repeats_now = 1 if auto else repeats
            iq8 = generate_iq8(raw, repeats=repeats_now)
            print(f"  TX: {name}  (x{repeats_now})")
            transmit(iq8)
            
            if auto:
                interrupted = _wait_with_interrupt(0.75)
                if interrupted:
                    try:
                        self._prompt_and_mark(name, raw)
                    except KeyboardInterrupt:
                        print("\n  Test session stopped.")
                        break
                # else silently continue to next
            else:
                result = self.send_and_test(name, raw, repeats)
                if result == 'quit':
                    print("\n  Test session stopped.")
                    break
            time.sleep(0.5)
        
        self.print_summary()
    
    def _prompt_and_mark(self, name, raw_timing):
        print(f"  Mark '{name}':")
        print(f"  [y] Yes — WORKING")
        print(f"  [n] No — FAILING")
        print(f"  [w] Wake bracelet (30s) + continue")
        print(f"  [s] Skip / continue auto")
        print(f"  [q] Quit")
        while True:
            try:
                response = _getkey()
                if response == 'y':
                    self.mark_working(name, raw_timing)
                    return
                if response == 'n':
                    self.mark_failing(name, raw_timing)
                    return
                if response == 'w':
                    print("  Waking bracelet (30s)...")
                    name0, label0, data0 = COMMANDS[0]
                    iq8 = generate_iq8(data0, repeats=int(30 * 1000 / 50))
                    transmit(iq8)
                    print("  Wake done. Continuing...")
                    return
                if response == 's':
                    return
                if response == 'q':
                    raise KeyboardInterrupt()
            except (EOFError, KeyboardInterrupt):
                raise
    
    def print_summary(self):
        print("\n" + "=" * 60)
        print("  TEST SUMMARY")
        print("=" * 60)
        print(f"  Working: {len(self.working)}")
        for name in self.working:
            print(f"    ✓ {name}")
        print(f"  Failing: {len(self.failing)}")
        for name in self.failing:
            print(f"    ✗ {name}")
        print(f"\n  Results saved to: {RESULTS_FILE}")
        
        if self.working:
            print("\n  WORKING commands — ready to add to proven list:")
            for name in self.working:
                print(f"    {name}")


# ====================== INTERACTIVE MODE ======================

def list_all():
    all_cmds = loaded_commands()
    print(f"\n  Experimental Commands Available:")
    print(f"  {'Name':<40} {'Source':<12} {'Payload':<30}")
    print("  " + "-" * 82)
    for name, raw, decoded in all_cmds:
        src = "bruteforce" if name.startswith("bf_") else "IR-match" if "_d0=" in name else "other"
        payload = f"D0={decoded[0]} G={decoded[2]} R={decoded[3]} B={decoded[4]} D8={decoded[8]}" if decoded else ""
        print(f"  {name:<40} {src:<12} {payload:<30}")


_loaded = None

def loaded_commands():
    global _loaded
    if _loaded is not None:
        return _loaded
    
    cmds = []
    cmds.extend(load_bruteforce_results())
    cmds.extend(generate_color_commands())
    cmds.extend(generate_bf_profiles())
    _loaded = cmds
    return cmds


def interactive():
    print("\n" + "=" * 60)
    print("  PixMob EXPERIMENTAL COMMAND EXPLORER")
    print("  Test unverified commands without modifying")
    print("  the proven controller.")
    print("=" * 60)
    print(f"\n  Results file: {RESULTS_FILE}")
    
    while True:
        all_cmds = loaded_commands()
        
        print(f"\n  Options ({len(all_cmds)} experimental commands loaded):")
        print("  1. Compare IR colors with working RF commands (no TX)")
        print("  2. Test CRC formulas against known commands (no TX)")
        print("  a. Auto-test all generated color commands (press any key to pause)")
        print("  m. Manual-test color commands (prompt each)")
        print("  b. Auto-test brute-force results (press any key to pause)")
        print("  j. Auto-test just-found BF profiles (press any key to pause)")
        print("  d. D0-sweep for a color (TX)")
        print("  w. Wake bracelet (30s)")
        print("  l. List all experimental commands")
        print("  q. Quit")
        
        try:
            choice = _getkey("\n  Select: ")
        except (EOFError, KeyboardInterrupt):
            print()
            break
        
        if choice == "q":
            break
        elif choice == "w":
            name, label, data = COMMANDS[0]
            iq8 = generate_iq8(data, repeats=int(30 * 1000 / 50))
            transmit(iq8)
            print("  Wake complete.")
        elif choice == "l":
            list_all()
        elif choice == "1":
            compare_ir_with_rf()
        elif choice == "2":
            test_crc_formulas()
            test_crc_vs_known()
        elif choice == "a":
            harness = ExperimentHarness()
            color_cmds = generate_color_commands()
            harness.run_batch(color_cmds, auto=True)
        elif choice == "m":
            harness = ExperimentHarness()
            color_cmds = generate_color_commands()
            harness.run_batch(color_cmds, auto=False)
        elif choice == "b":
            harness = ExperimentHarness()
            bf_cmds = load_bruteforce_results()
            if not bf_cmds:
                print(f"  No brute-force results found in {BF_RESULTS_FILE}")
                print("  Run bruteforce_d0d8.py first to generate results.")
            else:
                harness.run_batch(bf_cmds, auto=True)
        elif choice == "j":
            harness = ExperimentHarness()
            jf_cmds = generate_bf_profiles()
            if not jf_cmds:
                print("  No just-found profiles available.")
            else:
                print(f"  Testing {len(jf_cmds)} just-found BF profiles...")
                harness.run_batch(jf_cmds, auto=True)
        elif choice == "d":
            print("\n  Extended D0 sweep for a specific color/animation:")
            try:
                g = int(input("  G (0-63) [0]: ").strip() or "0")
                r = int(input("  R (0-63) [57]: ").strip() or "57")
                b = int(input("  B (0-63) [0]: ").strip() or "0")
                print("\n  Animations:")
                for i, (aname, _) in enumerate(ANIMATION_PAIRS.items(), 1):
                    print(f"  {i}. {aname}")
                anim_idx = int(input(f"  Pick 1-{len(ANIMATION_PAIRS)} [1]: ").strip() or "1") - 1
                anim_name = list(ANIMATION_PAIRS.keys())[anim_idx]
                d5, d6 = ANIMATION_PAIRS[anim_name]
                
                cmds = generate_d0_sweep_commands((g, r, b), (d5, d6))
                print(f"\n  Generated {len(cmds)} D0-sweep commands.")
                harness = ExperimentHarness()
                harness.run_batch(cmds)
            except (ValueError, IndexError):
                print("  Invalid input.")
        else:
            print("  Invalid choice.")


# ====================== JUST FOUND (Brute Force Research) ======================
"""
Research findings from brute-force analysis:

Packet structure (9 decoded bytes):
  [D0, 0, G, R, B, D5, D6, 0, D8]
    - D0/D8: 16-bit CRC split in half (D0 = first 8 bits, D8 = last 8 bits)
    - D1, D7: always 0
    - D2-D4: color (Green, Red, Blue) 6-bit each (0-63)
    - D5-D6: animation parameters

5 command bytes: G (D2), R (D3), B (D4), D5, D6
  - This is the payload that determines color + effect
  - The surrounding bytes (D0, D1, D7, D8) are framing/CRC

Brute-forced color profiles (G,R,B in hex, bookmark_color = [Blue Green Red]):
  Profile  1: G=00, R=BF, B=00  CS=BF  -> [00 00 BF] Red
  Profile  2: G=00, R=BF, B=60  CS=1F  -> [60 00 BF] Rose
  Profile  3: G=00, R=60, B=BF  CS=1F  -> [BF 00 60] Purple
  Profile  4: G=00, R=00, B=BF  CS=BF  -> [BF 00 00] Blue
  Profile  5: G=BF, R=00, B=BF  CS=7E  -> [BF BF 00] Cyan
  Profile  6: G=BF, R=00, B=00  CS=BF  -> [00 BF 00] Green
  Profile  7: G=BF, R=BF, B=00  CS=7E  -> [00 BF BF] Yellow
  Profile  8: G=60, R=BF, B=00  CS=1F  -> [00 60 BF] Orange
  Profile 16: G=BF, R=BF, B=BF  CS=3D  -> [BF BF BF] White

Checksum patterns: single channel max -> BF, two channels max -> 7E,
  mixed -> 1F, all three max -> 3D

Profile storage format (from device EEPROM analysis):
  4 bytes per profile: [Blue, Green, Red, Checksum]
  Checksum appears to be 6b/8b encoded form of a computed CRC over the 3 color bytes.
"""

# Color profiles from brute-force (8-bit hex -> 6-bit values)
# These need D0/D8 found via sweep — the CRC over GRB+D5+D6 is unknown
BRUTE_FORCE_PROFILES = [
    # (name, r6, g6, b6) — 6-bit values
    # Red:   IR=0xBF,0x00,0x00 -> 6bit=(47, 0, 0)
    ("bf_red",      47,  0,  0),
    # Rose:  IR=0xBF,0x00,0x60 -> 6bit=(47, 0,24)
    ("bf_rose",     47,  0, 24),
    # Purple:IR=0x60,0x00,0xBF -> 6bit=(24, 0,47)
    ("bf_purple",   24,  0, 47),
    # Blue:  IR=0x00,0x00,0xBF -> 6bit=( 0, 0,47)
    ("bf_blue",      0,  0, 47),
    # Cyan:  IR=0x00,0xBF,0xBF -> 6bit=( 0,47,47)
    ("bf_cyan",      0, 47, 47),
    # Green: IR=0x00,0xBF,0x00 -> 6bit=( 0,47, 0)
    ("bf_green",     0, 47,  0),
    # Yellow:IR=0xBF,0xBF,0x00 -> 6bit=(47,47, 0)
    ("bf_yellow",   47, 47,  0),
    # Orange:IR=0xBF,0x60,0x00 -> 6bit=(47,24, 0)
    ("bf_orange",   47, 24,  0),
    # White: IR=0xBF,0xBF,0xBF -> 6bit=(47,47,47)
    ("bf_white",    47, 47, 47),
]


def generate_bf_profiles(anim_name="fade"):
    """Generate D0-sweep commands for each brute-force profile.
    Sweeps D0 0-63 with multiple D8 candidates to find working CRC pairs.
    """
    if anim_name not in ANIM:
        return []
    d5, d6 = ANIM[anim_name]
    cmds = []
    for name, r6, g6, b6 in BRUTE_FORCE_PROFILES:
        for d0 in range(0, 64, 2):
            d8_candidates = [
                d0,
                (d0 + 27) % 64,
                (d0 + 41) % 64,
                d0 ^ d5 ^ d6,
                (d0 + d5 + d6) % 64,
                (2*d0 + d5 + d6) % 64,
                (d0 + 2*d5 + 3*d6) % 64,
                sum([d0, 0, g6, r6, b6, d5, d6, 0]) % 64,
                (d0 ^ d5 ^ d6 ^ g6 ^ r6 ^ b6) % 64,
                (sum(ENCODING_MAP[d] for d in [d0, 0, g6, r6, b6, d5, d6, 0]) % 64),
            ]
            for d8 in set(d8_candidates):
                decoded = [d0, 0, g6, r6, b6, d5, d6, 0, d8 & 0x3F]
                try:
                    raw = encode_payload_to_raw(decoded)
                    cmds.append((f"{name}_D0={d0}_D8={d8 & 0x3F}", raw, decoded))
                except Exception:
                    pass
    return cmds


# ====================== MAIN ======================
if __name__ == "__main__":
    if len(sys.argv) == 1:
        interactive()
    elif sys.argv[1] in ("-i", "--interactive", "interactive"):
        interactive()
    elif sys.argv[1] == "list":
        list_all()
    elif sys.argv[1] == "compare":
        compare_ir_with_rf()
    elif sys.argv[1] == "test-crc":
        test_crc_formulas()
        test_crc_vs_known()
    elif sys.argv[1] == "gen-colors":
        cmds = generate_color_commands()
        print(f"\nGenerated {len(cmds)} experimental color commands.")
        for name, raw, decoded in cmds[:10]:
            print(f"  {name}")
        if len(cmds) > 10:
            print(f"  ... and {len(cmds) - 10} more")
    elif sys.argv[1] == "send":
        if len(sys.argv) < 3:
            print("Usage: python3 pixmob_experiment.py send <name> [repeats]")
            sys.exit(1)
        name = sys.argv[2]
        repeats = int(sys.argv[3]) if len(sys.argv) > 3 else 3
        all_cmds = loaded_commands()
        for cmd_name, raw, decoded in all_cmds:
            if cmd_name == name:
                iq8 = generate_iq8(raw, repeats=repeats)
                print(f"Sending {name} x{repeats}")
                transmit(iq8)
                print("Done.")
                sys.exit(0)
        print(f"Unknown experimental command: {name}")
        sys.exit(1)
    else:
        print(f"Unknown command: {sys.argv[1]}")
        sys.exit(1)
