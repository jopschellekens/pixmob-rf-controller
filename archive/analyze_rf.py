#!/usr/bin/env python3
"""
Analyze PixMob RF encoding by decoding RAW_Data timing values.
Tries various bit-encoding hypotheses and applies 6b/8b decoding.
"""

import sys

# 6b -> 8b encoding table (from jamesw343/PixMob_IR)
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
# 8b -> 6b decoding map (reverse)
DECODING_MAP = {v: k for k, v in enumerate(ENCODING_MAP)}


def parse_raw_data(text):
    """Parse RAW_Data line from .sub file into list of ints."""
    values = []
    for part in text.strip().split():
        if part == 'RAW_Data:':
            continue
        values.append(int(part))
    return values


def extract_sync(values, base_unit=510):
    """Extract sync pattern (8x 510 ON/OFF + 510 ON + 1020 OFF) from data.
    Returns (sync_values, data_values) where data starts after sync.
    """
    # Sync: 8 pairs of (510, -510), then 510, -1020
    # But allow for slight variations
    
    # Try to find the sync terminator: -1020 or -1530
    # The sync is: 8x (510, -510) = 16 values
    # Then 510, -big_gap where big_gap should be -1020 or similar
    
    if len(values) < 18:
        return values, []
    
    # First 16 values should be 8x (510, -510)
    for i in range(8):
        if values[2*i] != 510 or values[2*i+1] != -510:
            # Try more flexible matching
            pass
    
    # After 16 values, we have ON=510, OFF=X where X >= 1020
    if values[16] == 510 and abs(values[17]) >= 1020:
        return values[:18], values[18:]
    
    # Try with different sync pattern lengths
    # Some captures might have slightly different sync
    for sync_len in range(14, 22, 2):
        if sync_len > len(values):
            break
        # Check if the last OFF of sync is >= 1020
        if abs(values[sync_len - 1]) >= 1020:
            return values[:sync_len], values[sync_len:]
    
    return values[:18], values[18:]


def values_to_pairs(values):
    """Convert flat values list into (on, off) pairs.
    Last incomplete pair (trailing ON) is included as (on, None).
    """
    pairs = []
    for i in range(0, len(values) - 1, 2):
        on = values[i]
        off = values[i + 1]
        if on > 0 and off < 0:
            pairs.append((on, -off))
        else:
            pairs.append((on, off))
    if len(values) % 2 == 1:
        pairs.append((values[-1], None))
    return pairs


def decode_bits_1_3(pairs):
    """Hypothesis: 510 ON + 510 OFF = '1', 510 ON + 1530 OFF = '0'
    All values rounded to nearest multiple of 510."""
    bits = []
    for on, off in pairs:
        if off is None:
            break
        on_u = round(on / 510)
        off_u = round(off / 510)
        if on_u == 1 and off_u == 1:
            bits.append(1)
        elif on_u == 1 and off_u == 3:
            bits.append(0)
        elif on_u == 2 and off_u == 2:
            bits.append(1)
        elif on_u == 1 and off_u == 2:
            bits.append(None)  # ambiguous
        elif on_u == 2 and off_u == 4:
            bits.append(None)
        else:
            bits.append(None)
    return bits


def decode_bits_pwm2(pairs):
    """Hypothesis: Each symbol is 4 time units (2040 us).
    ON time of 1 unit = '0', ON time of 3 units = '1'(but no 3x seen)
    Or: ON time of 1 = '0', ON time of 2 = '1'
    """
    bits = []
    for on, off in pairs:
        if off is None:
            break
        on_u = round(on / 510)
        off_u = round(off / 510)
        total = on_u + off_u
        if total == 2:
            # 1+1
            bits.append(1 if on_u == 1 else None)
        elif total == 3:
            # 1+2
            bits.append(0 if on_u == 1 else None)
        elif total == 4:
            # 1+3 or 2+2
            if on_u == 1 and off_u == 3:
                bits.append(0)
            elif on_u == 2 and off_u == 2:
                bits.append(1)
            else:
                bits.append(None)
        elif total == 5:
            # 1+4 or 2+3
            bits.append(None)
        elif total == 6:
            # 2+4
            bits.append(None)
        else:
            bits.append(None)
    return bits


def decode_bits_direct(pairs):
    """Hypothesis: ON duration in units directly gives bit.
    1 unit = '0', 2 units = '1'. OFF is ignored.
    """
    bits = []
    for on, off in pairs:
        on_u = round(on / 510)
        if on_u == 1:
            bits.append(0)
        elif on_u == 2:
            bits.append(1)
        else:
            bits.append(None)
    return bits


def decode_bits_off_only(pairs):
    """Hypothesis: OFF duration in units gives bit.
    1 unit = '1', 3 units = '0'. ON is ignored.
    """
    bits = []
    for on, off in pairs:
        if off is None:
            break
        off_u = round(off / 510)
        if off_u == 1:
            bits.append(1)
        elif off_u == 3:
            bits.append(0)
        elif off_u == 2:
            bits.append(None)  # ambiguous
        elif off_u == 4:
            bits.append(None)
        else:
            bits.append(None)
    return bits


def bits_to_bytes(bits, lsb_first=True):
    """Convert bit list to bytes."""
    if lsb_first:
        # Bits are LSB-first within each byte
        bytes_out = []
        for i in range(0, len(bits), 8):
            byte = 0
            for j in range(8):
                if i + j < len(bits) and bits[i + j]:
                    byte |= 1 << j
            if byte != 0 or True:
                bytes_out.append(byte)
        return bytes_out
    else:
        bytes_out = []
        for i in range(0, len(bits), 8):
            byte = 0
            for j in range(8):
                if i + j < len(bits) and bits[i + j]:
                    byte |= 1 << (7 - j)
            bytes_out.append(byte)
        return bytes_out


def decode_6b8b(encoded_bytes):
    """Decode 6b/8b encoded bytes back to 6-bit values."""
    decoded = []
    for b in encoded_bytes:
        if b in DECODING_MAP:
            decoded.append(DECODING_MAP[b])
        else:
            decoded.append(f"INV({b:02x})")
    return decoded


def encode_6b8b(decoded_values):
    """Encode 6-bit values to 6b/8b bytes."""
    return [ENCODING_MAP[v] for v in decoded_values]


def ir_checksum(encoded_bytes):
    """Calculate IR checksum for bytes[2:]."""
    checksum = sum(encoded_bytes[2:])
    checksum = (checksum >> 2) & 0x3F
    return ENCODING_MAP[checksum]


# ====================== RAW DATA SAMPLES ======================

# Single-burst captures from 868Mhz/ parent directory
SAMPLES = {
    "none": "510 -510 510 -510 510 -510 510 -510 510 -510 510 -510 510 -510 510 -1020 510 -510 510 -510 510 -510 1020 -510 510 -2040 510 -1020 510 -2040 510 -1020 510 -2040 510 -1020 510 -2040 510 -1530 1020 -1530 510 -1530 1020 -510 1020 -510 510 -2040 510 -2040 510 -510 510 -1020 510",
    
    "gold_fade": "510 -510 510 -510 510 -510 510 -510 510 -510 510 -510 510 -510 510 -1020 510 -510 510 -1020 510 -510 510 -510 510 -2040 510 -1020 510 -1020 510 -1530 1020 -510 1020 -510 510 -510 1020 -2040 510 -1020 510 -1530 510 -1020 1020 -510 510 -510 510 -1020 1020 -2040 510 -2040 1020 -510 510",
    
    "gold_blink": "510 -510 510 -510 510 -510 510 -510 510 -510 510 -510 510 -510 510 -1020 510 -510 510 -2040 510 -510 510 -2040 510 -1020 510 -1020 510 -1530 1020 -510 1020 -510 510 -510 1020 -2040 510 -1530 1020 -1020 510 -1530 1020 -510 510 -510 510 -510 510 -2040 510 -1530 510 -1020 510 -1020 510",
    
    "gold_fade_in": "510 -510 510 -510 510 -510 510 -510 510 -510 510 -510 510 -510 510 -1020 1020 -1020 510 -510 510 -1020 510 -2040 510 -1020 510 -1020 510 -1530 1020 -510 1020 -510 510 -510 1020 -2040 510 -1020 510 -1530 1020 -1530 510 -1530 510 -510 1020 -2040 510 -1020 510 -510 510 -510 1020 -510 510",
    
    "gold_fast_fade": "510 -510 510 -510 510 -510 510 -510 510 -510 510 -510 510 -510 510 -1020 510 -510 1020 -510 1020 -510 1020 -2040 510 -1020 510 -1020 510 -1530 1020 -510 1020 -510 510 -510 1020 -2040 510 -1530 510 -1020 510 -1020 510 -510 510 -1530 510 -510 1020 -2040 510 -1020 510 -1530 510 -510 510",
    
    "gold_fastfade2": "510 -510 510 -510 510 -510 510 -510 510 -510 510 -510 510 -510 510 -1020 510 -510 510 -510 510 -510 1020 -510 510 -2040 510 -1020 510 -1020 510 -1530 1020 -510 1020 -510 510 -510 1020 -2040 510 -2040 510 -510 510 -1020 510 -510 1020 -1020 510 -510 1020 -2040 510 -1530 1020 -2040 510",
    
    "red_fade": "510 -510 510 -510 510 -510 510 -510 510 -510 510 -510 510 -510 510 -1020 1020 -510 510 -1020 510 -1020 510 -2040 510 -1020 510 -2040 510 -1020 510 -510 1020 -510 510 -510 1020 -2040 510 -1020 510 -1530 510 -1020 1020 -1530 510 -1020 1020 -2040 510 -1530 1020 -1020 510 -510 510",
    
    "red_fastblink": "510 -510 510 -510 510 -510 510 -510 510 -510 510 -510 510 -510 510 -1020 510 -510 1020 -510 1020 -510 1020 -2040 510 -1020 510 -2040 510 -1020 510 -510 1020 -510 510 -510 1020 -2040 510 -1530 1020 -1020 510 -1530 1020 -510 510 -510 510 -510 510 -2040 510 -2040 510 -510 510 -1020 510",
    
    "red_fastfade": "510 -510 510 -510 510 -510 510 -510 510 -510 510 -510 510 -510 510 -1020 510 -510 510 -1020 1020 -1020 510 -2040 510 -1020 510 -2040 510 -1020 510 -510 1020 -510 510 -510 1020 -2040 510 -2040 510 -510 510 -1020 510 -510 1020 -1020 510 -510 1020 -2040 510 -1530 510 -1530 510 -510 510",
    
    "blue_fade": "510 -510 510 -510 510 -510 510 -510 510 -510 510 -510 510 -510 510 -1020 1020 -2040 510 -1020 510 -2040 510 -2040 1020 -1020 510 -510 510 -2040 510 -1020 510 -510 1020 -510 510 -510 1020 -1530 510 -1020 1020 -1530 510 -1020 1020 -2040 510 -2040 1020 -510 1020",
    
    "white_blink": "510 -510 510 -510 510 -510 510 -510 510 -510 510 -510 510 -510 510 -1020 510 -510 510 -1020 510 -510 510 -510 510 -2040 510 -1020 510 -510 1020 -510 510 -510 1020 -510 1020 -510 510 -510 1020 -510 1020 -510 510 -510 510 -510 1020 -1020 510 -1530 1020 -510 510 -510 510 -510 510 -2040 510 -1020 510 -1530 510 -1020 510",
    
    "white_fade": "510 -510 510 -510 510 -510 510 -510 510 -510 510 -510 510 -510 510 -1020 510 -510 1020 -1020 510 -510 1020 -2040 510 -1020 510 -510 1020 -510 510 -510 1020 -510 1020 -510 510 -510 1020 -510 1020 -510 510 -510 1020 -1530 510 -1020 1020 -1530 510 -1020 1020 -2040 510 -1020 510 -510 510 -510 1020 -510 510",
    
    "turq_blink": "510 -510 510 -510 510 -510 510 -510 510 -510 510 -510 510 -510 510 -1020 510 -1020 1020 -510 1020 -510 510 -2040 510 -1020 510 -510 1020 -510 510 -510 1020 -2040 510 -1020 510 -510 1020 -1530 1020 -510 1020 -510 1020 -1020 510 -1020 1020 -510 1020 -2040 510 -1020 510 -1020 510 -1530 510",
    
    "wine_fade_in": "510 -510 510 -510 510 -510 510 -510 510 -510 510 -510 510 -510 510 -1020 1020 -510 510 -1020 1020 -510 510 -2040 510 -1020 510 -2040 510 -1020 510 -510 1020 -510 510 -510 1020 -2040 510 -1020 510 -1530 1020 -1530 510 -1530 510 -510 1020 -2040 510 -1020 510 -510 510 -2040 510",
}

# Combo captures from withrepeats - extract first burst before -4500 gap
COMBO_SAMPLES = {
    "rand_red_wine": None,
    "rand_rwb": None,
    "rand_white_blink": None,
    "wine_gold_alt_fade": None,
    "blue_fade_fromrand": None,
    "red_fade_fromrand": None,
    "white_fade_fromrand": None,
}


def first_burst(raw_text):
    """Extract first burst from withrepeats data (ends at -4500 gap)."""
    vals = parse_raw_data(raw_text)
    # Find first -4500
    for i, v in enumerate(vals):
        if v == -4500:
            return vals[:i]
    return vals


def analyze(name, raw_text, decoder_func):
    """Try to decode a raw data sample."""
    vals = parse_raw_data(raw_text)
    sync_vals, data_vals = extract_sync(vals)
    pairs = values_to_pairs(data_vals)
    
    bits = decoder_func(pairs)
    valid_bits = [b for b in bits if b is not None]
    ambiguous = [b for b in bits if b is None]
    
    if len(valid_bits) < 16:
        return None
    
    bytes_lsb = bits_to_bytes(valid_bits, lsb_first=True)
    decoded = decode_6b8b(bytes_lsb)
    
    return {
        'name': name,
        'num_pairs': len(pairs),
        'num_bits_total': len(bits),
        'num_valid_bits': len(valid_bits),
        'num_ambiguous': len(ambiguous),
        'bytes_raw': bytes_lsb,
        'bytes_hex': [f"{b:02x}" for b in bytes_lsb],
        'decoded_6bit': decoded,
    }


def try_all_decoders(name, raw_text):
    """Try all decoder hypotheses and print results."""
    vals = parse_raw_data(raw_text)
    sync_vals, data_vals = extract_sync(vals)
    pairs = values_to_pairs(data_vals)
    
    print(f"\n{'='*80}")
    print(f"  {name}")
    print(f"{'='*80}")
    print(f"  Sync: {len(sync_vals)} values, Data: {len(data_vals)} values, Pairs: {len(pairs)}")
    print(f"  Raw (hex): {' '.join(f'{abs(v):04x}' if v < 0 else f'{v:04x}' for v in data_vals[:8])}...")
    
    decoders = [
        ("1:1=1, 1:3=0 (off-only)", decode_bits_1_3),
        ("ON units: 1=0, 2=1", decode_bits_direct),
        ("OFF units: 1=1, 3=0", decode_bits_off_only),
        ("PWM (2-unit total)", decode_bits_pwm2),
    ]
    
    for label, decoder_func in decoders:
        bits = decoder_func(pairs)
        valid_bits = [b for b in bits if b is not None]
        ambiguous = [b for b in bits if b is None]
        
        print(f"\n  --- {label} ---")
        print(f"  Bits: {len(valid_bits)} valid, {len(ambiguous)} ambiguous of {len(bits)} total")
        
        if len(valid_bits) >= 16:
            # Try LSB-first and MSB-first
            for lsb_name, lsb_val in [("LSB-first", True), ("MSB-first", False)]:
                bytes_out = bits_to_bytes(valid_bits, lsb_first=lsb_val)
                decoded = decode_6b8b(bytes_out)
                
                # Check for 0xa9 marker (encoded value 4)
                has_marker = 0xa9 in bytes_out
                has_encoded_marker = 4 in [d for d in decoded if isinstance(d, int)]
                
                # Print first 20 bytes
                hex_str = ' '.join(f"{b:02x}" if isinstance(b, int) else b for b in bytes_out[:15])
                dec_str = ' '.join(str(d) for d in decoded[:15])
                
                print(f"    {lsb_name}: bytes={' '.join(f'{b:02x}' for b in bytes_out[:12])}...")
                print(f"            6bit={' '.join(str(d) for d in decoded[:12])}...")
                
                if has_marker:
                    print(f"    *** CONTAINS 0xa9 marker! ***")
                if 4 in [d for d in decoded if isinstance(d, int)]:
                    print(f"    *** Decoded contains marker value 4! ***")
                    
                # Check for IR magic 0x80
                if 0x80 in bytes_out:
                    print(f"    *** CONTAINS 0x80 (IR magic)! ***")
    
    # Also print the raw pairs for manual analysis
    print(f"\n  Raw pairs (abs val / 510):")
    pair_strs = []
    for i, (on, off) in enumerate(pairs):
        on_u = round(on / 510) if on is not None else "?"
        off_u = round(off / 510) if off is not None else "?"
        pair_strs.append(f"({on_u},{off_u})")
    # Print in groups of 8
    for i in range(0, len(pair_strs), 8):
        print(f"    {' '.join(pair_strs[i:i+8])}")


def analyze_all_decoders(raw_samples):
    for name, data in raw_samples.items():
        if data:
            try_all_decoders(name, data)


if __name__ == "__main__":
    analyze_all_decoders(SAMPLES)
