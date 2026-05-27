#!/usr/bin/env python3
"""
Second attempt: RF encoding uses run-length encoding.
ON time (÷510) = number of consecutive 1 bits.
OFF time (÷510) = number of consecutive 0 bits.
Then decode 6b/8b LSB-first.
"""
import sys

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

def parse_raw_data(text):
    return [int(x) for x in text.strip().split()]

def extract_sync(values):
    """Find sync: 8x(510,-510) or similar, then 510 + longer OFF."""
    # Try different sync lengths
    for sync_len in range(14, 24, 2):
        if sync_len > len(values):
            break
        # Check: all ON values in sync should be 510 (1 unit)
        all_on_ok = all(values[i] == 510 for i in range(0, sync_len, 2))
        # Last OFF should be >= 1020 (2 units)
        last_off_ok = sync_len >= 2 and abs(values[sync_len-1]) >= 1020
        # Other OFF values should be 510
        offs_ok = all(abs(values[i]) == 510 for i in range(1, sync_len-1, 2))
        if all_on_ok and last_off_ok and offs_ok:
            return values[:sync_len], values[sync_len:]
    # Fallback: just use 16 as sync
    return values[:16], values[16:]

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

def runlen_to_bits(values_units):
    """Convert run-length units to bits:
    Positive = number of consecutive 1s
    Negative = number of consecutive 0s
    """
    bits = []
    for v in values_units:
        if v > 0:
            bits.extend([1] * v)
        else:
            bits.extend([0] * abs(v))
    return bits

def bits_to_bytes_lsb(bits):
    """Convert bits to bytes, LSB-first."""
    result = []
    for i in range(0, len(bits), 8):
        byte = 0
        for j in range(8):
            if i + j < len(bits) and bits[i + j]:
                byte |= 1 << j
        result.append(byte)
    return result

def decode_6b8b(bytes_list):
    """Decode 6b/8b encoded bytes to 6-bit values."""
    decoded = []
    for b in bytes_list:
        if b in DECODING_MAP:
            decoded.append(DECODING_MAP[b])
        else:
            decoded.append(None)
    return decoded

# IR checksum calculation
def ir_checksum(encoded_bytes):
    """Calculate IR checksum for the RF payload.
    IR: sum(encoded[2:]) >> 2 & 0x3F, then encode.
    """
    if len(encoded_bytes) < 3:
        return None
    chk = sum(encoded_bytes[2:])
    chk = (chk >> 2) & 0x3F
    return ENCODING_MAP[chk]

def analyze(name, raw_text):
    vals = parse_raw_data(raw_text)
    sync_vals, data_vals = extract_sync(vals)
    
    print(f"\n{'='*80}")
    print(f"  {name}")
    print(f"{'='*80}")
    print(f"  Sync: {len(sync_vals)} vals, Data: {len(data_vals)} vals")
    
    # Convert data values to units of 510
    data_units = [round(v / 510) for v in data_vals]
    print(f"  Run-lengths: {data_units}")
    
    # Decode run-length to bits
    bits = runlen_to_bits(data_units)
    print(f"  Bits ({len(bits)}): {''.join(str(b) for b in bits)}")
    
    # Convert to bytes LSB-first
    bytes_lsb = bits_to_bytes_lsb(bits)
    print(f"  Bytes: {' '.join(f'{b:02x}' for b in bytes_lsb)}")
    
    # Decode 6b/8b
    decoded = decode_6b8b(bytes_lsb)
    valid_decoded = [d for d in decoded if d is not None]
    print(f"  6-bit decoded: {' '.join(str(d) if d is not None else '??' for d in decoded)}")
    print(f"  Valid 6-bit values: {len(valid_decoded)}/{len(decoded)}")
    
    # Check for known patterns
    has_0xa9 = 0xa9 in bytes_lsb
    has_0x80 = 0x80 in bytes_lsb
    if has_0xa9:
        print(f"  *** CONTAINS 0xa9 (RF marker)")
    if has_0x80:
        print(f"  *** CONTAINS 0x80 (IR magic)")
    
    cksum = ir_checksum(bytes_lsb)
    if cksum is not None:
        print(f"  IR checksum byte[1] would be: {cksum:02x}")
        if len(bytes_lsb) > 1:
            match = "MATCH" if bytes_lsb[1] == cksum else "MISMATCH"
            print(f"  Actual byte[1] = {bytes_lsb[1]:02x} vs IR checksum = {cksum:02x} ({match})")
    
    # Also try skipping the first bit (possible bit alignment issue)
    for skip in [0, 1, 2, 3, 4, 5, 6, 7]:
        shifted = bits[skip:]
        bytes_shifted = bits_to_bytes_lsb(shifted)
        decoded_shifted = decode_6b8b(bytes_shifted)
        valid_shifted = [d for d in decoded_shifted if d is not None]
        if valid_shifted:
            nond = sum(1 for d in decoded_shifted if d is not None)
            if nond >= 6:  # At least 6 valid 6-bit values
                print(f"  [skip={skip}] Bytes: {' '.join(f'{b:02x}' for b in bytes_shifted[:10])}")
                print(f"            Decoded: {' '.join(str(d) if d is not None else '??' for d in decoded_shifted[:10])} (valid={nond})")
                
                # Check for constant 13
                has_13 = 13 in decoded_shifted
                has_51 = 51 in decoded_shifted or 37 in decoded_shifted or 7 in decoded_shifted or 28 in decoded_shifted or 20 in decoded_shifted
                if has_13:
                    print(f"            *** Contains 13 (constant)!")
                if has_51:
                    print(f"            *** Contains known animation value!")

for name, data in SAMPLES.items():
    analyze(name, data)
