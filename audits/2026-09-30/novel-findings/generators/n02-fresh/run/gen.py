import random
r = random.Random(4242)
# 1,000,000 bytes; each byte is (x<<4)|x for a uniform 4-bit x,
# so the high nibble duplicates the low nibble: 4 bits of entropy per 8 bits (0.5 bit/bit).
data = bytes(((x << 4) | x) for x in (r.randrange(16) for _ in range(1000000)))
open('nibdup.bin', 'wb').write(data)
# The same data as a bitstring, one bit per byte, MSB first (8,000,000 samples).
open('nibdup_bits.bin', 'wb').write(bytes((b >> k) & 1 for b in data for k in range(7, -1, -1)))
