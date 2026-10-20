#!/usr/bin/env python3
"""R-1 exposure scan over the fork's own evidence sets (OC-42).

R-1 aborts only when every symbol count is EXACTLY equal and the observed
alphabet size is one of the affected values for the platform. Real captures are
immune; CONSTRUCTED data is the exposed case, because forced matrices and
synthetic fixtures are where counts come out perfectly balanced. So the fork's
own corpora are the thing to check.

Usage: r1_corpus_scan.py <file-or-directory> ...
"""
import sys, os, collections

# Measured through the production functions at exact balance (OC-41, OC-40).
ARM64 = {17,21,23,25,27,29,34,35,37,39,41,42,44,47,48,52,53,54,55,58,59,60,62,65,
         66,67,68,69,73,77,78,81,82,83,88,91,92,94,95,96,100,103,104,106,107,109,
         110,112,120,125,126,130,131,133,134,135,136,140,142,145,146,149,150,152,
         153,154,156,157,158,162,164,168,171,172,173,175,176,178,179,181,183,186,
         188,189,190,191,192,193,198,199,200,201,202,203,210,211,214,218,219,220,
         221,222,224,226,227,228,233,235,237,239,244,246,247,248,250,252,254}
X86_64 = {3,6,7,9,12,14,15,17,18,19,21,23,24,27,28,29,30,31,34,35,36,38,39,42,43,
          46,47,48,49,51,53,54,55,56,57,58,59,60,62,63,67,68,70,72,73,76,78,79,81,
          84,85,86,87,89,92,94,95,96,97,98,102,103,106,107,108,110,111,112,113,114,
          116,118,119,120,124,126,127,129,131,133,134,136,137,140,141,143,144,145,
          146,147,149,152,155,156,158,161,162,165,168,169,170,171,172,173,174,175,
          177,178,181,183,184,187,188,189,190,192,194,195,196,197,201,204,205,206,
          207,209,212,214,215,216,217,219,220,222,223,224,225,226,228,229,231,232,
          233,236,237,238,239,240,248,249,251,252,253,254,255}

def scan(path):
    try:
        d = open(path, 'rb').read()
    except OSError as e:
        print("  SKIPPED (unreadable): %s (%s)" % (path, e))
        return None
    if not d:
        return None
    c = collections.Counter(d)
    k = len(c)
    counts = set(c.values())
    balanced = (len(counts) == 1)
    return dict(n=len(d), k=k, balanced=balanced, spread=(max(c.values()) - min(c.values())),
                arm=(k in ARM64), x86=(k in X86_64))

def main(args):
    files = []
    for a in args:
        if os.path.isdir(a):
            for root, _, names in os.walk(a):
                files += [os.path.join(root, n) for n in sorted(names) if n.endswith('.bin')]
        elif a.endswith('.bin'):
            files.append(a)
    print("| file | bytes | k | counts exactly equal | k affected arm64 | k affected x86-64 | ABORTS |")
    print("|---|---:|---:|---|---|---|---|")
    examined = 0; found = []; balanced = 0; results = []
    for f in sorted(files):
        r = scan(f)
        if r is None:
            continue
        results.append((f, r))
        examined += 1
        if r['balanced']:
            balanced += 1
        ab_arm = r['balanced'] and r['arm']
        ab_x86 = r['balanced'] and r['x86']
        if ab_arm or ab_x86:
            found.append((f, r, ab_arm, ab_x86))
        if r['balanced']:          # only the interesting rows, to keep this readable
            print("| %s | %d | %d | yes | %s | %s | %s |" % (
                os.path.basename(f), r['n'], r['k'], r['arm'], r['x86'],
                ("**arm64+x86-64**" if (ab_arm and ab_x86) else
                 "**arm64**" if ab_arm else "**x86-64**" if ab_x86 else "no")))
    print()
    print("examined: %d files" % examined)
    print("exactly balanced: %d" % balanced)
    print("would abort on some platform: %d" % len(found))
    for f, r, a, x in found:
        print("  %s  k=%d  arm64=%s  x86-64=%s" % (f, r['k'], a, x))
    if not found:
        print("  none.")

if __name__ == '__main__':
    main(sys.argv[1:] or ['bin'])
