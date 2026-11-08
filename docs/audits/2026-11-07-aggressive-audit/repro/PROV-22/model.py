#!/usr/bin/env python3
"""Transcription of cpp/shared/utils.h xoshiro_jump() (lines 765-789) beside the canonical Blackman/Vigna jump().
The code declares the accumulators s0..s3 ONCE, outside the `for j < jump_count` loop, and never re-zeroes them,
so for jump_count >= 2 the result is acc_{j+1} = acc_j XOR J(s_j), not J^k(state).
usage: model.py <kmax>   -- prints one line per k in 0..kmax; exit 0 if every k agrees with canonical, 1 otherwise."""
import sys
MASK=(1<<64)-1
def rotl(x,k): return ((x<<k)|(x>>(64-k)))&MASK
def next_(s):
    r=(rotl((s[1]*5)&MASK,7)*9)&MASK; t=(s[1]<<17)&MASK
    s[2]^=s[0]; s[3]^=s[1]; s[1]^=s[2]; s[0]^=s[3]; s[2]^=t; s[3]=rotl(s[3],45); return r
JUMP=[0x180ec6d33cfd0aba,0xd5a61266f0c9392c,0xa9582618e03fc9aa,0x39abdc4529b1661c]
def canonical_jump(s):           # Blackman/Vigna: accumulators zeroed per call; == 2^128 next() calls
    acc=[0,0,0,0]
    for w in JUMP:
        for b in range(64):
            if w&(1<<b):
                for i in range(4): acc[i]^=s[i]
            next_(s)
    s[:]=acc
def code_jump(jump_count,s):     # utils.h:765-789 as written
    s0=s1=s2=s3=0
    for _ in range(jump_count):
        for w in JUMP:
            for b in range(64):
                if w&(1<<b): s0^=s[0]; s1^=s[1]; s2^=s[2]; s3^=s[3]
                next_(s)
        s[0],s[1],s[2],s[3]=s0,s1,s2,s3
seed=[0x9E3779B97F4A7C15,0xBF58476D1CE4E5B9,0x94D049BB133111EB,0x2545F4914F6CDD1D]
kmax=int(sys.argv[1]) if len(sys.argv)>1 else 4
bad=0
for k in range(kmax+1):
    a=list(seed); code_jump(k,a); b=list(seed)
    for _ in range(k): canonical_jump(b)
    same=(a==b); bad+=0 if same else 1
    print("k=%d (thread %d): code==canonical? %s ; code state nonzero? %s" % (k,k,same,any(a)))
if kmax>=2:
    s1=list(seed); canonical_jump(s1); s2=list(s1); canonical_jump(s2)
    a2=list(seed); code_jump(2,a2)
    print("k=2 equals S1 xor S2 (the un-reset accumulator prediction)?", a2==[x^y for x,y in zip(s1,s2)])
sys.exit(1 if bad else 0)
