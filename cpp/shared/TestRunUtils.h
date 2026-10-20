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
    const string tmp = path + ".tmp." + std::to_string((long)getpid());

    {
        ofstream output;
        output.open(tmp.c_str(), std::ios::out | std::ios::trunc | std::ios::binary);
        if (!output) {
            fprintf(stderr, "Error: could not create the temporary output file '%s'.\n", tmp.c_str());
            return false;
        }

        output << json;
        output.close();

        // close() flushes, so a device-full or I/O error shows up here.
        if (!output) {
            fprintf(stderr, "Error: could not write the temporary output file '%s'.\n", tmp.c_str());
            remove(tmp.c_str());
            return false;
        }
    }

    if (rename(tmp.c_str(), path.c_str()) != 0) {
        fprintf(stderr, "Error: could not put the report in place at '%s'.\n", path.c_str());
        remove(tmp.c_str());
        return false;
    }

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
