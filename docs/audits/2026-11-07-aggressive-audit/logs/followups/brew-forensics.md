# Forensics of `brew install afl++` (2026-11-07, 19:24-19:29 EST) and a revert plan

Status: READ-ONLY. Nothing below was executed. No `brew install/uninstall/link/unlink`,
no `make`, no branch switch, no commit. Every figure is traceable to a file in this
directory (index at the end).

Window asked for: 2026-11-07 19:20:00-19:35:00 EST = epochs 1794097200-1794098100
(= 2026-11-08 00:20-00:35 UTC; EST was in force, DST ended 2026-11-01).

## 1. What the install did, from the log and the receipts

Source (1), `brew-afl.log` (165 lines, read in full): Homebrew auto-updated itself
7.0.10 (8d799352d3) -> 7.0.12 (3ccfa1d071) and three taps, then announced

    Would install 1 formula:            afl++ 5.03c
    Would install 5 dependencies:       z3 5.3.3, llvm 23.1.5, lld 23.1.5, openssl@4 4.1.0, python@3.15 3.15.2
    Would upgrade 3 dependencies:       lz4 1.10.0 -> 1.11.0, ca-certificates 2026-10-20 -> 2026-11-05, sqlite 3.53.4 -> 3.54.1

and then actually poured only: z3, llvm, lld, openssl@4, sqlite (upgrade), python@3.15,
afl++ ("Installing dependencies for afl++: z3, llvm, lld, openssl@4, sqlite and
python@3.15"). **lz4 and ca-certificates were fetched (bottles are in the download
cache) but never poured**: the Cellar still holds lz4 1.10.0 only and ca-certificates
2026-07-16 / 2026-08-13 / 2026-10-20 only (`receipts-raw-and-lz4.txt`).

Two collateral lines in the log matter more than the formula list:

    Unlinking /opt/homebrew/Cellar/openssl@3/3.6.4... 6570 symlinks removed.      (while pouring openssl@4)
    Warning: These files were overwritten during the `brew link` step:            (while pouring python@3.15)
      /opt/homebrew/bin/{idle3,pip3,pydoc3,python3,python3-config}
      /opt/homebrew/share/man/man1/python3.1
      /opt/homebrew/lib/pkgconfig/{python3-embed.pc,python3.pc}
      /opt/homebrew/Frameworks/Python.framework/{Headers,Python,Resources,Versions/Current}
    They have been backed up to: /Users/gmcas/Library/Caches/Homebrew/Backup

Source (2), every `INSTALL_RECEIPT.json` under `/opt/homebrew/Cellar/*/*/` (130 kegs,
`receipts-all.json`, `receipts-scan.txt`). Exactly seven kegs fall in the window:

| keg | receipt `time` (epoch) | local | UTC | `installed_on_request` | `source.versions.stable` |
|---|---|---|---|---|---|
| z3 5.3.3 | 1794097696 | 2026-11-07 19:28:16 EST | 2026-11-08 00:28:16 | false | 5.3.3 |
| llvm 23.1.5 | 1794097702 | 19:28:22 EST | 00:28:22 | false | 23.1.5 |
| lld 23.1.5 | 1794097716 | 19:28:36 EST | 00:28:36 | false | 23.1.5 |
| openssl@4 4.1.0 | 1794097721 | 19:28:41 EST | 00:28:41 | false | 4.1.0 |
| sqlite 3.54.1 | 1794097730 | 19:28:50 EST | 00:28:50 | false | 3.54.1 |
| python@3.15 3.15.2 | 1794097733 | 19:28:53 EST | 00:28:53 | false | 3.15.2 |
| afl++ 5.03c | 1794097748 | 19:29:08 EST | 00:29:08 | **true** | 5.03c |

No other keg on the machine has a receipt time on 2026-11-07 or 2026-11-08. The next
most recent keg is gawk 5.4.1 at 2026-10-25 20:10:53 EDT.

Receipt note: Homebrew 7.0.12 tabs carry `installed_on_request` but **no
`installed_as_dependency` key at all** (checked on z3, afl++, python@3.14, openssl@3).
The "installed as dependency" column below is therefore `NOT installed_on_request`.

Receipt oddity: afl++'s `runtime_dependencies` records `lz4 1.11.0` and
`ca-certificates 2026-11-05` -- versions that were never installed. `brew missing`
reports nothing because the formulae exist at other versions.

## 2. The table

"Depended on by (installed)" is `brew uses --installed <f>`, which Homebrew computes from
the installed kegs' receipts (`brew-uses.txt`); "linked?" is `brew info --json=v2`
`linked_keg` plus `ls /opt/homebrew/opt`, `/opt/homebrew/var/homebrew/linked`
(`brew-info-summary.txt`, `symlink-state.txt`).

| formula | before | after | added-or-upgraded | installed as dependency | depended on by (installed) | linked? |
|---|---|---|---|---|---|---|
| afl++ | absent | 5.03c | **added** (on request) | no | nothing | yes (opt + 301-file keg linked) |
| z3 | absent | 5.3.3 | **added** | yes | afl++, lld, llvm | yes (bin/z3, lib/libz3*, python3.15 site-packages symlinks) |
| llvm | absent | 23.1.5 | **added** | yes | afl++, lld | **no** -- keg-only (`:provided_by_macos`); opt/llvm only |
| lld | absent | 23.1.5 | **added** | yes | afl++ | yes (bin/ld.lld, lld, ...) |
| openssl@4 | absent | 4.1.0 | **added** | yes | afl++, python@3.15 | **yes**, and it now owns the `openssl` alias: opt/openssl, lib/libcrypto.dylib, include/openssl, bin/openssl, pkgconfig |
| python@3.15 | absent | 3.15.2 | **added** | yes | afl++ | **yes**, and it now owns `python3`: bin/python3, pip3, idle3, pydoc3, python3-config, opt/python, opt/python3, Frameworks Current |
| sqlite | 3.53.4 | 3.54.1 | **upgraded** (old keg still present) | yes | afl++, emscripten, firebase-cli, node, **python@3.14**, python@3.15, rust (+ cask gcloud-cli recursively) | keg-only; opt/sqlite -> 3.54.1 (live for every dependent) |
| lz4 | 1.10.0 | 1.10.0 | announced, **not performed** | yes | zstd, gcc, llvm, llvm@22, node, python@3.14, rust, ... (21) | yes |
| ca-certificates | 2026-10-20 | 2026-10-20 | announced, **not performed** | yes | openssl@3, openssl@4, python@3.14, node, ruby, rust, gnupg, ... (20) | yes |
| openssl@3 | 3.6.4 **linked** (owned libcrypto.dylib, include/openssl, bin/openssl) | 3.6.4 **unlinked**, and the updated formula is now keg-only (`:versioned_formula`) | collateral (not a version change) | yes | cocoapods, emscripten, firebase-cli, libgit2, libngtcp2, libssh2, node, **python@3.14**, ruby, rust | **no** (6570 symlinks removed); opt/openssl@3 -> 3.6.4 remains |
| python@3.14 | 3.14.7 linked, owned `python3` | 3.14.7 still "linked" per brew (509 symlinks), but the 12 unversioned paths now point at 3.15 | collateral | yes | emscripten, cask gcloud-cli | partially -- bin/python3.14, pip3.14, ... yes; bin/python3, pip3, pkgconfig/python3.pc, man python3.1, Framework Headers/Python/Resources/Current **taken by 3.15** |
| Homebrew itself | 7.0.10 (8d799352d3) | 7.0.12 (3ccfa1d071); taps homebrew/core, homebrew/cask, hashicorp/tap updated | collateral | - | - | - |

Disk added: afl++ 6.2M, lld 5.8M, llvm 1.8G, z3 44M, python@3.15 92M, openssl@4 25M,
sqlite 3.54.1 5.2M; about 2.0 GB (`autoremove-and-misc.txt`).

## 3. Prefix symlinks that flipped (before -> after)

From `symlink-state.txt`, the Backup directory, and the install log.

| path | before (Backup / log) | after (now) |
|---|---|---|
| /opt/homebrew/bin/python3 | ../Cellar/python@3.14/3.14.7/bin/python3 | ../Cellar/python@3.15/3.15.2/bin/python3 |
| bin/pip3, idle3, pydoc3, python3-config | python@3.14/3.14.7 | python@3.15/3.15.2 |
| lib/pkgconfig/python3.pc, python3-embed.pc | python@3.14 | python@3.15 |
| share/man/man1/python3.1 | python@3.14 | python@3.15 |
| Frameworks/Python.framework/{Headers,Python,Resources,Versions/Current} | python@3.14 | python@3.15 |
| opt/python, opt/python3 (aliases) | not recorded | python@3.15/3.15.2 |
| lib/libcrypto.dylib, lib/libssl.dylib | openssl@3/3.6.4 (log: 6570 openssl@3 links removed) | openssl@4/4.1.0 |
| lib/libcrypto.3.dylib, libssl.3.dylib | present | **absent** |
| lib/libcrypto.4.dylib, libssl.4.dylib | absent | present |
| include/openssl | openssl@3 | openssl@4 |
| bin/openssl | openssl@3 3.6.4 | openssl@4 4.1.0 |
| lib/pkgconfig/openssl.pc, libcrypto.pc, libssl.pc | openssl@3 | openssl@4 (`pkg-config --modversion openssl` = 4.1.0) |
| opt/openssl (alias) | openssl@3 | openssl@4 |

The 12 overwritten python paths are preserved verbatim at
`/Users/gmcas/Library/Caches/Homebrew/Backup/` (all -> python@3.14/3.14.7; listed with
targets in `symlink-state.txt`). The python@3.14 keg's own `bin/` still contains the
unversioned `python3`, `pip3`, `idle3`, `pydoc3`, `python3-config` entries
(`cellar-bins.txt`), so relinking it recreates exactly those paths.

Symlink census (`symlink-counts.txt`, `symlinks-into-python@3.1{4,5}.txt`): 500 prefix
symlinks resolve into Cellar/python@3.15 (479 under lib/python3.15, 10 in bin, 4
pkgconfig, 2 man, 5 Framework); 509 into Cellar/python@3.14 (498 under lib/python3.14,
7 versioned bin names, 2 pkgconfig, 1 man, 1 Framework) -- and **zero** of python@3.14's
are the unversioned `python3/pip3/idle3/pydoc3/python3-config`; all five of those belong
to 3.15 today. **6708** prefix symlinks resolve into Cellar/openssl@4 (mostly
include/openssl headers and etc/openssl@4 cert links; `symlinks-into-openssl@4.txt`,
complete) -- that is the set `brew uninstall openssl@4` removes, the counterpart of the
6570 openssl@3 links the install removed.

## 4. openssl@3 vs openssl@4: who declares what, who actually links what

Declared (current formula definitions) vs installed-receipt vs actual Mach-O load
commands (`brew-uses.txt`, `brew-linkage-openssl-users.txt`, `python-resolution.txt`):

| installed formula | declares (current formula) | receipt (installed keg) | actually links (otool / brew linkage) |
|---|---|---|---|
| python@3.15 3.15.2 | openssl@4 | openssl@4 | /opt/homebrew/opt/openssl@4/lib/libcrypto.4.dylib, libssl.4.dylib (`_ssl`, `_hashlib`) |
| python@3.14 3.14.7 | **openssl@4** (formula moved on) | **openssl@3 3.6.4** | /opt/homebrew/opt/openssl@3/lib/libcrypto.3.dylib, libssl.3.dylib (`ssl.OPENSSL_VERSION` = "OpenSSL 3.6.4") |
| afl++ | python@3.15 (-> openssl@4) | python@3.15, openssl@4 | python@3.15 Framework only; no libcrypto directly |
| node, ruby, rust, libssh2, libngtcp2 | openssl@3 | openssl@3 | libcrypto.3 / libssl.3 |
| libgit2, cocoapods, emscripten, firebase-cli, gnupg, gnutls | (openssl@3 or none) | - | neither OpenSSL |
| llvm 23.1.5, lld, z3 | - | - | neither OpenSSL, no python |
| cask gcloud-cli | python@3.14 | - | (cask; follows python@3.14 -> openssl@3) |

So on this machine **nothing links libcrypto.4 except openssl@4 itself, python@3.15, and
the three repo binaries built during the install** (next section). The `--recursive`
form of `brew uses` lists gcloud-cli under openssl@4 only because it walks the *current*
python@3.14 formula definition, not the installed keg.

Note for later: python@3.14 is `outdated` (3.14.7 -> newer) and its current formula
depends on openssl@4. **Any `brew upgrade python@3.14` (or blanket `brew upgrade`) will
reinstall openssl@4 and relink it**, re-taking lib/libcrypto.dylib. 57 formulae are
outdated overall (`caveats-deps-leaves.txt`).

## 5. python3 resolution and PyYAML

PATH puts /opt/homebrew/bin first (`python-resolution.txt`).

| interpreter | resolves to | version | `import yaml` | OpenSSL |
|---|---|---|---|---|
| /opt/homebrew/bin/python3 | ../Cellar/python@3.15/3.15.2/bin/python3 | 3.15.2 | **FAILS** (ModuleNotFoundError) | 4.1.0 |
| /opt/homebrew/bin/python3.15 | python@3.15 | 3.15.2 | FAILS; `pip list`: pip only | 4.1.0 |
| /opt/homebrew/bin/python3.14 | ../Cellar/python@3.14/3.14.7/bin/python3.14 | 3.14.7 | **OK** -- PyYAML 6.0.3 at /opt/homebrew/lib/python3.14/site-packages/yaml; `pip list`: mpmath 1.4.1, pypdf 6.15.0, PyYAML 6.0.3, wheel 0.47.0 | 3.6.4 |
| /usr/local/bin/python3 | python.org framework 3.14.5 | 3.14.5 | FAILS | - |
| /usr/bin/python3 | Xcode 3.9.6 | 3.9.6 | FAILS | LibreSSL |

The regression scripts use the bare PATH name: `cpp/selftest/regression-workflows.sh`
line 55 is `if ! python3 -c 'import yaml'` (the current refusal), and 35 other
`cpp/selftest/regression-*.sh` call `python3` (`residues-and-regression-python.txt`).
Nothing in the repo pins `python3.14`. The audit's own workaround was a scratchpad PATH
shim, `scratchpad/py314bin/python3 -> /opt/homebrew/bin/python3.14` (Nov 8 17:57), and
its venv was created from python@3.14 at 19:26 before 3.15 landed
(`scratchpad-venv-shim.txt`); neither is a brew object.

## 6. The repo's cpp binaries (source 8)

`otool -L` on every Mach-O in `cpp/` (`repo-binaries-and-python-use.txt`):

| binary | mtime | libcrypto load command |
|---|---|---|
| cpp/ea_iid | 2026-11-07 19:28 | **/opt/homebrew/opt/openssl@4/lib/libcrypto.4.dylib** |
| cpp/ea_non_iid | 2026-11-07 19:28 | **libcrypto.4.dylib** |
| cpp/ea_restart | 2026-11-07 19:29 | **libcrypto.4.dylib** |
| cpp/ea_conditioning | 2026-10-20 21:06 | /opt/homebrew/opt/openssl@3/lib/libcrypto.3.dylib |
| cpp/ea_transpose | 2026-10-15 18:17 | libcrypto.3.dylib |

Mechanism, from `scratchpad/build.log` and `cpp/Makefile` lines 69-72 on master: the
build compiled with `-I/opt/homebrew/opt/openssl@3/include` but linked with
`-L/opt/homebrew/lib -L/opt/homebrew/opt/openssl@3/lib` in that order; at 19:28:41
`/opt/homebrew/lib/libcrypto.dylib` flipped to openssl@4, so the three tools built in
that minute are **compiled against OpenSSL 3.6.4 headers and loading libcrypto 4.1.0**.
`fix/openssl-pin` reorders both `-I` and `-L` so the pinned prefix comes first
(`final-checks.txt`); with that Makefile the rebuild links libcrypto.3 whatever
`/opt/homebrew/lib` holds. All other load commands (libomp, jsoncpp, libdivsufsort,
libbz2, mpfr/gmp for conditioning) are unaffected by anything in the window.

For /opt/homebrew/bin, `brew uses --installed openssl@4` + `brew linkage` (section 4)
give the complete list of libcrypto.4 consumers: openssl@4's own `bin/openssl`, and
python@3.15's `_ssl`/`_hashlib`. No other keg.

## 7. REVERT PLAN (in order; NOT executed)

Preconditions for whoever runs it:

    export HOMEBREW_NO_AUTO_UPDATE=1 HOMEBREW_NO_ENV_HINTS=1     # my own `brew outdated` already auto-updated taps once; do not let it happen mid-plan
    pgrep -fl afl-fuzz                                            # expect nothing
    readlink /opt/homebrew/bin/python3; brew list --versions afl++ lld llvm z3 python@3.15 openssl@4 sqlite python@3.14 openssl@3 > /tmp/before.txt

### Step 1 -- put `python3` back on 3.14.7 (restores PyYAML for the regression scripts)

    brew unlink python@3.15

Removes the 500 symlinks that resolve into Cellar/python@3.15 (section 3; list in
`symlinks-into-python@3.15.txt`): bin/{python3, pip3, idle3, pydoc3, python3-config,
python3.15, pip3.15, idle3.15, pydoc3.15, python3.15-config}, lib/pkgconfig/{python3.pc,
python3-embed.pc, python-3.15.pc, python-3.15-embed.pc}, share/man/man1/{python3.1,
python3.15.1}, Frameworks/Python.framework/{Headers, Python, Resources, Versions/3.15,
Versions/Current}, and the lib/python3.15 tree. Leaves the keg, opt/python@3.15 and
/opt/homebrew/lib/python3.15/site-packages (real pip dirs) in place.

**After this line `/opt/homebrew/bin/python3` is ABSENT.** `brew unlink` never restores
another keg's links, so the answer to "does `brew unlink python@3.15` restore python3 ->
3.14?" is **no**. And a plain `brew link python@3.14` is a **no-op** here: brew still
holds `var/homebrew/linked/python@3.14`, so it prints "Already linked: ... To relink,
run: brew unlink python@3.14 && brew link python@3.14" and skips, even with
`--overwrite` (`cmd/link.rb` lines 73-84, `homebrew-source-excerpts.txt`). Hence:

    brew unlink python@3.14 && brew link python@3.14

Expected: "Unlinking ... 509 symlinks removed" then "Linking ... ~521 symlinks created".
The 12 extra are exactly the Backup set. python@3.14 is not keg-only, so no `--force`.

Verify (every line must hold before going on):

    readlink /opt/homebrew/bin/python3                       # ../Cellar/python@3.14/3.14.7/bin/python3
    for f in bin/python3 bin/pip3 bin/idle3 bin/pydoc3 bin/python3-config lib/pkgconfig/python3.pc lib/pkgconfig/python3-embed.pc share/man/man1/python3.1 \
             Frameworks/Python.framework/Headers Frameworks/Python.framework/Python Frameworks/Python.framework/Resources Frameworks/Python.framework/Versions/Current; do
      [ "$(readlink /opt/homebrew/$f)" = "$(readlink ~/Library/Caches/Homebrew/Backup/$f)" ] || echo "MISMATCH $f"; done   # expect silence
    python3 -c 'import sys, yaml; print(sys.version.split()[0], yaml.__version__, yaml.__file__)'   # 3.14.7 6.0.3 /opt/homebrew/lib/python3.14/site-packages/yaml/__init__.py
    python3 -c 'import mpmath; print(mpmath.__version__)'   # 1.4.1 (c22c oracles)
    (cd /Users/gmcas/repos/SP800-90B_EntropyAssessment && cpp/selftest/regression-workflows.sh)   # must get past the line-55 PyYAML precondition

Fallback if brew misbehaves: the Backup directory is a verbatim copy of the 12 original
relative symlinks; `cp -a ~/Library/Caches/Homebrew/Backup/. /opt/homebrew/` after the
unlink would restore them byte-for-byte, but bypasses brew's bookkeeping -- use it as the
cross-check above, not as the method.

### Step 2 -- remove afl++ and the audit-only orphans, by name

    brew uninstall afl++ lld llvm z3 python@3.15 openssl@4

One command is safe: Homebrew excludes formulae in the same uninstall set from the
dependents check (`installed_dependents.rb` line 52) and computes dependents from
**receipts** (`formula.rb` `missing_dependencies`, lines 3089-3093: `tab_deps`), so
python@3.14's receipt (openssl@3) does not block openssl@4, and the cask gcloud-cli
follows python@3.14's receipt likewise. If preferred sequentially, the only valid order
is afl++ -> lld -> llvm -> z3 -> python@3.15 -> openssl@4 (each becomes a leaf only after
the one before). **If brew prints "Refusing to uninstall ... because it is required by
X", stop and report X; do not add `--ignore-dependencies`.**

Each keg is "audit-only" by the two tests the task set: receipt time in the window, and
no installed dependent outside the set (section 2 table). sqlite fails the second test
and is excluded (section 8).

What each removal changes:

- afl++: Cellar/afl++ (6.2M), bin/afl-*, opt/afl++, linked record.
- lld: bin/ld.lld, lld, ld64.lld, wasm-ld, lib/liblld*; 5.8M.
- llvm 23.1.5: keg-only, so only opt/llvm goes; 1.8G. `/opt/homebrew/etc/clang` STAYS and
  must stay: its 54 `.cfg` files date from 2026-08-30 (llvm@22's install); only
  `.keepme` is from 19:28 (`final-checks.txt`).
- z3: bin/z3, lib/libz3*, include/z3*, and the symlinks
  lib/python3.15/site-packages/z3/* (they point into the z3 keg); 44M.
- python@3.15: already unlinked by step 1; removes the keg (92M), opt/python@3.15 and
  the alias links opt/python, opt/python3. **Residue:** /opt/homebrew/lib/python3.15/
  (real dirs `pip`, `pip-26.2.2.dist-info`; nothing user-installed -- `pip list` showed
  pip only). Optional, after confirming the keg is gone: `rm -rf /opt/homebrew/lib/python3.15`.
- openssl@4: bin/openssl, lib/libcrypto.dylib, libssl.dylib, libcrypto.4.dylib,
  libssl.4.dylib, lib/cmake/OpenSSL, include/openssl, lib/pkgconfig/{openssl,libcrypto,
  libssl}.pc, opt/openssl alias; 25M. Brew will warn that
  `/opt/homebrew/etc/openssl@4` (8 config files, no user edits known) was not removed;
  optional `rm -rf /opt/homebrew/etc/openssl@4`.

**What happens to /opt/homebrew/lib/libcrypto.dylib:** it becomes ABSENT, together with
include/openssl, bin/openssl (system /usr/bin/openssl = LibreSSL remains) and
`pkg-config openssl`. It is **not** restored to openssl@3 automatically: the tap update
made openssl@3 keg-only (`keg_only_reason: :versioned_formula`), and brew relinks nothing
on uninstall (`keg.rb` `uninstall`, lines 328-349). See step 3.

**What happens to the repo's current cpp/ea_* binaries:** `ea_iid`, `ea_non_iid`,
`ea_restart` will abort at launch with `dyld: Library not loaded:
/opt/homebrew/opt/openssl@4/lib/libcrypto.4.dylib`. They must be rebuilt
(`cd cpp && make clean && make` -- not run here). With master's Makefile the rebuild
links libcrypto.3 only because the first `-L` directory no longer has a libcrypto; with
fix/openssl-pin's Makefile it links libcrypto.3 regardless. `ea_conditioning` and
`ea_transpose` are untouched (they already load libcrypto.3 from
/opt/homebrew/opt/openssl@3, which stays). This is also why step 2 must precede the
"re-runs green on a clean build" merges in the user's task 2, or those builds will again
pick libcrypto.4 on master's Makefile.

**Do NOT use `brew autoremove`.** Its dry run today lists five unrelated, pre-existing
(2026-10-20) formulae -- dav1d, lame, libvmaf, libvpx, mpg123 -- and it would take them
along (`autoremove-and-misc.txt`).

### Step 3 -- OPTIONAL: restore openssl@3's pre-audit link

    brew link openssl@3          # only after step 2; allowed WITHOUT --force because the keg-only reason is :versioned_formula (cmd/link.rb line 108)

Recreates ~6570 symlinks: lib/libcrypto.dylib -> 3.6.4, libcrypto.3.dylib, libssl.*,
include/openssl, bin/openssl 3.6.4, pkgconfig. This is the literal pre-audit state, but:
Homebrew now treats openssl@3 as keg-only, so the next `brew upgrade openssl@3` (it is
outdated) installs a new keg and does **not** relink it -- the link would silently vanish
then. Nothing measured on this machine needs it: the repo Makefile uses `brew --prefix
openssl@3` explicitly, and every other dependent loads openssl@3 by its absolute
`/opt/homebrew/opt/openssl@3/...` install name (section 4). Recommendation: skip unless
a build outside this repo is found to rely on `/opt/homebrew/lib/libcrypto.dylib` or
`pkg-config openssl`.

### Step 4 -- final verification

    brew list --versions afl++ lld llvm z3 python@3.15 openssl@4     # all "No such keg"/empty
    brew list --versions sqlite python@3.14 openssl@3 llvm@22         # sqlite 3.54.1 3.53.4; python@3.14 3.14.7; openssl@3 3.6.4 3.6.3; llvm@22 22.1.8  (unchanged)
    readlink /opt/homebrew/bin/python3                                # ../Cellar/python@3.14/3.14.7/bin/python3
    ls -l /opt/homebrew/lib/libcrypto.dylib                           # absent (or -> openssl@3/3.6.4 if step 3 was taken)
    python3.14 -c 'import sqlite3, ssl; print(sqlite3.sqlite_version, ssl.OPENSSL_VERSION)'   # 3.54.1  OpenSSL 3.6.4 ...  (proves sqlite and openssl@3 still serve python@3.14)
    brew autoremove --dry-run                                         # still exactly the five unrelated names, nothing new
    otool -L cpp/ea_iid cpp/ea_non_iid cpp/ea_restart | grep crypto   # after the rebuild: libcrypto.3.dylib on all three

### Not reverted, deliberately

- **sqlite 3.54.1** -- see section 8.
- **Homebrew 7.0.12 and the tap updates** (incl. the further auto-update to bc63375ac3
  that my `brew outdated` triggered on 2026-11-08). Rolling Homebrew back is neither
  sensible nor what the task asked.
- **openssl@3's keg-only status** -- a property of the updated formula, not of the Cellar.
- **lz4, ca-certificates** -- unchanged; nothing to revert. Their fetched bottles
  (`lz4--1.11.0.arm64_tahoe.bottle.tar.gz`, `ca-certificates--2026-11-05.all.bottle.tar.gz`)
  and the seven window manifests sit in `~/Library/Caches/Homebrew/downloads`; `brew
  cleanup -n` previews, optional.
- **~/Library/Caches/Homebrew/Backup** -- keep until step 1 is verified; delete afterwards if wanted.

## 8. DO-NOT-TOUCH list

Anything in or near the window that something older depends on, or that the suite needs:

- **sqlite 3.54.1** (in window, upgraded). Keg-only but live through `opt/sqlite` for
  python@3.14 (`sqlite3.sqlite_version` = 3.54.1 right now), node, rust, emscripten,
  firebase-cli (receipt-based uses). Downgrading is not a clean operation: `brew
  uninstall sqlite` resolves to the opt keg (3.54.1), removes it and opt/sqlite, and
  because the keg-only reason is `:provided_by_macos` on the default prefix, `brew link
  sqlite` **refuses even with `--force`** (`cmd/link.rb` lines 97-105), so 3.53.4 could
  only be re-pointed by a hand-made opt symlink. Leave 3.54.1; leave the orphaned 3.53.4
  keg too (`brew cleanup sqlite` would delete it; harmless either way).
- **readline 8.3.6, xz 5.8.4, zstd 1.5.7_1, lz4 1.10.0, mpdecimal 4.0.1, ca-certificates
  2026-10-20** -- pre-existing shared deps of python@3.14, gcc, node, rust, llvm@22, ...
- **python@3.14 3.14.7** and `/opt/homebrew/lib/python3.14/site-packages` (PyYAML 6.0.3,
  mpmath 1.4.1, pypdf 6.15.0) -- the regression suite's interpreter.
- **openssl@3 3.6.4 (and the 3.6.3 keg)** -- python@3.14, node, ruby, rust, libssh2,
  libngtcp2, and the repo's ea_conditioning/ea_transpose load 3.6.4 by absolute path.
- **llvm@22 22.1.8** (keg-only, 2026-08-30) and **/opt/homebrew/etc/clang** -- a
  different formula from llvm 23.1.5.
- **libomp 23.1.2, jsoncpp 1.9.8, libdivsufsort 2.0.1, gcc 16.2.0 (mpfr, gmp)** -- the
  repo's build deps (2026-09-30).
- **dav1d, lame, libvmaf, libvpx, mpg123** -- what `brew autoremove` would remove; unrelated.
- **/usr/local/bin/python3** (python.org 3.14.5 framework) -- not Homebrew's.
- The scratchpad venv and `py314bin` shim -- not Homebrew's; scratchpad-local.

## 9. Caveats on this report

- Branch: the task said `audit/2026-11-07` was checked out and it was at my first
  command; at 2026-11-08 19:55:29 EST another process ran `checkout: moving from
  audit/2026-11-07 to master` (reflog in `branch-and-makefile.txt`). I switched nothing
  and committed nothing. `docs/audits/` is untracked on master, so this directory shows
  as untracked there; the four fix branches are checked out in `.claude/worktrees/`.
- My `brew outdated` call (before I set `HOMEBREW_NO_AUTO_UPDATE=1`) auto-updated the
  Homebrew taps 3ccfa1d071 -> bc63375ac3. No Cellar change, but it is a write I caused.
- `brew linkage --reverse <f>` lists a keg's own internal references, not outside
  dependents (`brew-linkage-reverse-openssl.txt`); section 4 therefore used `brew
  linkage <dependent>` and `otool -L` directly.
- The symlink census (`symlink-counts.txt`) is complete for python@3.15 (500),
  python@3.14 (509) and openssl@4 (6708). The passes for openssl@3, z3, lld, afl++ and
  llvm were still running when this report was finalised and are cut off with the
  session: `symlinks-into-openssl@3.txt` (expected 0 -- it is unlinked) and any
  `symlinks-into-{z3,lld,afl++,llvm}.txt` may be absent or truncated and nothing above
  relies on them.
- This directory also holds files from other follow-up tasks running in parallel
  (`mergesim-*`, `diff-noncpp-*`, `merge-map.md`, `final-files*`); they are not part of
  this forensics and were not read for it.
- `brew uses --installed --recursive` mixes receipt data with current formula
  definitions (gcloud-cli under openssl@4 is that artefact); the direct form is the one
  tabulated.

## Evidence index (all in this directory)

brew-afl.log is the saved install log at
`/private/tmp/claude-501/-Users-gmcas-repos-SP800-90B-EntropyAssessment/204b56c2-3645-487d-aa86-fccec9fd2701/scratchpad/brew-afl.log`.

- `scan-receipts.py`, `receipts-all.json`, `receipts-scan.txt` -- every receipt, window filter, multi-keg racks
- `receipts-raw-and-lz4.txt` -- raw receipt keys; lz4 / ca-certificates kegs; `brew list --versions`
- `brew-info-installed.json`, `brew-info-summary.txt`, `brew-info-installed.err` -- source (4)
- `brew-uses.txt` -- source (5)/(6), direct and recursive
- `brew-linkage-reverse-openssl.txt`, `brew-linkage-openssl-users.txt`, `llvm-linkage.txt` -- actual dylib bindings
- `symlink-state.txt` -- opt/bin/lib/include/Framework targets, linked registry, pinned, Backup dir with targets
- `cellar-bins.txt` -- python and openssl keg contents
- `python-resolution.txt` -- source (7)
- `repo-binaries-and-python-use.txt` -- source (8), Makefile link flags, python use in workflows/scripts
- `caveats-deps-leaves.txt` -- keg-only reasons, caveats, dep trees, leaves, outdated, missing
- `scratchpad-venv-shim.txt` -- the audit venv, the py314bin shim, build.log link lines
- `branch-and-makefile.txt`, `final-checks.txt` -- branch/worktree state, Makefile, fix/openssl-pin diff, etc/clang, cache
- `homebrew-source-semantics.txt`, `homebrew-source-excerpts.txt` -- the Homebrew code the plan's claims rest on
- `autoremove-and-misc.txt`, `residues-and-regression-python.txt`, `symlink-counts.txt`, `symlinks-into-*.txt`
