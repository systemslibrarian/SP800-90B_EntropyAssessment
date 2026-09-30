# "Conditioned" dataset: 1,000,000 bytes, each byte = (r<<4)|r with r uniform on 0..15 (seeded).
# Bytes are IID (16 equiprobable values, 4 bits of min-entropy per byte = 0.5 bit/bit),
# but the concatenated binary string is not IID (bits 4..7 of each byte repeat bits 0..3).
import random
r=random.Random(4242)
b=bytes(((x<<4)|x) for x in (r.randrange(16) for _ in range(10**6)))
open('nibdup.bin','wb').write(b)
# the same data as a binary string, one bit per byte, MSB-first (as ea_iid's own bsymbols)
bits=bytearray()
for y in b[:125000]:
    for k in range(7,-1,-1): bits.append((y>>k)&1)
open('nibdup_bits_1e6.bin','wb').write(bytes(bits))
