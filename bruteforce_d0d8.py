#!/usr/bin/env python3
"""
Brute-force D[0] and D[8] on live PixMob bracelets via HackRF.

Usage:
    # Sweep all 64 D0 values (hold D5,D6,D8 fixed):
    python3 bruteforce_d0d8.py --d5 36 --d6 36 --d8 0 --color 51,57,0 --sweep d0

    # Sweep all 64 D8 values (hold D0,D5,D6 fixed):
    python3 bruteforce_d0d8.py --d0 43 --d5 36 --d6 19 --color 51,57,0 --sweep d8

    # Full 4096 sweep (D0 x D8), which may take ~30-60 min:
    python3 bruteforce_d0d8.py --d5 36 --d6 36 --color 0,57,0 --sweep both

    # Quick: sweep D0 with K-relationship (D8 = D0 + K mod 64):
    python3 bruteforce_d0d8.py --d5 36 --d6 36 --color 0,57,0 --sweep d0 --k 27

    # Resume from a specific index:
    python3 bruteforce_d0d8.py --d5 36 --d6 36 --color 51,57,0 --sweep both --resume 100
"""

import sys
import os
import time
import argparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rf_codec import encode_payload_to_raw
from pixmob_hackrf import generate_iq8, transmit, COMMANDS, set_config, current_freq

RESULTS_FILE = "/tmp/pixmob_bruteforce_results.txt"


def get_color_groups():
    groups = {
        "gold": {
            "color": (51, 57, 0),
            "animations": {
                "fade":    {"d0": 43, "d5": 36, "d6": 19, "d8": 30, "k": 51},
                "blink":   {"d0": 22, "d5": 63, "d6":  8, "d8":  9, "k": 51},
                "fade_in": {"d0":  7, "d5": 41, "d6": 35, "d8": 24, "k": 17},
            }
        },
        "magenta": {
            "color": (0, 57, 57),
            "animations": {
                "fade": {"d0": 41, "d5": 58, "d6": 35, "d8": 34, "k": 57},
            }
        },
        "red": {
            "color": (0, 57, 0),
            "animations": {
                "fade":     {"d0": 55, "d5": 36, "d6": 36, "d8": 18, "k": 27},
                "fade_in":  {"d0":  3, "d5": 41, "d6": 35, "d8": 44, "k": 41},
                "fastblink":{"d0": -1, "d5": 63, "d6":  8, "d8": 58, "k": -1},
            }
        },
        "blue": {
            "color": (16, 0, 57),
            "animations": {
                "fade": {"d0": 0, "d5": 36, "d6": 36, "d8": 29, "k": 29},
            }
        },
        "white": {
            "color": (57, 57, 57),
            "animations": {
                "blink": {"d0": 43, "d5": 63, "d6": 8, "d8": 36, "k": 57},
                "fade":  {"d0": 18, "d5": 36, "d6": 36, "d8": 24, "k":  6},
            }
        },
        "turq": {
            "color": (57, 0, 60),
            "animations": {
                "blink": {"d0": 29, "d5": 6, "d6": 12, "d8": 51, "k": 22},
            }
        },
        "off": {
            "color": (0, 0, 0),
            "animations": {
                "nothing": {"d0": 17, "d5": 25, "d6": 29, "d8": 58, "k": 41},
            }
        },
    }
    return groups


def build_payload(d0, g, r, b, d5, d6, d8):
    return [d0 & 0x3F, 0, g & 0x3F, r & 0x3F, b & 0x3F, d5 & 0x3F, d6 & 0x3F, 0, d8 & 0x3F]


def send_payload(payload, repeats=3):
    raw = encode_payload_to_raw(payload)
    iq8 = generate_iq8(raw, repeats=repeats)
    transmit(iq8)


def log_result(d0, d8, g, r, b, d5, d6, tag=""):
    with open(RESULTS_FILE, "a") as f:
        f.write(f"D0={d0} D8={d8} G={g} R={r} B={b} D5={d5} D6={d6} {tag}\n")


def prompt_mark(d0, d8, g, r, b, d5, d6):
    """Show status and block until user responds. Returns True if marked."""
    print(f"\n  D0={d0:2d} D8={d8:2d}  (Enter=mark, s+Enter=skip, Ctrl+C=quit)", end="")
    sys.stdout.flush()
    data = sys.stdin.readline().strip().lower()
    if data == 's':
        return False
    print(f"  MARKED: D0={d0} D8={d8} (G={g} R={r} B={b} D5={d5} D6={d6})")
    log_result(d0, d8, g, r, b, d5, d6, "MARKED")
    print(f"  Saved to {RESULTS_FILE}")
    return True


def sweep_d0(g, r, b, d5, d6, d8=None, k=None, start=0, end=64):
    if d8 is None and k is None:
        print("ERROR: must provide --d8 or --k for D0 sweep")
        return

    for d0 in range(start, end):
        cur_d8 = d8 if d8 is not None else (d0 + k) & 0x3F
        payload = build_payload(d0, g, r, b, d5, d6, cur_d8)
        send_payload(payload)

        try:
            prompt_mark(d0, cur_d8, g, r, b, d5, d6)
        except KeyboardInterrupt:
            print(f"\n  Stopped at D0={d0}")
            return

    print(f"\n  D0 sweep complete ({end-start} values)")


def sweep_d8(g, r, b, d5, d6, d0, start=0, end=64):
    for d8 in range(start, end):
        payload = build_payload(d0, g, r, b, d5, d6, d8)
        send_payload(payload)

        try:
            prompt_mark(d0, d8, g, r, b, d5, d6)
        except KeyboardInterrupt:
            print(f"\n  Stopped at D8={d8}")
            return

    print(f"\n  D8 sweep complete ({end-start} values)")


def sweep_both(g, r, b, d5, d6, start=0):
    total = 64 * 64
    count = 0
    for d0 in range(64):
        for d8 in range(64):
            count += 1
            if count < start:
                continue

            payload = build_payload(d0, g, r, b, d5, d6, d8)
            send_payload(payload)

            pct = count * 100 / total
            print(f"\n  [{count}/{total} ({pct:.0f}%)] D0={d0:2d} D8={d8:2d}", end="")
            sys.stdout.flush()

            try:
                prompt_mark(d0, d8, g, r, b, d5, d6)
            except KeyboardInterrupt:
                print(f"\n  Stopped at D0={d0} D8={d8}")
                print(f"  Resume with: --resume {count}")
                return

    print(f"\n  Full sweep complete!")


def preset_menu():
    groups = get_color_groups()
    print("\n  Select a known command as starting point:")
    cmds = []
    for gname, gdata in groups.items():
        for aname, adata in gdata["animations"].items():
            label = f"{gname}_{aname}"
            cmds.append((label, gdata["color"], adata))
    cmds.append(("custom", None, None))

    for i, (label, _, _) in enumerate(cmds, 1):
        print(f"  {i:2d}. {label}")
    print(f"  q. Quit")

    try:
        choice = input(f"\n  Pick 1-{len(cmds)} or q: ").strip().lower()
        if choice == "q":
            return None, None, None
        idx = int(choice) - 1
        if 0 <= idx < len(cmds):
            label, color, anim = cmds[idx]
            if color is None:
                return None, None, None
            return label, color, anim
    except (ValueError, IndexError):
        pass
    return None, None, None


def interactive_bruteforce():
    print("\n" + "=" * 60)
    print("  PixMob D[0]/D[8] BRUTE FORCE TOOL")
    print("  Place bracelet near the HackRF antenna")
    print("  Press Enter when you see a color change")
    print("  Type 's' + Enter to skip (no response)")
    print("=" * 60)

    label, color, anim = preset_menu()
    if label is None:
        print("\n  Enter custom parameters:")
        try:
            color_input = input("  G,R,B (comma separated) [51,57,0]: ").strip() or "51,57,0"
            g, r, b = [int(x) for x in color_input.split(",")]
            d5 = int(input("  D5 [36]: ").strip() or "36")
            d6 = int(input("  D6 [36]: ").strip() or "36")
            d0 = input("  D0 [enter to sweep]: ").strip()
            d8 = input("  D8 [enter to sweep]: ").strip()
            k = input("  K (D8-D0 mod 64) [enter to skip]: ").strip()
        except (ValueError, IndexError):
            print("  Invalid input.")
            return
    else:
        g, r, b = color
        d5 = anim["d5"]
        d6 = anim["d6"]
        d0 = anim["d0"]
        d8 = anim["d8"]
        k = anim.get("k")
        print(f"\n  Starting from: {label}")
        print(f"  Known: D0={d0} D8={d8} G={g} R={r} B={b} D5={d5} D6={d6} K={k}")

    d0_val = int(d0) if d0 else None
    d8_val = int(d8) if d8 else None
    k_val = int(k) if k else None

    print(f"\n  Sweep strategy:")
    print(f"  1. Sweep D0 (try all 64 D0 values)")
    print(f"  2. Sweep D8 (try all 64 D8 values)")
    print(f"  3. Sweep both D0xD8 (all 4096 combos)")
    print(f"  4. Sweep D0 using K-relationship (D8 = D0+K mod 64)")

    try:
        strategy = input(f"\n  Pick 1-4: ").strip()
    except (EOFError, KeyboardInterrupt):
        print()
        return

    try:
        wake = input("  Send wake first? (y/n) [y]: ").strip().lower() or "y"
        if wake == "y":
            print("\n  Sending wake (30s)...")
            name, label, data = COMMANDS[0]
            iq8 = generate_iq8(data, repeats=int(30 * 1000 / 50))
            transmit(iq8)
            time.sleep(1)
            print("  Wake complete.\n")
    except KeyboardInterrupt:
        print()
        return

    if strategy == "1":
        if d8_val is None and k_val is None:
            print("  Need D8 or K to sweep D0. Setting D8=0.")
            d8_val = 0
        sweep_d0(g, r, b, d5, d6, d8=d8_val, k=k_val)
    elif strategy == "2":
        if d0_val is None:
            print("  Need D0 to sweep D8. Setting D0=0.")
            d0_val = 0
        sweep_d8(g, r, b, d5, d6, d0_val)
    elif strategy == "3":
        sweep_both(g, r, b, d5, d6)
    elif strategy == "4":
        if k_val is None:
            print("  Need K value. Computing from known or setting to 0.")
            k_val = 0
        sweep_d0(g, r, b, d5, d6, d8=None, k=k_val)
    else:
        print("  Invalid strategy.")


if __name__ == "__main__":
    from rf_codec import ENCODING_MAP

    parser = argparse.ArgumentParser(description="Brute-force D0/D8 on PixMob bracelets")
    parser.add_argument("--color", help="G,R,B (comma separated, e.g. 51,57,0)")
    parser.add_argument("--d0", type=int, help="Fixed D0 value")
    parser.add_argument("--d8", type=int, help="Fixed D8 value")
    parser.add_argument("--d5", type=int, default=36, help="D5 (animation param 1)")
    parser.add_argument("--d6", type=int, default=36, help="D6 (animation param 2)")
    parser.add_argument("--k", type=int, help="K = D8 - D0 mod 64 (for K-relationship sweep)")
    parser.add_argument("--sweep", choices=["d0", "d8", "both"], default="d0",
                        help="What to sweep")
    parser.add_argument("--start", type=int, default=0, help="Starting index")
    parser.add_argument("--end", type=int, default=64, help="Ending index (exclusive)")
    parser.add_argument("--resume", type=int, default=0, help="Resume from count")
    parser.add_argument("--wake", action="store_true", help="Send wake before sweep")
    parser.add_argument("--interactive", "-i", action="store_true", help="Interactive mode")

    args = parser.parse_args()

    if args.interactive or len(sys.argv) == 1:
        interactive_bruteforce()
        sys.exit(0)

    if args.color:
        try:
            g, r, b = [int(x) for x in args.color.split(",")]
        except ValueError:
            print("ERROR: --color must be G,R,B (e.g. 51,57,0)")
            sys.exit(1)
    else:
        print("ERROR: --color is required")
        sys.exit(1)

    if args.wake:
        print("Sending wake (30s)...")
        name, label, data = COMMANDS[0]
        iq8 = generate_iq8(data, repeats=int(30 * 1000 / 50))
        transmit(iq8)
        time.sleep(1)
        print("Wake complete.\n")

    if args.sweep == "d0":
        sweep_d0(g, r, b, args.d5, args.d6, d8=args.d8, k=args.k,
                 start=args.start, end=args.end)
    elif args.sweep == "d8":
        if args.d0 is None:
            print("ERROR: --d0 required for D8 sweep")
            sys.exit(1)
        sweep_d8(g, r, b, args.d5, args.d6, args.d0,
                 start=args.start, end=args.end)
    elif args.sweep == "both":
        sweep_both(g, r, b, args.d5, args.d6, start=args.resume)
    else:
        print("ERROR: unknown sweep type")
        sys.exit(1)
