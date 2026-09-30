# Check utils.h xoshiro_jump(jump_count>1): accumulators s0..s3 are not reset between jumps.
M=(1<<64)-1
def rotl(x,k): return ((x<<k)|(x>>(64-k)))&M
def step(s):
    t=(s[1]<<17)&M
    s[2]^=s[0]; s[3]^=s[1]; s[1]^=s[2]; s[0]^=s[3]; s[2]^=t; s[3]=rotl(s[3],45)
JUMP=[0x180ec6d33cfd0aba,0xd5a61266f0c9392c,0xa9582618e03fc9aa,0x39abdc4529b1661c]
def jump_tool(n, s):          # verbatim structure of utils.h:551-575
    s0=s1=s2=s3=0
    for j in range(n):
        for w in JUMP:
            for b in range(64):
                if w>>b & 1: s0^=s[0]; s1^=s[1]; s2^=s[2]; s3^=s[3]
                step(s)
        s[0],s[1],s[2],s[3]=s0,s1,s2,s3
def jump_ref(n, s):           # reference: accumulators reset for every jump
    for j in range(n):
        s0=s1=s2=s3=0
        for w in JUMP:
            for b in range(64):
                if w>>b & 1: s0^=s[0]; s1^=s[1]; s2^=s[2]; s3^=s[3]
                step(s)
        s[0],s[1],s[2],s[3]=s0,s1,s2,s3
seed=[0x0123456789abcdef,0xfedcba9876543210,0x0f0f0f0f0f0f0f0f,0x1234123412341234]
for n in range(0,5):
    a=list(seed); b=list(seed); jump_tool(n,a); jump_ref(n,b)
    print(n, "tool==ref" if a==b else "DIFFER", [hex(x) for x in a][:2])
# is tool-jump(2) == jump_ref(1) XOR jump_ref(2) ?
a=list(seed); jump_tool(2,a); r1=list(seed); jump_ref(1,r1); r2=list(seed); jump_ref(2,r2)
print("tool(2) == ref(1) xor ref(2):", a==[x^y for x,y in zip(r1,r2)])
