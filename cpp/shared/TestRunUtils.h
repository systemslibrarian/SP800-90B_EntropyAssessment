#ifndef TESTRUNUTILS_H
#define TESTRUNUTILS_H

#include <cstdlib>
#include <string.h>
#include <string>
#include <fstream>
#include <unistd.h>   // getpid, for the atomic report write below
#include <cstdio>     // rename, remove
#include <sys/types.h>
#include <sys/stat.h>

// S_ISREG is POSIX and is present on Linux, macOS and mingw-w64, which is the
// Windows toolchain this fork documents. Define it for a toolchain that has
// only the _S_IFREG spelling.
#ifndef S_ISREG
#define S_ISREG(m) (((m) & _S_IFMT) == _S_IFREG)
#endif

#include <openssl/evp.h>
#include <openssl/sha.h>

using namespace std;

// ===========================================================================
// A05 -- THE OUTPUT TARGET MUST NEVER BE THE INPUT CAPTURE
//
// C14 claims the -o path with a placeholder as soon as the path is known, so
// that no run can leave a stale success behind. That repair moved an
// irreversible truncation EARLIER than the assessment, and with
// `-o capture.bin capture.bin` the 1,000,000-byte capture became a 602-byte
// error report before a single sample was read. Measured, all three tools,
// exit 255. In January the input is a physical capture that cannot be
// recreated, so this outranks everything else in the audit.
//
// The guard is identity, not string equality: "./x" and "x", a hard link, a
// symlink, and an absolute path all name the same bytes. On POSIX the
// documented identity pair is (st_dev, st_ino) and stat() follows symlinks, so
// one comparison covers every alias form. On Windows stat() reports st_ino as
// 0 for every file, which would make two DIFFERENT files compare equal and
// refuse valid runs, so there the identity pair is the volume serial number
// and the 64-bit file index from GetFileInformationByHandle -- opening for
// read is not destructive, and that is the documented Win32 equivalent.
//
// FAIL-CLOSED. If identity cannot be established, the run is refused rather
// than guessed at: the cost of a wrong refusal is re-running a command, and
// the cost of a wrong permission is an unrecoverable capture.
// ===========================================================================

#ifdef _WIN32
#ifndef WIN32_LEAN_AND_MEAN
#define WIN32_LEAN_AND_MEAN
#endif
#ifndef NOMINMAX
#define NOMINMAX
#endif
#include <windows.h>
#endif

#include <cerrno>
#include <fcntl.h>   // O_CREAT|O_EXCL|O_NOFOLLOW for the temp write (F03)
#include <ctime>

enum FileIdentity { FILES_DISTINCT, FILES_SAME, FILES_UNDETERMINED };

static FileIdentity sameFileIdentity(const char *outPath, const char *inPath) {
    if (outPath == NULL || inPath == NULL) return FILES_UNDETERMINED;
    if (strcmp(outPath, inPath) == 0) return FILES_SAME;   // the cheap case first
#ifdef _WIN32
    HANDLE ho = CreateFileA(outPath, 0, FILE_SHARE_READ | FILE_SHARE_WRITE | FILE_SHARE_DELETE,
                            NULL, OPEN_EXISTING, FILE_FLAG_BACKUP_SEMANTICS, NULL);
    if (ho == INVALID_HANDLE_VALUE) {
        const DWORD e = GetLastError();
        // The output does not exist, so it cannot be the input.
        if (e == ERROR_FILE_NOT_FOUND || e == ERROR_PATH_NOT_FOUND) return FILES_DISTINCT;
        return FILES_UNDETERMINED;
    }
    HANDLE hi = CreateFileA(inPath, 0, FILE_SHARE_READ | FILE_SHARE_WRITE | FILE_SHARE_DELETE,
                            NULL, OPEN_EXISTING, FILE_FLAG_BACKUP_SEMANTICS, NULL);
    if (hi == INVALID_HANDLE_VALUE) {
        const DWORD e = GetLastError();
        CloseHandle(ho);
        if (e == ERROR_FILE_NOT_FOUND || e == ERROR_PATH_NOT_FOUND) return FILES_DISTINCT;
        return FILES_UNDETERMINED;
    }
    BY_HANDLE_FILE_INFORMATION io, ii;
    const BOOL okO = GetFileInformationByHandle(ho, &io);
    const BOOL okI = GetFileInformationByHandle(hi, &ii);
    CloseHandle(ho); CloseHandle(hi);
    if (!okO || !okI) return FILES_UNDETERMINED;
    const bool same = (io.dwVolumeSerialNumber == ii.dwVolumeSerialNumber)
                   && (io.nFileIndexHigh == ii.nFileIndexHigh)
                   && (io.nFileIndexLow  == ii.nFileIndexLow);
    return same ? FILES_SAME : FILES_DISTINCT;
#else
    struct stat so, si;
    if (stat(outPath, &so) != 0) {
        if (errno == ENOENT) return FILES_DISTINCT;   // nothing there to destroy
        return FILES_UNDETERMINED;
    }
    if (stat(inPath, &si) != 0) {
        if (errno == ENOENT) return FILES_DISTINCT;   // no capture to destroy
        return FILES_UNDETERMINED;
    }
    // st_ino 0 on both would make every pair compare equal; treat it as no answer.
    if (so.st_ino == 0 && si.st_ino == 0) return FILES_UNDETERMINED;
    return (so.st_dev == si.st_dev && so.st_ino == si.st_ino) ? FILES_SAME : FILES_DISTINCT;
#endif
}

// THE GUARD BELONGS IN THE WRITER, SO THE CLAIM CAN STAY EARLY.
//
// The first version of this fix deferred C14's claim until after argument
// parsing, so that the input path would be known and could be compared. That
// cost C14 real coverage, and the existing regression caught it immediately:
// `ea_iid -o <stale>` with no operand exits on the usage path, which is now
// ABOVE the claim, so the previous run's complete report survived byte
// identical -- the exact fail-open C14 closed.
//
// So the input path is REGISTERED as protected as soon as a prescan can see
// it, and writeJsonReport -- the only function that writes a report at all --
// refuses any target that identifies it. The claim goes back to where C14 put
// it, at `-o` parse time, and no report write of any kind can reach the
// capture. A usage error with no operand protects nothing, because there is no
// input to destroy, and the stale report is replaced as before.
static string g_protectedInputPath;

static void protectInputPath(const string &path) { g_protectedInputPath = path; }

// Find the -o value and the first operand the way getopt will, so the identity
// check can run before anything is written. Handles clusters ("-vo out"),
// attached arguments ("-oout", "-l5,10"), the "--" separator, and options that
// consume the FOLLOWING element -- which is what A04 showed the old prescan
// did not understand.
static void prescanOutputAndOperand(int argc, char *argv[], const char *optstring,
                                    string *outPath, string *operand) {
    outPath->clear();
    operand->clear();
    int i = 1;
    for (; i < argc; i++) {
        const char *a = argv[i];
        if (a == NULL) return;
        if (strcmp(a, "--") == 0) { i++; break; }
        if (a[0] != '-' || a[1] == '\0') break;          // the first operand
        if (a[1] == '-') continue;                       // a long option (--version)
        for (size_t k = 1; a[k] != '\0'; k++) {
            const char *p = strchr(optstring, a[k]);
            if (p == NULL) break;                        // getopt will reject it
            if (p[1] == ':') {                           // this option takes an argument
                if (a[k + 1] != '\0') {                  // attached: "-oout"
                    if (a[k] == 'o') *outPath = a + k + 1;
                } else if (i + 1 < argc) {               // separate: "-o out"
                    if (a[k] == 'o') *outPath = argv[i + 1];
                    i++;
                }
                break;
            }
        }
    }
    if (i < argc && argv[i] != NULL) *operand = argv[i];
}

// Refuse before any destructive open. Returns true when it is safe to proceed.
// Nothing is written on refusal: the whole point is to leave the capture, and
// any previous report, exactly as they are. Failed-run evidence goes to stderr,
// which costs the captured bytes nothing.
static bool outputTargetIsSafe(const string &outPath, const char *inPath) {
    if (outPath.empty()) return true;            // no -o, nothing to claim
    // No input path at all -- a usage error with no operand, for instance --
    // means there is no capture to destroy, so the claim is safe and C14's
    // stale-report coverage is preserved. The first version of this returned
    // UNDETERMINED here and refused every `-o <path>` with no operand, which
    // broke the usage path the existing regression covers.
    if (inPath == NULL || inPath[0] == '\0') return true;
    const FileIdentity id = sameFileIdentity(outPath.c_str(), inPath);
    if (id == FILES_SAME) {
        fprintf(stderr,
            "Error: the output path '%s' is the same file as the input '%s'.\n"
            "       Refusing to run: claiming the output truncates it, and that would\n"
            "       destroy the input capture before any sample was read. Nothing has\n"
            "       been written; the input is untouched. Choose a different -o path.\n",
            outPath.c_str(), inPath ? inPath : "(none)");
        return false;
    }
    if (id == FILES_UNDETERMINED) {
        fprintf(stderr,
            "Error: cannot establish whether the output path '%s' and the input '%s'\n"
            "       are the same file. Refusing to run rather than risk truncating the\n"
            "       input capture. Nothing has been written; the input is untouched.\n",
            outPath.c_str(), inPath ? inPath : "(none)");
        return false;
    }
    return true;
}

// ===========================================================================
// A04 -- THE --version PRESCAN MUST UNDERSTAND OPTIONS THAT CONSUME AN ARGUMENT
//
// The prescan stopped at the first operand and skipped argv[0], which closed
// C14 route 2. It still did not know that `-o` takes an argument, so
// `ea_non_iid -o --version absent-data 1` treated `--version` as an OPTION,
// printed the version, and exited 0 -- nothing assessed, no report written,
// any previous report left in place. Exit status 0 with a stale report is the
// fail-open C14 exists to prevent, reached through the option parser instead
// of through an error path.
//
// Walk argv the way getopt will: stop at "--" or the first operand, and when a
// short-option cluster ends in a letter the optstring marks with ':' and no
// argument is attached, skip the next element, because that element is the
// option's ARGUMENT and not an option at all.
// ===========================================================================
static bool versionOptionRequested(int argc, char *argv[], const char *optstring) {
    for (int i = 1; i < argc; i++) {
        const char *a = argv[i];
        if (a == NULL) return false;
        if (strcmp(a, "--") == 0) return false;            // end of options
        if (a[0] != '-' || a[1] == '\0') return false;     // first operand, or "-"
        if (strcmp(a, "--version") == 0) return true;      // a real option
        const size_t n = strlen(a);
        const char last = a[n - 1];
        const char *p = strchr(optstring, last);
        // ':' after the letter means it takes an argument; n == 2 means the
        // cluster is exactly "-x", so the argument is the NEXT element. For
        // "-oout" or "-l5,10" the argument is attached and nothing is skipped.
        if (p != NULL && p[1] == ':' && n == 2) i++;
    }
    return false;
}

// Write a JSON report, reporting a failure instead of silently losing it.
//
// Every report write was an unchecked ofstream, so "-o /dev/full" or a path in
// a directory that does not exist produced no file and exited 0. A caller that
// reads the exit status and then opens the report would read a stale file, or
// none, believing the run had succeeded.
//
// Returns true when the report was written. The caller decides the exit
// status, because several of these writes happen on paths that are already
// failing for some other reason and that reason should be the one reported.
// C08 / oac-13: the report write is ATOMIC from a reader's point of view.
//
// It used to open the operator's path and stream into it, so a signal, a full
// device or an I/O error part-way through left TRUNCATED JSON at that path --
// syntactically invalid, and a consumer that reads the file after checking the
// exit status could parse-fail on it or, worse, read a prefix. C14's
// placeholder narrowed the window from "a stale VALID report" to "an invalid
// one", which a consumer can at least detect, but did not close it.
//
// Now the content is written to a sibling temporary file, flushed and checked,
// and only then renamed over the target. rename(2) within a directory is
// atomic, so the path a reader opens holds either the previous content or the
// complete new content and never a prefix. The temporary is removed on every
// failure path, so a failed write leaves no debris beside the operator's file.
//
// The sibling must be in the SAME directory: rename() across filesystems
// fails, and a temporary in /tmp would silently reintroduce a copy step that
// is not atomic. That also keeps the existing failure behaviour intact -- an
// unwritable directory or a path like /dev/full fails at the temporary, which
// is still a failed run, and the regressions that assert those failures pass
// unchanged.
bool writeJsonReport(const string &path, const string &json) {
    // A05: no report write may target the input capture, whatever path it
    // reached here by. This is the single choke point: the C14 placeholder,
    // every error report and every successful report all come through here.
    if (!g_protectedInputPath.empty()
        && sameFileIdentity(path.c_str(), g_protectedInputPath.c_str()) != FILES_DISTINCT) {
        fprintf(stderr,
            "Error: refusing to write the report to '%s': it is the same file as the\n"
            "       input '%s' (or that cannot be ruled out). Writing it would destroy\n"
            "       the input capture. Nothing has been written.\n",
            path.c_str(), g_protectedInputPath.c_str());
        return false;
    }

    // F03 (OC-77): THE GUARD MUST COVER EVERY WRITE PATH, NOT THE ENTRY POINT.
    //
    // The identity check above protects the FINAL report path. The temporary
    // was `path + ".tmp." + getpid()` -- predictable -- and was opened with
    // std::ios::trunc, which FOLLOWS A SYMLINK. Measured: an open of that
    // shape through a symlink pointing at a 1,000,000-byte capture left the
    // capture 15 bytes long. So the alias guard was at the front door while
    // the temporary was an unguarded second one, and in January the input is a
    // capture that cannot be recreated.
    //
    // Four changes, each closing a separate part of it:
    //   1. O_CREAT|O_EXCL -- the open FAILS if anything exists at that path,
    //      including a symlink. This alone defeats the planted-symlink case,
    //      because O_EXCL does not follow one.
    //   2. O_NOFOLLOW as well where it exists, so the refusal is explicit
    //      rather than incidental.
    //   3. a RANDOM suffix instead of the pid, so the path cannot be guessed
    //      and pre-created in the first place.
    //   4. the temporary is checked against the protected input like any other
    //      write target, and fstat'd after opening to confirm it is the
    //      regular file we just created and that we own it -- an open that
    //      succeeded is not proof of what it opened.
    string tmp;
    int fd = -1;
    for (int attempt = 0; attempt < 8 && fd < 0; attempt++) {
        char suffix[24];
        unsigned long r1 = (unsigned long) time(NULL) ^ ((unsigned long) getpid() << 16);
        // a second, independent draw so two processes in the same second differ
        unsigned long r2 = 0;
        {
            FILE *rf = fopen("/dev/urandom", "rb");
            if (rf) { if (fread(&r2, sizeof(r2), 1, rf) != 1) r2 = 0; fclose(rf); }
        }
        if (r2 == 0) r2 = (unsigned long) (attempt * 2654435761UL) ^ r1;
        snprintf(suffix, sizeof(suffix), ".tmp.%08lx%08lx",
                 (unsigned long)(r1 & 0xffffffffUL), (unsigned long)(r2 & 0xffffffffUL));
        tmp = path + suffix;

        // (4) the temporary is a write target, so it gets the same check
        if (!g_protectedInputPath.empty()
            && sameFileIdentity(tmp.c_str(), g_protectedInputPath.c_str()) != FILES_DISTINCT) {
            fprintf(stderr,
                "Error: the temporary output path '%s' is the same file as the input\n"
                "       '%s' (or that cannot be ruled out). Nothing has been written.\n",
                tmp.c_str(), g_protectedInputPath.c_str());
            return false;
        }

        int flags = O_WRONLY | O_CREAT | O_EXCL;
#ifdef O_NOFOLLOW
        flags |= O_NOFOLLOW;
#endif
#ifdef O_BINARY
        flags |= O_BINARY;
#endif
        // 0666, not 0600, so the PROCESS UMASK decides exactly as the
        // ofstream this replaced did. Measured: creating at 0600 delivered
        // reports mode 0600 where the pre-repair writer delivered 0644 -- a
        // silent behavioural divergence this repair has no business making. A
        // narrower temporary buys nothing here: another user who could read it
        // can read the finished report at the same mode a moment later, and at
        // 0644 cannot write to it at all.
        fd = open(tmp.c_str(), flags, 0666);
        if (fd < 0 && errno != EEXIST) {
            fprintf(stderr, "Error: could not create the temporary output file '%s' (%s).\n",
                    tmp.c_str(), strerror(errno));
            return false;
        }
    }
    if (fd < 0) {
        fprintf(stderr, "Error: could not create a temporary output file beside '%s' "
                        "after 8 attempts.\n", path.c_str());
        return false;
    }

    // (4) an open that succeeded is not proof of what it opened
    {
        struct stat st;
        if (fstat(fd, &st) != 0 || !S_ISREG(st.st_mode)
#ifndef _WIN32
            || st.st_uid != getuid() || st.st_nlink != 1
#endif
           ) {
            fprintf(stderr, "Error: the temporary output file '%s' is not the regular, "
                            "single-linked file just created; refusing to write.\n", tmp.c_str());
            close(fd);
            remove(tmp.c_str());
            return false;
        }
    }

    {
        const char *p = json.c_str();
        size_t left = json.size();
        bool wrote_ok = true;
        while (left > 0) {
            ssize_t n = write(fd, p, left);
            if (n <= 0) { wrote_ok = false; break; }
            p += n; left -= (size_t) n;
        }
        if (close(fd) != 0) wrote_ok = false;
        if (!wrote_ok) {
            fprintf(stderr, "Error: could not write the temporary output file '%s'.\n", tmp.c_str());
            remove(tmp.c_str());
            return false;
        }
    }

    // C24 (OC-57): PUT IT IN PLACE WITH THE PRIMITIVE THAT IS SPECIFIED TO
    // REPLACE, WHICH IS NOT THE SAME CALL ON EVERY PLATFORM.
    //
    // C08's whole argument is that rename(2) replaces an existing destination
    // atomically, so a reader finds either the previous complete report or the
    // new complete one and never a prefix. That is POSIX. Windows rename()
    // REFUSES an existing destination -- measured on windows-latest:
    //
    //     destination absent   rename rc=0   errno=0
    //     destination EXISTS   rename rc=-1  errno=17 (File exists)
    //
    // and C14 has already placed a placeholder at this path before any real
    // report is written, so on Windows the placeholder GUARANTEED that every
    // subsequent write failed and no tool could produce a -o report at all.
    // Two repairs, each sound under its own assumptions, jointly non-portable.
    //
    // MoveFileEx with MOVEFILE_REPLACE_EXISTING is the documented Win32
    // equivalent and is atomic from a reader's point of view;
    // MOVEFILE_WRITE_THROUGH makes it durable before returning, which is what
    // a report write wants. The POSIX path is untouched.
    //
    // THE ONE-LINER THAT MUST BE REFUSED: remove(path) before rename(). It
    // would "work" on both platforms and it reopens exactly the window C08
    // closed -- an interval in which the path does not exist at all, so a
    // reader finds nothing where it should find the previous report. A
    // regression justified by convenience is still a regression.
#ifdef _WIN32
    if (!MoveFileExA(tmp.c_str(), path.c_str(),
                     MOVEFILE_REPLACE_EXISTING | MOVEFILE_WRITE_THROUGH)) {
        fprintf(stderr, "Error: could not put the report in place at '%s' (Win32 error %lu).\n",
                path.c_str(), (unsigned long) GetLastError());
        remove(tmp.c_str());
        return false;
    }
#else
    if (rename(tmp.c_str(), path.c_str()) != 0) {
        fprintf(stderr, "Error: could not put the report in place at '%s'.\n", path.c_str());
        remove(tmp.c_str());
        return false;
    }
#endif

    return true;
}

string getCurrentTimestamp() {

    string timestamp = "";

    time_t t = time(NULL);
    tm* timePtr = localtime(&t);

    string mon = "";
    if ((timePtr->tm_mon + 1) < 10)
        mon = "0" + to_string(timePtr->tm_mon + 1);
    else
        mon = to_string(timePtr->tm_mon + 1);

    string day = "";
    if ((timePtr->tm_mday) < 10)
        day = "0" + to_string(timePtr->tm_mday);
    else
        day = to_string(timePtr->tm_mday);

    string hour = "";
    if ((timePtr->tm_hour) < 10)
        hour = "0" + to_string(timePtr->tm_hour);
    else
        hour = to_string(timePtr->tm_hour);

    string min = "";
    if ((timePtr->tm_min) < 10)
        min = "0" + to_string(timePtr->tm_min);
    else
        min = to_string(timePtr->tm_min);

    string sec = "";
    if ((timePtr->tm_sec) < 10)
        sec = "0" + to_string(timePtr->tm_sec);
    else
        sec = to_string(timePtr->tm_sec);


    timestamp = to_string(1900 + timePtr->tm_year) + mon + day + hour + min + sec;

    return timestamp;

}

void sha256_hash_string(unsigned char *hash, char *outputBuffer) {
    for (int i = 0; i < SHA256_DIGEST_LENGTH; i++) {
        sprintf(outputBuffer + (i * 2), "%02x", hash[i]);
    }
}

int sha256_file(const char *path, char *outputBuffer) {
    unsigned char *buffer=NULL;
    unsigned char digest[SHA256_DIGEST_LENGTH];
    size_t bytesRead;
    FILE *file=NULL;
    const int bufSize = 32768;
    int res = 0;
    EVP_MD_CTX *mdctx = NULL;

    // Fork hardening, and not a defect anyone upstream has accepted: the
    // read loop below runs
    // to EOF, so a character device never ends it and the tool hangs before
    // any size check runs; a FIFO blocks even earlier, inside fopen, waiting
    // for a writer. The file type is therefore established from the path,
    // before the file is opened. Upstream #259 records the behaviour;
    // @joshuaehill's view there is "I'm not sure this is a bug, it's more of
    // an observation that when the user does wildly wrong things, marginally
    // bad stuff might occur", so this is a local robustness choice rather
    // than a standards fix. A dataset has to be a regular file to be seekable
    // and sized, which read_file_subset already requires.
    {
        struct stat st;

        if(stat(path, &st) != 0) {
            perror("Can't stat the provided file name");
            res=-1;
            goto err;
        }

        if(!S_ISREG(st.st_mode)) {
            fprintf(stderr, "Error: '%s' is not a regular file.\n", path);
            res=-1;
            goto err;
        }
    }

    // open the file
    if((file = fopen(path, "rb"))==NULL) {
        perror("Can't open the provided file name");
	res=-1;
        goto err;
    }

    // Allocate the buffer
    if ( (buffer = new unsigned char[bufSize]) == NULL) {
        perror("Can't allocate the FILE I/O buffer");
	res=-1;
        goto err;
    }

    // Get a hash context.
    if ( (mdctx = EVP_MD_CTX_new()) == NULL ) {
        fprintf(stderr, "Can't allocate a new hash context.");
        res = -1;
        goto err;
    }

   // In this call, we implicitly fetch the SHA256 algorithm automatically from the relevant API
   // Setup the SHA256 context.
   if (EVP_DigestInit_ex(mdctx, EVP_sha256(), NULL) != 1) {
        fprintf(stderr, "Can't setup mdctx as a SHA256 context.");
        res = -1;
        goto err;
    }

    while(!feof(file)) {
        bytesRead = fread(buffer, 1, bufSize, file);

	if(ferror(file)) {
            perror("Error reading file for hashing");
            res=-1;
            goto err;
        }

        if(bytesRead > 0) {
	    if(EVP_DigestUpdate(mdctx, buffer, bytesRead)!=1) {
                fprintf(stderr, "Can't hash in new data.");
                res = -1;
                goto err;
            }
        }
    }

    // Finalize the hash.
    if(EVP_DigestFinal_ex(mdctx, digest, NULL)!=1) {
        fprintf(stderr, "Can't finalize the hash.");
        res = -1;
        goto err;
    }

    // Output the hash as a string.
    sha256_hash_string(digest, outputBuffer);
err:
    // Close the file.
    if(file) fclose(file);

    // De-allocate the buffer.
    if(buffer) delete[] buffer;

    // Free the hash context
    if(mdctx) EVP_MD_CTX_free(mdctx);

    return res;
}
#endif /* TESTRUNUTILS_H */
