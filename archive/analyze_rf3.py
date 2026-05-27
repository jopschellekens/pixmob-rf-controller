#!/usr/bin/env python3
"""
Comprehensive RF decoding analysis.
Run-length encoding: ON units = consecutive 1s, OFF units = consecutive 0s.
Then 6b/8b decode with various bit shifts to find the correct alignment.
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

SAMPLES = {
    "none": "510 -510 510 -510 510 -510 510 -510 510 -510 510 -510 510 -510 510 -1020 510 -510 510 -510 510 -510 1020 -510 510 -2040 510 -1020 510 -2040 510 -1020 510 -2040 510 -1020 510 -2040 510 -1530 1020 -1530 510 -1530 1020 -510 1020 -510 510 -2040 510 -2040 510 -510 510 -1020 510",
    "gold_fade": "510 -510 510 -510 510 -510 510 -510 510 -510 510 -510 510 -510 510 -1020 510 -510 510 -1020 510 -510 510 -510 510 -2040 510 -1020 510 -1020 510 -1530 1020 -510 1020 -510 510 -510 1020 -2040 510 -1020 510 -1530 510 -1020 1020 -510 510 -510 510 -1020 1020 -2040 510 -2040 1020 -510 510",
    "gold_blink": "510 -510 510 -510 510 -510 510 -510 510 -510 510 -510 510 -510 510 -1020 510 -510 510 -2040 510 -510 510 -2040 510 -1020 510 -1020 510 -1530 1020 -510 1020 -510 510 -510 1020 -2040 510 -1530 1020 -1020 510 -1530 1020 -510 510 -510 510 -510 510 -2040 510 -1530 510 -1020 510 -1020 510",
    "gold_fade_in": "510 -510 510 -510 510 -510 510 -510 510 -510 510 -510 510 -510 510 -1020 1020 -1020 510 -510 510 -1020 510 -2040 510 -1020 510 -1020 510 -1530 1020 -510 1020 -510 510 -510 1020 -2040 510 -1020 510 -1530 1020 -1530 510 -1530 510 -510 1020 -2040 510 -1020 510 -510 510 -510 1020 -510 510",
    "gold_fast_fade": "510 -510 510 -510 510 -510 510 -510 510 -510 510 -510 510 -510 510 -1020 510 -510 1020 -510 1020 -510 1020 -2040 510 -1020 510 -1020 510 -1530 1020 -510 1020 -510 510 -510 1020 -2040 510 -1530 510 -1020 510 -1020 510 -510 510 -1530 510 -510 1020 -2040 510 -1020 510 -1530 510 -510 510",
    "red_fade": "510 -510 510 -510 510 -510 510 -510 510 -510 510 -510 510 -510 510 -1020 1020 -510 510 -1020 510 -1020 510 -2040 510 -1020 510 -2040 510 -1020 510 -510 1020 -510 510 -510 1020 -2040 510 -1020 510 -1530 510 -1020 1020 -1530 510 -1020 1020 -2040 510 -1530 1020 -1020 510 -510 510",
    "red_fastblink": "510 -510 510 -510 510 -510 510 -510 510 -510 510 -510 510 -510 510 -1020 510 -510 1020 -510 1020 -510 1020 -2040 510 -1020 510 -2040 510 -1020 510 -510 1020 -510 510 -510 1020 -2040 510 -1530 1020 -1020 510 -1530 1020 -510 510 -510 510 -510 510 -2040 510 -2040 510 -510 510 -1020 510",
    "blue_fade": "510 -510 510 -510 510 -510 510 -510 510 -510 510 -510 510 -510 510 -1020 1020 -2040 510 -1020 510 -2040 510 -2040 1020 -1020 510 -510 510 -2040 510 -1020 510 -510 1020 -510 510 -510 1020 -1530 510 -1020 1020 -1530 510 -1020 1020 -2040 510 -2040 1020 -510 1020",
    "white_blink": "510 -510 510 -510 510 -510 510 -510 510 -510 510 -510 510 -510 510 -1020 510 -510 510 -1020 510 -510 510 -510 510 -2040 510 -1020 510 -510 1020 -510 510 -510 1020 -510 1020 -510 510 -510 1020 -510 1020 -510 510 -510 510 -510 1020 -1020 510 -1530 1020 -510 510 -510 510 -510 510 -2040 510 -1020 510 -1530 510 -1020 510",
    "white_fade": "510 -510 510 -510 510 -510 510 -510 510 -510 510 -510 510 -510 510 -1020 510 -510 1020 -1020 510 -510 1020 -2040 510 -1020 510 -510 1020 -510 510 -510 1020 -510 1020 -510 510 -510 1020 -510 1020 -510 510 -510 1020 -1530 510 -1020 1020 -1530 510 -1020 1020 -2040 510 -1020 510 -510 510 -510 1020 -510 510",
    "turq_blink": "510 -510 510 -510 510 -510 510 -510 510 -510 510 -510 510 -510 510 -1020 510 -1020 1020 -510 1020 -510 510 -2040 510 -1020 510 -510 1020 -510 510 -510 1020 -2040 510 -1020 510 -510 1020 -1530 1020 -510 1020 -510 1020 -1020 510 -1020 1020 -510 1020 -2040 510 -1020 510 -1020 510 -1530 510",
    "wine_fade_in": "510 -510 510 -510 510 -510 510 -510 510 -510 510 -510 510 -510 510 -1020 1020 -510 510 -1020 1020 -510 510 -2040 510 -1020 510 -2040 510 -1020 510 -510 1020 -510 510 -510 1020 -2040 510 -1020 510 -1530 1020 -1530 510 -1530 510 -510 1020 -2040 510 -1020 510 -510 510 -2040 510",
}

def parse_raw_data(text):
    return [int(x) for x in text.strip().split()]

def extract_sync(values):
    for sync_len in range(14, 24, 2):
        if sync_len > len(values):
            break
        all_on_ok = all(values[i] == 510 for i in range(0, sync_len, 2))
        last_off_ok = sync_len >= 2 and abs(values[sync_len-1]) >= 1020
        offs_ok = all(abs(values[i]) == 510 for i in range(1, sync_len-1, 2))
        if all_on_ok and last_off_ok and offs_ok:
            return values[:sync_len], values[sync_len:]
    return values[:16], values[16:]

def runlen_to_bits(values_units):
    bits = []
    for v in values_units:
        if v > 0:
            bits.extend([1] * v)
        else:
            bits.extend([0] * abs(v))
    return bits

def bits_to_bytes_lsb(bits):
    result = []
    for i in range(0, len(bits), 8):
        byte = 0
        for j in range(8):
            if i + j < len(bits) and bits[i + j]:
                byte |= 1 << j
        result.append(byte)
    return result

# ======== IR COMMAND CONSTRUCTION (for cross-reference) ========
def ir_encode(decoded_6bit_values):
    """Encode 6-bit values into IR encoded bytes with checksum."""
    # Byte 0 is always 0x80 (magic)
    # Byte 1 is checksum
    # Bytes 2+ are encoded payload
    encoded = [0x80, 0]  # placeholder for checksum
    for val in decoded_6bit_values:
        encoded.append(ENCODING_MAP[val])
    
    # Calculate checksum (IR formula)
    chk = sum(encoded[2:])
    chk = (chk >> 2) & 0x3F
    encoded[1] = ENCODING_MAP[chk]
    return encoded

def analyze_all():
    print(f"{'Name':<16} {'Skip':>4} {'Bytes (hex)':<40} {'Decoded 6-bit (payload)':<40} {'Notes'}")
    print("-" * 140)
    
    for name, data in SAMPLES.items():
        vals = parse_raw_data(data)
        sync_vals, data_vals = extract_sync(vals)
        data_units = [round(v / 510) for v in data_vals]
        
        # Get all bits from run-length decoding
        all_bits = runlen_to_bits(data_units)
        
        best_skip = None
        best_decoded = None
        best_bytes = None
        
        # Try skip=1 first (most promising), then skip=0, and others
        for skip in [1, 0, 2, 3, 4, 5, 6, 7]:
            shifted = all_bits[skip:]
            bytes_lsb = bits_to_bytes_lsb(shifted)
            decoded = []
            for b in bytes_lsb:
                if b in DECODING_MAP:
                    decoded.append(DECODING_MAP[b])
                else:
                    decoded.append(None)
            
            valid_count = sum(1 for d in decoded if d is not None)
            total = len(decoded)
            
            # Skip=1 with all valid is promising
            if valid_count == total and total >= 9:
                if best_skip is None:
                    best_skip = skip
                    best_decoded = decoded
                    best_bytes = bytes_lsb
        
        if best_skip is not None:
            # Color code
            is_gold = 'gold' in name
            is_red = 'red' in name
            is_blue = 'blue' in name and 'fromrand' not in name
            is_white = 'white' in name
            is_turq = 'turq' in name
            is_wine = 'wine' in name
            color = 'G' if is_gold else 'R' if is_red else 'B' if is_blue else 'W' if is_white else 'T' if is_turq else 'V' if is_wine else '?'
            
            hex_str = ' '.join(f'{b:02x}' for b in best_bytes[:12])
            dec_str = ' '.join(f'{d:2d}' if d is not None else ' ?' for d in best_decoded[:12])
            
            # Check for 0xa9 marker
            marker = "M" if 0xa9 in best_bytes else " "
            has_0 = 0 in best_decoded
            has_13 = 13 in best_decoded
            
            notes = f"{color}"
            if has_0: notes += f" has0={best_decoded.count(0)}"
            if has_13: notes += " has13"
            
            print(f"{name:<16} {best_skip:>4} {hex_str:<40} {dec_str:<40} {notes}")
        else:
            print(f"{name:<16} {'?':>4} (no valid skip found)")

analyze_all()

# ======== DETAILED COMPARISON ========
print("\n\n============== DETAILED COMPARISON ==============")
print("Comparing all gold variants to find animation bytes and checksum.\n")

# Manually extract the decoded payloads at skip=1 for all samples
def decode_with_skip(name, skip):
    vals = parse_raw_data(SAMPLES[name])
    sync_vals, data_vals = extract_sync(vals)
    data_units = [round(v / 510) for v in data_vals]
    all_bits = runlen_to_bits(data_units)
    shifted = all_bits[skip:]
    bytes_lsb = bits_to_bytes_lsb(shifted)
    decoded = [DECODING_MAP.get(b, None) for b in bytes_lsb]
    return bytes_lsb, decoded

for name in SAMPLES:
    for skip in [0, 1, 2, 3, 4]:
        bytes_lsb, decoded = decode_with_skip(name, skip)
        valid = sum(1 for d in decoded if d is not None)
        total = len(decoded)
        if valid == total and total >= 9:
            # Check if this matches known structure
            d = decoded[:11]
            non_zero_positions = [i for i, v in enumerate(d) if v != 0]
            print(f"{name:16s} skip={skip}: {' '.join(f'{b:02x}' for b in bytes_lsb[:11])}")
            print(f"  {'':16s}         {' '.join(f'{v:3d}' for v in d)} valid={valid}/{total}")
            
            # Check if byte 0 or 1 decodes to 4 (0xa9 marker)
            if len(bytes_lsb) > 0 and bytes_lsb[0] == 0xa9:
                print(f"  {'':16s}         *** Byte 0 is 0xa9 (RF marker)")
            if len(bytes_lsb) > 1 and bytes_lsb[1] == 0xa9:
                print(f"  {'':16s}         *** Byte 1 is 0xa9 (RF marker)")
