#!/usr/bin/env python3
"""Regenerate spec.txt (text of NIST.SP.800-90B.pdf, Jan 2018) as used by the phase-2 audit.
Usage: python3 extract_spec_text.py NIST.SP.800-90B.pdf spec.txt   (needs pypdf; 6.19.0 was used)"""
import sys, pypdf
r = pypdf.PdfReader(sys.argv[1])
open(sys.argv[2], 'w').write(''.join(f"\n\n=====PAGE {i+1}=====\n" + (p.extract_text() or '') for i, p in enumerate(r.pages)))
