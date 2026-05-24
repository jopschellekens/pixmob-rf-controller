#!/usr/bin/env python3
"""
PixMob RF Codec: encode/decode 868 MHz OOK packets.

Encoding chain:
  Decoded 6-bit bytes → 6b/8b encode → LSB-first bit stream → 
  run-length encode (510 µs units) → add sync preamble → RAW timing data

Decoding chain:
  RAW timing data → extract sync → run-length to bits → 
  bits to bytes LSB-first → 6b/8b decode → decoded 6-bit bytes
"""

ENCODING_MAP = [
    0x21, 0x32, 0x54, 0x65, 0xa9, 0x9a, 0x6d, 0x29,
    0x56, 0x92, 0xa1, 0xb4, 0xb2, 0x84, 0x66, 0x2a,
    0x4c, 0x6a, 0xa6, 0x95, 0x62, 0x51, 0x42, 0x24,
    0x35, 0x46, 0x8a, 0xac, 0x8c, 0x6c, 0x2c, 0x4a,
    0x59, 0x86, 0xa4, 0xa2, 0x91, 0x64, 0x55, 0x44,
    0x22, 0x31, 0xb1, 0x52, 0x85, 0x96, 0xa5, 0x69,
    0x5a, 0x2d, 0x4d, 0x89, 0x45, 0x34, 0x61, 0x25,
    0x36, 0xad, 0x94, 0xaa, 0x8d, 0x49, 0x99, 0x26,
]
DECODING_MAP = {v: k for k, v in enumerate(ENCODING_MAP)}
VALID_ENCODED = set(ENCODING_MAP)

UNIT = 510  # µs per unit
SYNC_PREAMBLE = [(510, -510)] * 7 + [(510, -1020)]  # 8 bursts: 7 short gaps + 1 long gap

# Known animation parameter pairs (D5, D6)
ANIM = {
    "fade":        (36, 36),
    "blink":       (63, 8),
    "fade_in":     (41, 35),
    "fast_fade":   (9, 35),
    "nothing":     (25, 29),
    "fast_out":    (58, 35),   # observed: magenta fast fade out
}

# Known command payloads from captured RF data.
# Format: (G, R, B, anim_name) -> (D0, D5, D6, D8)
# These store the actual captured animation parameters (D5,D6),
# which may differ from the 'standard' pairs in ANIM dict.
KNOWN_COMMANDS = {
    # gold: G=51, R=57, B=0
    #   gold_fade:   D5=36, D6=19  (non-standard fade variant)
    #   gold_blink:  D5=63, D6=8   (standard blink)
    (51, 57, 0, "fade"):     (43, 36, 19, 30),
    (51, 57, 0, "blink"):    (22, 63,  8,  9),
    # red: G=0, R=57, B=0
    #   red_fade:    D5=36, D6=36  (standard fade)
    (0, 57, 0, "fade"):      (55, 36, 36, 18),
    # blue: G=16, R=0, B=57
    #   blue_fade:   D5=36, D6=36  (standard fade)
    (16, 0, 57, "fade"):     ( 0, 36, 36, 29),
    # white: G=57, R=57, B=57
    #   white_blink: D5=63, D6=8   (standard blink)
    (57, 57, 57, "blink"):   (43, 63,  8, 36),
    # turq: G=57, R=0, B=60
    #   turq_blink:  D5=6,  D6=12  (non-standard blink variant)
    (57, 0, 60, "blink"):    (29,  6, 12, 51),
    # wine: G=0, R=57, B=0 (same RGB as red, different D0/D8/animation)
    #   wine_fade_in:D5=41, D6=35  (standard fade_in)
    (0, 57, 0, "fade_in"):   ( 3, 41, 35, 44),
    # gold_fade_in: G=51,R=57,B=0, anim=fade_in (D5=41, D6=35)
    #   Trimmed trailing spurious unit, skip=1.
    (51, 57, 0, "fade_in"):  ( 7, 41, 35, 24),
    # white_fade: G=57,R=57,B=57, anim=fade (D5=36, D6=36)
    #   Trimmed trailing spurious unit, skip=1.
    (57, 57, 57, "fade"):    (18, 36, 36, 24),
    # magenta (purple): G=0,R=57,B=57 — extracted from wild_combo
    #   fast_out animation (D5=58,D6=35)
    (0, 57, 57, "fade"):     (41, 58, 35, 34),
    # none (off): G=0, R=0, B=0
    #   nothing:     D5=25, D6=29  (standard nothing)
    (0, 0, 0, "nothing"):    (17, 25, 29, 58),
}


def encode_byte(val_6bit):
    """Encode a 6-bit value (0-63) to an 8-bit 6b/8b symbol."""
    return ENCODING_MAP[val_6bit & 0x3F]


def decode_byte(enc_byte):
    """Decode an 8-bit 6b/8b symbol back to a 6-bit value. Returns None if invalid."""
    return DECODING_MAP.get(enc_byte)


def bytes_to_bits_lsb(encoded_bytes):
    """Convert list of encoded bytes to LSB-first bit stream."""
    bits = []
    for b in encoded_bytes:
        for i in range(8):
            bits.append((b >> i) & 1)
    return bits


def bits_to_bytes_lsb(bits):
    """Convert LSB-first bit stream to list of bytes."""
    result = []
    for i in range(0, len(bits), 8):
        byte = 0
        for j in range(8):
            if i + j < len(bits) and bits[i + j]:
                byte |= 1 << j
        result.append(byte)
    return result


def encode_payload_to_raw(decoded_bytes):
    """
    Convert decoded 6-bit bytes to RAW timing data (list of ON/OFF µs values).
    
    decoded_bytes: list of 9 decoded values (0-63 each)
    returns: list of ints (positive=ON, negative=OFF, in µs)
    """
    # 1: Encode each byte
    encoded = [ENCODING_MAP[d & 0x3F] for d in decoded_bytes]
    
    # 2: Convert to LSB-first bits
    bits = bytes_to_bits_lsb(encoded)
    
    # 3: Run-length encode: count consecutive 1s (ON) and 0s (OFF)
    raw = []
    i = 0
    while i < len(bits):
        if bits[i] == 1:
            count = 0
            while i < len(bits) and bits[i] == 1:
                count += 1
                i += 1
            raw.append(count * UNIT)
        else:
            count = 0
            while i < len(bits) and bits[i] == 0:
                count += 1
                i += 1
            raw.append(-count * UNIT)
    
    # 4: Prepend sync preamble
    result = []
    for on, off in SYNC_PREAMBLE:
        result.append(on)
        result.append(off)
    result.extend(raw)
    
    return result


def decode_raw_to_payload(raw_timing):
    """
    Convert RAW timing data (list of µs values) to decoded 6-bit bytes.
    
    raw_timing: list of ints (positive=ON, negative=OFF, in µs)
    returns: (decoded_bytes, skip) where decoded_bytes is list of 9 values or None per byte,
             or None if decoding fails entirely.
    """
    # 1: Round to nearest unit
    units = [round(v / UNIT) if v > 0 else round(v / UNIT) for v in raw_timing]
    
    # 2: Extract sync (first 16 entries: 8× ON=1,OFF=-1 then ON=1,OFF=-2)
    if len(units) < 16:
        return None
    for i in range(0, 14, 2):
        if not (units[i] == 1 and abs(units[i+1]) == 1):
            return None
    if not (units[14] == 1 and abs(units[15]) == 2):
        return None
    data_units = units[16:]
    
    # 3: Run-length to bits
    bits = []
    for v in data_units:
        if v > 0:
            bits.extend([1] * v)
        else:
            bits.extend([0] * (-v))
    
    # 4: Try different skip values (0-15 bits) to find best alignment
    best = None
    for skip in range(16):
        shifted = bits[skip:]
        b = bits_to_bytes_lsb(shifted)
        if len(b) < 9:
            continue
        payload = b[:9]
        valid = sum(1 for byte in payload if byte in VALID_ENCODED)
        if best is None or valid > best['valid']:
            best = {
                'skip': skip,
                'valid': valid,
                'bytes': payload,
                'decoded': [DECODING_MAP.get(byte) for byte in payload],
            }
    
    return best


def payload_to_timing_str(raw):
    """Convert raw timing list to string format (positive/negative space-separated)."""
    return ' '.join(str(v) for v in raw)


def timing_str_to_payload(timing_str):
    """Parse timing string and decode to bytes."""
    raw = [int(x) for x in timing_str.strip().split()]
    return decode_raw_to_payload(raw)


def find_nearest_known(g, r, b, anim_name):
    """
    Find the known command closest to the desired (G,R,B,anim) combo.
    Uses Euclidean distance on (G,R,B), preferring same animation as tiebreaker.
    Returns (D0, D8) from the nearest match, or None if no match.
    """
    key = (g, r, b, anim_name)
    if key in KNOWN_COMMANDS:
        d0, d5, d6, d8 = KNOWN_COMMANDS[key]
        return (d0, d8)
    
    best = None
    best_dist = 99999
    best_has_same_anim = False
    
    for (cg, cr, cb, ca), (d0, d5, d6, d8) in KNOWN_COMMANDS.items():
        dist = ((g - cg) ** 2 + (r - cr) ** 2 + (b - cb) ** 2) ** 0.5
        same = ca == anim_name
        if (best is None or
            dist < best_dist or
            (dist == best_dist and same and not best_has_same_anim)):
            best = (d0, d8)
            best_dist = dist
            best_has_same_anim = same
    
    return best


def generate_static_color_command(g, r, b, anim_name="blink"):
    """
    Generate a static color command for given G,R,B (0-63 each).
    Uses nearest known command's D0, D8 values and ANIM dict for D5,D6.
    
    Returns RAW timing data or None if generation fails.
    """
    if anim_name not in ANIM:
        return None
    d5, d6 = ANIM[anim_name]
    
    nearest = find_nearest_known(g, r, b, anim_name)
    if nearest is None:
        return None
    d0, d8 = nearest
    
    decoded = [d0, 0, g, r, b, d5, d6, 0, d8]
    return encode_payload_to_raw(decoded)


# Verification: encode known decoded bytes and compare with original raw data
def verify_codec():
    """Verify the codec by encoding known payloads and comparing with original timing."""
    print("=" * 70)
    print("CODEC VERIFICATION")
    print("=" * 70)
    
    # Known decoded payloads (from our RF analysis)
    known = {
        "gold_fade":   [43, 0, 51, 57, 0, 36, 19, 0, 30],
        "gold_blink":  [22, 0, 51, 57, 0, 63,  8, 0,  9],
        "red_fade":    [55, 0,  0, 57, 0, 36, 36, 0, 18],
        "blue_fade":   [ 0, 0, 16,  0, 57, 36, 36, 0, 29],
        "white_blink": [43, 0, 57, 57, 57, 63,  8, 0, 36],
        "turq_blink":  [29, 0, 57,  0, 60,  6, 12, 0, 51],
        "wine_fade_in":[ 3, 0,  0, 57,  0, 41, 35, 0, 44],
        "none":        [17, 0,  0,  0,  0, 25, 29, 0, 58],
        "gold_fade_in":[ 7, 0, 51, 57,  0, 41, 35, 0, 24],
        "white_fade":  [18, 0, 57, 57, 57, 36, 36, 0, 24],
    }
    
    for name, decoded in known.items():
        # Encode
        raw = encode_payload_to_raw(decoded)
        
        # Decode back
        result = decode_raw_to_payload(raw)
        
        if result is None:
            print(f"  {name:15s}: FAILED to decode own encoding")
            continue
        
        re_decoded = result['decoded']
        match = re_decoded == decoded
        
        # Show encoded bytes
        encoded = [ENCODING_MAP[d & 0x3F] for d in decoded]
        hex_str = ' '.join(f'{b:02x}' for b in encoded)
        
        if match:
            print(f"  ✓ {name:15s}: {hex_str}")
        else:
            print(f"  ✗ {name:15s}: original={decoded}")
            print(f"    decoded back: {re_decoded}")

    # Show timing data sizes
    print("\nTiming data sizes:")
    for name, decoded in known.items():
        raw = encode_payload_to_raw(decoded)
        print(f"  {name:15s}: {len(raw)} values")


if __name__ == "__main__":
    verify_codec()
    
    # Also generate some example commands
    print("\n" + "=" * 70)
    print("GENERATING NEW COMMANDS")
    print("=" * 70)
    
    # Static red with blink animation
    print("\nStatic red (G=0,R=63,B=0, blink):")
    # Use red_fade's D0=55, D8=18 since red_blink doesn't exist
    result = generate_static_color_command(0, 63, 0, "blink")
    if result:
        print(f"  RAW: {payload_to_timing_str(result)}")
        print(f"  Length: {len(result)} values")
    
    # Static green (G=63,R=0,B=0, blink)
    print("\nStatic green (G=63,R=0,B=0, blink):")
    result = generate_static_color_command(63, 0, 0, "blink")
    if result:
        print(f"  RAW: {payload_to_timing_str(result)}")
        print(f"  Length: {len(result)} values")
    
    # Static yellow (G=63,R=63,B=0, blink) 
    print("\nStatic yellow (G=63,R=63,B=0, fade):")
    result = generate_static_color_command(63, 63, 0, "fade")
    if result:
        print(f"  RAW: {payload_to_timing_str(result)}")
        print(f"  Length: {len(result)} values")
