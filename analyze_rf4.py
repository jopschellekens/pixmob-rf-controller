#!/usr/bin/env python3
"""
Final RF analysis: find correct bit alignment per sample,
extract decoded payloads, and reverse-engineer the RF protocol.
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
    # Fallback: first OFF >= 1020 marks sync end
    for i in range(1, min(24, len(values)), 2):
        if abs(values[i]) >= 1020:
            return values[:i+1], values[i+1:]
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

def find_best_skip(name, all_bits):
    """Find skip that gives most valid 6b/8b bytes for 9-byte payload."""
    best = None
    for skip in range(16):
        shifted = all_bits[skip:]
        if len(shifted) < 8:
            continue
        bytes_lsb = bits_to_bytes_lsb(shifted)
        if len(bytes_lsb) < 9:
            continue
        # Check first 9 bytes
        payload = bytes_lsb[:9]
        valid = [b for b in payload if b in DECODING_MAP]
        invalid = [b for b in payload if b not in DECODING_MAP]
        if best is None or len(valid) > best['valid']:
            best = {
                'skip': skip,
                'valid': len(valid),
                'invalid': len(invalid),
                'bytes': payload,
                'decoded': [DECODING_MAP.get(b, None) for b in payload],
            }
    return best

# Analyze all samples
results = {}
for name, data in SAMPLES.items():
    vals = parse_raw_data(data)
    sync_vals, data_vals = extract_sync(vals)
    data_units = [round(v / 510) for v in data_vals]
    all_bits = runlen_to_bits(data_units)
    best = find_best_skip(name, all_bits)
    results[name] = best

# Print summary table
print(f"{'Name':<16} {'Skip':>4} {'Bytes (encoded)':<48} {'Decoded 6-bit values':<48} {'Valid/9'}")
print("-" * 130)
for name in SAMPLES:
    r = results[name]
    if r:
        hex_str = ' '.join(f'{b:02x}' for b in r['bytes'])
        dec_str = ' '.join(f'{d:3d}' if d is not None else ' ??' for d in r['decoded'])
        print(f"{name:<16} {r['skip']:>4} {hex_str:<48} {dec_str:<48} {r['valid']}/9")
    else:
        print(f"{name:<16} {'?':>4} No valid decoding found")

# Detailed comparison of gold variants
print("\n\n========== GOLD COMPARISON ==========")
for name in ['gold_fade', 'gold_blink', 'gold_fade_in', 'gold_fast_fade']:
    r = results[name]
    if r and r['valid'] >= 8:
        print(f"\n{name}:")
        print(f"  Encoded: {' '.join(f'{b:02x}' for b in r['bytes'])}")
        print(f"  Decoded: {r['decoded']}")

# Comparison across colors (fade animation)
print("\n\n========== FADE ANIMATION COMPARISON ==========")
fades = ['gold_fade', 'red_fade', 'blue_fade']
for name in fades:
    r = results[name]
    if r:
        print(f"{name}: {r['decoded']}")

# Comparison across colors (blink animation)
print("\n\n========== BLINK ANIMATION COMPARISON ==========")
blinks = ['gold_blink', 'red_fastblink', 'white_blink', 'turq_blink']
for name in blinks:
    r = results[name]
    if r:
        print(f"{name}: {r['decoded']}")

# Try to compute checksum using IR formula on the RF packets
print("\n\n========== CHECKSUM ANALYSIS ==========")
for name in SAMPLES:
    r = results[name]
    if r and r['valid'] == 9:
        d = r['decoded']
        b = r['bytes']
        # The IR formula: sum of encoded bytes[2:] >> 2 & 0x3F, then encode
        # In our RF case, which bytes are included?
        # Try different checksum positions
        
        # Position 0 = byte0, Position 8 = checksum byte
        # Or maybe Position 8 = byte8, and Position 1 = checksum (like IR)?
        
        # Try: byte[1] is checksum, sum of byte[2:9] 
        if len(b) >= 9:
            chk_data = b[2:]  # bytes 2 through 8
            chk_sum = sum(chk_data)
            chk_raw = (chk_sum >> 2) & 0x3F
            chk_enc = ENCODING_MAP[chk_raw]
            
            # Also try: byte[8] is checksum, sum of byte[0:8]
            chk_sum2 = sum(b[:8])
            chk_raw2 = (chk_sum2 >> 2) & 0x3F
            chk_enc2 = ENCODING_MAP[chk_raw2]
            
            # Also try: without the first byte
            chk_sum3 = sum(b[1:8])
            chk_raw3 = (chk_sum3 >> 2) & 0x3F
            chk_enc3 = ENCODING_MAP[chk_raw3]
            
            # Also try: sum of ALL bytes
            chk_sum4 = sum(b)
            chk_raw4 = (chk_sum4 >> 2) & 0x3F
            chk_enc4 = ENCODING_MAP[chk_raw4]
            
            b1 = b[1] if len(b) > 1 else 0
            b8 = b[8] if len(b) > 8 else 0
            
            print(f"{name:16s}: b[1]={b1:02x} b[8]={b8:02x} "
                  f"IR(b[2:]→{chk_enc:02x}) "
                  f"IR(b[0:8]→{chk_enc2:02x}) "
                  f"IR(b[1:8]→{chk_enc3:02x}) "
                  f"IR(all→{chk_enc4:02x})")
