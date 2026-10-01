#ifndef TESTRUNUTILS_H
#define TESTRUNUTILS_H

#include <cstdlib>
#include <string.h>
#include <string>
#include <fstream>
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
bool writeJsonReport(const string &path, const string &json) {
    ofstream output;

    output.open(path.c_str());
    if (!output) {
        fprintf(stderr, "Error: could not open the output file '%s'.\n", path.c_str());
        return false;
    }

    output << json;
    output.close();

    // close() flushes, so a device-full or I/O error shows up here.
    if (!output) {
        fprintf(stderr, "Error: could not write the output file '%s'.\n", path.c_str());
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

    // Fork hardening, not a defect NIST has accepted: the read loop below runs
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
