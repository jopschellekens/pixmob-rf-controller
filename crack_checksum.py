#!/usr/bin/env python3
"""Brute-force the RF checksum formula using all 9-byte-valid samples."""
from itertools import combinations

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

# All samples with 9/9 valid decoded bytes at skip=1 (encoded bytes then decoded)
SAMPLES = {
    "gold_fade":   ("52 21 89 ad 21 91 95 21 2c", [43, 0, 51, 57, 0, 36, 19, 0, 30]),
    "gold_blink":  ("42 21 89 ad 21 26 56 21 92", [22, 0, 51, 57, 0, 63,  8, 0,  9]),
    "red_fade":    ("25 21 21 ad 21 91 91 21 a6", [55, 0,  0, 57, 0, 36, 36, 0, 18]),
    "blue_fade":   ("21 21 4c 21 ad 91 91 21 6c", [ 0, 0, 16,  0, 57, 36, 36, 0, 29]),
    "white_blink": ("52 21 ad ad ad 26 56 21 91", [43, 0, 57, 57, 57, 63,  8, 0, 36]),
    "turq_blink":  ("6c 21 ad 21 8d 6d b2 21 89", [29, 0, 57,  0, 60,  6, 12, 0, 51]),
    "wine_fade_in":("65 21 21 ad 21 31 a2 21 85", [ 3, 0,  0, 57,  0, 41, 35, 0, 44]),
    "none":        ("6a 21 21 21 21 46 6c 21 94", [17, 0,  0,  0,  0, 25, 29, 0, 58]),
}

def test_formula(name, formula_fn, expected, verbose=False):
    """Test a checksum formula against all samples. Returns list of (name, actual, expected, ok)."""
    results = []
    for n, (enc_hex, dec) in SAMPLES.items():
        enc = [int(x, 16) for x in enc_hex.split()]
        actual = DECODING_MAP.get(formula_fn(enc, dec), -1)
        ok = actual == expected[0] if callable(expected) else actual == expected
        results.append((n, actual, expected[0] if not callable(expected) else '?', ok))
    return results

def pass_rate(results):
    return sum(1 for _, _, _, ok in results if ok) / len(results)

print("=" * 80)
print("CHECKSUM BRUTE FORCE: testing various formulas")
print("=" * 80)

print("\n--- Testing formulas on ENCODED bytes ---")

# Get expected B[8] values
expected_b8 = {}
expected_d8 = {}
for n, (enc_hex, dec) in SAMPLES.items():
    enc = [int(x, 16) for x in enc_hex.split()]
    expected_b8[n] = enc[8]
    expected_d8[n] = dec[8]

# Try simple sum + mod operations on encoded bytes
print("\n1a. B[8] = ENCODING_MAP[sum(B[0:8]) mod 64]")
for n, (enc_hex, dec) in SAMPLES.items():
    enc = [int(x, 16) for x in enc_hex.split()]
    s = sum(enc[:8])
    pred = ENCODING_MAP[s % 64]
    ok = "✓" if pred == enc[8] else "✗"
    print(f"  {n:15s}: sum={s:3d}, {s}%64={s%64:2d}, pred={pred:02x}, actual={enc[8]:02x} {ok}")

print("\n1b. B[8] = ENCODING_MAP[(sum(B[0:8]) >> 2) & 0x3F] (IR formula)")
for n, (enc_hex, dec) in SAMPLES.items():
    enc = [int(x, 16) for x in enc_hex.split()]
    s = sum(enc[:8])
    pred = ENCODING_MAP[(s >> 2) & 0x3F]
    ok = "✓" if pred == enc[8] else "✗"
    print(f"  {n:15s}: sum={s:3d}, ({s}>>2)&0x3F={(s>>2)&0x3F:2d}, pred={pred:02x}, actual={enc[8]:02x} {ok}")

print("\n1c. B[8] = ENCODING_MAP[sum(B[2:8]) mod 64]")
for n, (enc_hex, dec) in SAMPLES.items():
    enc = [int(x, 16) for x in enc_hex.split()]
    s = sum(enc[2:8])
    pred = ENCODING_MAP[s % 64]
    ok = "✓" if pred == enc[8] else "✗"
    print(f"  {n:15s}: sum(B[2:8])={s:3d}, %64={s%64:2d}, pred={pred:02x}, actual={enc[8]:02x} {ok}")

print("\n1d. B[8] = ENCODING_MAP[XOR of B[0:8] mod 64]")
for n, (enc_hex, dec) in SAMPLES.items():
    enc = [int(x, 16) for x in enc_hex.split()]
    x = 0
    for b in enc[:8]:
        x ^= b
    pred = ENCODING_MAP[x % 64]
    ok = "✓" if pred == enc[8] else "✗"
    print(f"  {n:15s}: xor={x:02x}, %64={x%64:2d}, pred={pred:02x}, actual={enc[8]:02x} {ok}")

print("\n1e. Simple XMOD (xor of nibble-pairs, then mod 64, then encode)")
# For each byte: (high_nibble ^ low_nibble), sum all up, mod 64
for n, (enc_hex, dec) in SAMPLES.items():
    enc = [int(x, 16) for x in enc_hex.split()]
    nibble_xor_sum = sum(((b >> 4) ^ (b & 0x0f)) for b in enc[:8])
    pred_index = nibble_xor_sum % 64
    pred = ENCODING_MAP[pred_index]
    ok = "✓" if pred == enc[8] else "✗"
    print(f"  {n:15s}: nibble_xor_sum={nibble_xor_sum:2d}, %64={pred_index:2d}, pred={pred:02x}, actual={enc[8]:02x} {ok}")

print("\n1f. Simple sum of nibbles (hi_nibble + lo_nibble)")
for n, (enc_hex, dec) in SAMPLES.items():
    enc = [int(x, 16) for x in enc_hex.split()]
    nibble_sum = sum(((b >> 4) + (b & 0x0f)) for b in enc[:8])
    pred_index = nibble_sum % 64
    pred = ENCODING_MAP[pred_index]
    ok = "✓" if pred == enc[8] else "✗"
    print(f"  {n:15s}: nibble_sum={nibble_sum:2d}, %64={pred_index:2d}, pred={pred:02x}, actual={enc[8]:02x} {ok}")

# Now try formulas on DECODED values
print("\n\n--- Testing formulas on DECODED 6-bit values ---")

print("\n2a. D[8] = sum(D[0:8]) mod 64 (raw)")
for n, (enc_hex, dec) in SAMPLES.items():
    d = DECODING_MAP
    raw_sum = sum(dec[:8])
    pred = raw_sum % 64
    ok = "✓" if pred == dec[8] else "✗"
    print(f"  {n:15s}: sum={raw_sum:3d}, %64={pred:2d}, actual={dec[8]:2d} {ok}")

print("\n2b. D[8] = (sum(D[0:8]) >> 2) & 0x3F")
for n, (enc_hex, dec) in SAMPLES.items():
    raw_sum = sum(dec[:8])
    pred = (raw_sum >> 2) & 0x3F
    ok = "✓" if pred == dec[8] else "✗"
    print(f"  {n:15s}: sum={raw_sum:3d}, >>2=%{(raw_sum>>2)&0x3F:2d}, actual={dec[8]:2d} {ok}")

print("\n2c. D[8] = sum(D[2:8]) mod 64")
for n, (enc_hex, dec) in SAMPLES.items():
    s = sum(dec[2:8])
    pred = s % 64
    ok = "✓" if pred == dec[8] else "✗"
    print(f"  {n:15s}: sum(D[2:8])={s:3d}, %64={pred:2d}, actual={dec[8]:2d} {ok}")

print("\n2d. D[8] = (sum(D[2:8]) >> 2) & 0x3F")
for n, (enc_hex, dec) in SAMPLES.items():
    s = sum(dec[2:8])
    pred = (s >> 2) & 0x3F
    ok = "✓" if pred == dec[8] else "✗"
    print(f"  {n:15s}: sum(D[2:8])={s:3d}, >>2={(s>>2)&0x3F:2d}, actual={dec[8]:2d} {ok}")

print("\n2e. D[8] = sum(D[0:8]) & 0x3F (no shift)")
for n, (enc_hex, dec) in SAMPLES.items():
    s = sum(dec[:8])
    pred = s & 0x3F
    ok = "✓" if pred == dec[8] else "✗"
    print(f"  {n:15s}: sum={s:3d}, &0x3F={pred:2d}, actual={dec[8]:2d} {ok}")

print("\n2f. D[8] = D[0] + D[5] + D[6] mod 64")
for n, (enc_hex, dec) in SAMPLES.items():
    s = dec[0] + dec[5] + dec[6]
    pred = s % 64
    ok = "✓" if pred == dec[8] else "✗"
    print(f"  {n:15s}: {dec[0]}+{dec[5]}+{dec[6]}={s:3d}, %64={pred:2d}, actual={dec[8]:2d} {ok}")

print("\n2g. D[8] = D[0] ^ D[5] ^ D[6]")
for n, (enc_hex, dec) in SAMPLES.items():
    pred = dec[0] ^ dec[5] ^ dec[6]
    ok = "✓" if pred == dec[8] else "✗"
    print(f"  {n:15s}: {dec[0]}^{dec[5]}^{dec[6]}={pred:2d}, actual={dec[8]:2d} {ok}")

# Try weighted sum
print("\n\n--- Weighted sums on decoded values ---")

def try_weights(weights, formula_name):
    """Try D[8] = sum(w_i * D[i]) mod 64 for given weights."""
    print(f"\n3{formula_name}. D[8] = sum(w_i * D[i]) mod 64")
    for n, (enc_hex, dec) in SAMPLES.items():
        s = sum(w * dec[i] for i, w in enumerate(weights) if i < 8)
        pred = s % 64
        ok = "✓" if pred == dec[8] else "✗"
        print(f"  {n:15s}: weighted_sum={s:3d}, %64={pred:2d}, actual={dec[8]:2d} {ok}")

try_weights([1,1,1,1,1,1,1,1], "a (all 1)")
try_weights([1,0,1,1,1,1,1,0], "b (excl pos 1,7)")
try_weights([0,0,1,1,1,1,1,0], "c (pos 2-6 only)")
try_weights([1,0,0,0,0,1,1,0], "d (pos 0,5,6 only)")

# Check what coefficients would solve for each pair of samples
print("\n\n--- Trying to find consistent linear coefficients ---")
print("If D8 = (sum(coeff_i * D[i]) mod 64), solving for coeff_i...\n")

# For each pair of columns, check if there's a consistent coefficient
# D8 = a * D0 + b * D5 + c * D6 (mod 64) is a simple model to test
# since D1, D7 are always 0 and D2-D4 are constant within color groups

# gold_fade: 43a + 36b + 19c ≡ 30 (mod 64)
# gold_blink: 22a + 63b +  8c ≡  9 (mod 64)
# red_fade:   55a + 36b + 36c ≡ 18 (mod 64)
# white_blink: 43a + 63b +  8c ≡ 36 (mod 64)

# From gold_fade and gold_blink (same color, diff animation):
# (43-22)a + (36-63)b + (19-8)c ≡ 30-9 (mod 64)
# 21a - 27b + 11c ≡ 21 (mod 64)

# From gold_fade and red_fade (diff color, same animation):
# (43-55)a + (51-0)d + (36-36)b + (19-36)c ≡ 30-18 (mod 64)
# -12a + 51d + 0b - 17c ≡ 12 (mod 64)

# This is getting complex. Let me just brute force it.

print("Brute-forcing a,b,c in D8 = (a*D0 + b*D5 + c*D6 + d*D2 + e*D3 + f*D4) mod 64...")
print(f"Using 6 variables, 8 equations, searching mod 64 space...")
print()

# Try simpler: D8 = (a*D0 + b*animation_sum) mod 64
# where animation_sum = D5 + D6
print("4a. D8 = (a*D0 + b*(D5+D6)) mod 64")
hits = []
for a in range(64):
    for b in range(64):
        ok_count = 0
        results = []
        for n, (enc_hex, dec) in SAMPLES.items():
            pred = (a * dec[0] + b * (dec[5] + dec[6])) % 64
            if pred == dec[8]:
                ok_count += 1
                results.append(f"{n}")
        if ok_count == 8:
            hits.append((a, b))
            print(f"  ✓ a={a}, b={b}: ALL MATCH")
if not hits:
    print("  No exact match found for all 8 samples")

print()
print("4b. D8 = (a*D0 + b*D5 + c*D6) mod 64")
hits = []
for a in range(64):
    for b in range(64):
        for c in range(64):
            ok_count = 0
            for n, (enc_hex, dec) in SAMPLES.items():
                pred = (a * dec[0] + b * dec[5] + c * dec[6]) % 64
                if pred == dec[8]:
                    ok_count += 1
            if ok_count == 8:
                hits.append((a,b,c))
if len(hits) > 0 and len(hits) <= 5:
    for a,b,c in hits:
        print(f"  ✓ a={a}, b={b}, c={c}: ALL {len(hits)} solutions")
elif len(hits) > 5:
    print(f"  Found {len(hits)} solutions (too many to list all)")
elif len(hits) == 0:
    print("  No exact match found")

    # Check with D2 as well
    print()
    print("4c. D8 = (a*D0 + b*D5 + c*D6 + d*D2) mod 64")
    hits = []
    for a in range(64):
        for b in range(64):
            for c in range(64):
                for d in range(64):
                    ok_count = 0
                    for n, (enc_hex, dec) in SAMPLES.items():
                        pred = (a * dec[0] + b * dec[5] + c * dec[6] + d * dec[2]) % 64
                        if pred == dec[8]:
                            ok_count += 1
                    if ok_count == 8:
                        hits.append((a,b,c,d))
                        break
                if len(hits) > 0:
                    break
            if len(hits) > 0:
                break
        if len(hits) > 0:
            break
    if len(hits) > 0:
        print(f"  ✓ Found: {hits[0]}")
    else:
        print("  No exact match found")

# Try: maybe D8 = xor of specific encoded bytes, not decoded values
print()
print("5. B[8] as XOR of specific encoded byte pairs:")
for n, (enc_hex, dec) in SAMPLES.items():
    enc = [int(x, 16) for x in enc_hex.split()]
    # XOR of all encoded bytes
    x_all = 0
    for b in enc[:8]:
        x_all ^= b
    
    # Sum of all encoded bytes
    s_all = sum(enc[:8])
    
    # The check we're looking for: what function of enc gives enc[8]?
    x_mod = x_all % 64
    s_mod = s_all % 64
    print(f"  {n:15s}: XOR={x_all:02x}, XOR%64={x_mod:2d}, SUM%64={s_mod:2d}, B[8]={enc[8]:02x}")

# Maybe the checksum is NOT at byte 8. Let's check if byte 1 could be the checksum
print()
print("6. Checking if byte[1] could be the checksum (IR-style):")
print("   (sum of decoded bytes except byte[1]) >> 2 & 0x3F, then encode")
for n, (enc_hex, dec) in SAMPLES.items():
    enc = [int(x, 16) for x in enc_hex.split()]
    # Exclude byte 1 (index 1) from sum
    # Check which set of bytes sums to byte 1's decoded value
    
    if 1 not in DECODING_MAP or len(enc) <= 1:
        continue
    
    # IR formula: IR_BYTE = ENCODING_MAP[(sum(decoded[2:]) >> 2) & 0x3F]
    # Try: ENC[1] = ENCODING_MAP[(sum(decoded[0,2:9]) >> 2) & 0x3F]
    s = dec[0] + sum(dec[2:9])  # all except byte 1
    pred = ENCODING_MAP[(s >> 2) & 0x3F]
    ok = "✓" if pred == enc[1] else "✗"
    print(f"  {n:15s}: sum(dec[0,2:9])={s:3d}, >>2={(s>>2)&0x3F:2d}, pred={pred:02x}, actual={enc[1]:02x} {ok}")

# What if we use encoded bytes?
print()
print("7. Byte[1] as checksum using encoded bytes:")
for n, (enc_hex, dec) in SAMPLES.items():
    enc = [int(x, 16) for x in enc_hex.split()]
    s = sum(enc[:1] + enc[2:9])  # all except byte 1
    pred = ENCODING_MAP[(s >> 2) & 0x3F]
    ok = "✓" if pred == enc[1] else "✗"
    print(f"  {n:15s}: sum(enc[0,2:9])={s:3d}, >>2={(s>>2)&0x3F:2d}, pred={pred:02x}, actual={enc[1]:02x} {ok}")

print()
print("8. Byte[8] as sum of nibbles in bytes[0:8], mod 64:")
for n, (enc_hex, dec) in SAMPLES.items():
    enc = [int(x, 16) for x in enc_hex.split()]
    # Add all nibbles together
    total = 0
    for b in enc[:8]:
        total += (b >> 4) + (b & 0x0f)
    pred_index = total % 64
    pred = ENCODING_MAP[pred_index]
    ok = "✓" if pred == enc[8] else "✗"
    print(f"  {n:15s}: nibble_sum={total:2d}, %64={pred_index:2d}, pred={pred:02x}, actual={enc[8]:02x} {ok}")

print()
print("9. Byte[8] as encoded sum of high nibbles only:")
for n, (enc_hex, dec) in SAMPLES.items():
    enc = [int(x, 16) for x in enc_hex.split()]
    total = sum(b >> 4 for b in enc[:8])
    pred_index = total % 64
    pred = ENCODING_MAP[pred_index]
    ok = "✓" if pred == enc[8] else "✗"
    print(f"  {n:15s}: high_nibble_sum={total:2d}, %64={pred_index:2d}, pred={pred:02x}, actual={enc[8]:02x} {ok}")

print()
print("10. Byte[8] as encoded sum of low nibbles only:")
for n, (enc_hex, dec) in SAMPLES.items():
    enc = [int(x, 16) for x in enc_hex.split()]
    total = sum(b & 0x0f for b in enc[:8])
    pred_index = total % 64
    pred = ENCODING_MAP[pred_index]
    ok = "✓" if pred == enc[8] else "✗"
    print(f"  {n:15s}: low_nibble_sum={total:2d}, %64={pred_index:2d}, pred={pred:02x}, actual={enc[8]:02x} {ok}")

# Try with bit counts
print()
print("11. Byte[8] as encoded count of set bits in bytes[0:8]:")
for n, (enc_hex, dec) in SAMPLES.items():
    enc = [int(x, 16) for x in enc_hex.split()]
    total_bits = sum(b.bit_count() for b in enc[:8])
    pred_index = total_bits % 64
    pred = ENCODING_MAP[pred_index]
    ok = "✓" if pred == enc[8] else "✗"
    print(f"  {n:15s}: popcount={total_bits:2d}, %64={pred_index:2d}, pred={pred:02x}, actual={enc[8]:02x} {ok}")

# Maybe the RF checksum is the encoded version of: (XOR of all decoded bytes) >> 0 no shift?
print()
print("12. D[8] = XOR of decoded bytes D[0:8], then re-encode:")
for n, (enc_hex, dec) in SAMPLES.items():
    x = 0
    for d in dec[:8]:
        x ^= d
    enc_bytes2 = [int(x, 16) for x in enc_hex.split()]
    pred_enc = ENCODING_MAP[x]
    ok = "✓" if pred_enc == enc_bytes2[8] else "✗"
    ok = "✓" if pred_enc == enc_bytes2[8] else "✗"
    print(f"  {n:15s}: xor({','.join(str(d) for d in dec[:8])})={x:2d}, enc={pred_enc:02x}, actual={enc_bytes[8]:02x} {ok}")

# Try CRC-8 with various polynomials
print()
print("13. CRC-8 on encoded bytes[0:8]:")
for poly_name, poly in [("0x07 (x8+x2+x+1)", 0x07), ("0x31 (x8+x5+x4+1)", 0x31)]:
    print(f"\n   Polynomial {poly_name}:")
    for n, (enc_hex, dec) in SAMPLES.items():
        enc = [int(x, 16) for x in enc_hex.split()]
        crc = 0
        for b in enc[:8]:
            crc ^= b
            for _ in range(8):
                if crc & 0x80:
                    crc = ((crc << 1) ^ poly) & 0xFF
                else:
                    crc = (crc << 1) & 0xFF
        pred_index = crc % 64
        pred = ENCODING_MAP[pred_index]
        ok = "✓" if pred == enc[8] else "✗"
        print(f"    {n:15s}: crc8={crc:02x}, %64={pred_index:2d}, pred={pred:02x}, actual={enc[8]:02x} {ok}")
