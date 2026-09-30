import sys, re, subprocess, math
S='/tmp/claude-1000/-workspaces-SP800-90B-EntropyAssessment/bae8c694-6a48-4fd3-83f6-685460129aee/scratchpad'
fn, bits = sys.argv[1], sys.argv[2]
tool = subprocess.run([S+'/up/cpp/ea_non_iid','-vv',fn,bits],capture_output=True,text=True)
T={}
for line in tool.stdout.splitlines():
    m=re.match(r'^Literal (.+?) Estimate: (.+?) = (\S+)$',line)
    if m: T[(m.group(1),m.group(2))]=m.group(3)
if tool.returncode!=0: print(fn,'TOOL rc',tool.returncode, tool.stderr.strip()[-200:])
orc = subprocess.run(['python3',S+'/oracle.py',fn,'MCV,Markov,TT,Lag,LZ78Y','tool-z'],capture_output=True,text=True)
O={}
for line in orc.stdout.splitlines():
    m=re.match(r'^(.+?): (.+?) = (\S+)$',line)
    if m: O[(m.group(1),m.group(2))]=m.group(3)
names={'Most Common Value':'Most Common Value','Markov':'Markov','t-Tuple':'t-Tuple','LRS':'LRS','Lag Prediction':'Lag Prediction','LZ78Y Prediction':'LZ78Y Prediction'}
worst=0; n=0; bad=[]
for (est,key),ov in O.items():
    tk=(names[est],key)
    if tk not in T:
        if key in ('skip','P_local'): continue
        bad.append(f'MISSING tool {tk} oracle={ov}'); continue
    tv=T[tk]; n+=1
    try:
        a=float(ov); b=float(tv)
    except: bad.append(f'{tk} oracle={ov} tool={tv}'); continue
    d=abs(a-b)/max(abs(a),abs(b),1e-300)
    tol = 1e-9 if key!='P_local' else 1e-6
    if d>tol: bad.append(f'DIFF {tk} oracle={a!r} tool={b!r} rel={d:.3g}')
    if key!='P_local': worst=max(worst,d)
print(f'{fn}: compared {n} values, worst rel {worst:.3g}; issues={len(bad)}')
for x in bad: print('   ',x)
