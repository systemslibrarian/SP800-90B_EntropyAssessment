# Exact build lines on this host (captured from `make -n` on 2026-11-07)

Production (what `cpp/Makefile` runs; DO NOT re-run `make` in `cpp/` during the audit):

```sh
cd cpp && clang++ -std=c++11 -Xpreprocessor -fopenmp -I/opt/homebrew/opt/libomp/include -O2 \
  -Werror=ignored-optimization-argument -I/usr/include/jsoncpp -I/opt/homebrew/include \
  -I/opt/homebrew/opt/openssl@3/include non_iid_main.cpp -o ea_non_iid \
  -L/opt/homebrew/lib -L/opt/homebrew/opt/openssl@3/lib -lbz2 -lpthread -ldivsufsort -ldivsufsort64 \
  -L/opt/homebrew/opt/libomp/lib -lomp -ljsoncpp -lcrypto
```

Same shape for `iid_main.cpp -o ea_iid` and `restart_main.cpp -o ea_restart`.

Out-of-tree instrumented builds: same line, run from `cpp/`, but with `-o <scratch>/<name>`
and the sanitizer flags added, e.g.

```sh
-O1 -g -fno-omit-frame-pointer -fsanitize=address,undefined -fno-sanitize-recover=undefined
-O1 -g -fno-omit-frame-pointer -fsanitize=thread
```

Apple clang 21 here has ASan, UBSan and TSan but NOT libFuzzer (`libclang_rt.fuzzer_osx.a`
is absent). AFL++ is installed from the Homebrew bottle for fuzzing (`afl-clang-fast++`).
Note `-Werror=ignored-optimization-argument` is kept so a silently dropped flag fails the build.
