#!/usr/bin/env python3
"""Validate oracle.py against the SP 800-90B worked examples (Lag D=3, LZ78Y B=4, t-Tuple/LRS cutoff 3,
Markov, MCV). Re-creation of the inline check run on 2026-09-30. Usage: python3 oracle_worked_examples.py [oracle.py]"""
import sys, os
src = open(sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(os.path.abspath(__file__)), 'oracle.py')).read()
src = src.replace("    D = 128\n", "    D = DLAG\n").replace("    B = 16\n", "    B = BLZ\n").replace("if Q[W] < 35:", "if Q[W] < CUT:")
ns = {'DLAG': 3, 'BLZ': 4, 'CUT': 3, '__name__': 'x'}
exec(src, ns)
S = [2,1,3,2,1,3,1,3,1,2]; print("Lag ex (want P_global'=0.6008 P_local=0.1167 H=0.735):", ns['lag']([x-1 for x in S], 3, 2.576))
S = [2,1,3,2,1,3,1,3,1,2,1,3,2]; print('LZ78Y ex (want 0.9868 0.1229 0.0191):', ns['lz78y']([x-1 for x in S], 3, 2.576))
S = [2,2,0,1,0,2,0,1,2,1,2,0,1,2,1,0,0,1,0,0,0]; print('t-Tuple/LRS ex (want t 0.273, LRS u4 v5 0.6146):', ns['ttuple_lrs'](S, 2.576))
S = [1,0,0,0,1,1,1,0,0,1,0,1,0,1,0,1,1,1,0,0,1,1,0,0,0,1,1,1,0,0,1,0,1,0,1,0,1,1,1,0]; print('Markov ex (want 0.761):', ns['markov'](S)['min entropy'])
S = [0,1,1,2,0,1,2,2,0,1,0,1,1,0,2,2,1,0,2,1]; print('MCV ex (p_u 0.6895):', ns['mcv'](S, 2.576))
