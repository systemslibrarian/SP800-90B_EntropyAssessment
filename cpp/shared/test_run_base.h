#ifndef TESTRUN_H
#define TESTRUN_H

#include "utils.h"
#include <string>
#include <json/json.h>

using namespace std;

class TestRunBase {
public:
    string timestamp;
    string sha256;
    string filename;
    int errorLevel = 0;
    string errorMsg;
    string type;
    string commandline;
    // True only when a run below the SP 800-90B Section 3.1.1 minimum sample
    // count was allowed to proceed by EA_ALLOW_SHORT_DATASET. Such a run is
    // not a compliant assessment, so any report it produces says so.
    bool nonCompliantShortDataset = false;
    // Subset provenance, recorded only when -l was used. sha256 stays the hash
    // of the WHOLE file: @joshuaehill on #260, "I think that the SHA sum acting
    // on the file is the most reasonable behavior ... the file hash is more
    // useful in this setting." These three fields are what make the assessed
    // bytes identifiable alongside it, since the report otherwise did not say
    // that only part of the file was read, nor how much of it was actually
    // obtained when the last block was short.
    // The symbol width the assessment actually used, and whether it was taken
    // from the command line or inferred from the data. @joshuaehill on #254:
    // "Certainly reporting the evident symbol width in JSON would be useful."
    // The inference itself is deliberately unchanged, and the warning that the
    // same issue proposed is deliberately not added: "Reporting this 'not a
    // mapping' as a warning isn't useful."
    int bitsPerSymbol = 0;
    bool bitsPerSymbolInferred = false;
    bool subsetRequested = false;
    unsigned long subsetIndex = 0;
    unsigned long subsetRequestedSamples = 0;
    long subsetActualSamples = 0;

protected:
    Json::Value GetBaseJson() {
        Json::Value baseJson;
        baseJson["dateTimeStamp"] = timestamp;
        baseJson["commandline"] = commandline;
        baseJson["errorLevel"] = errorLevel;
        baseJson["type"] = type;
        baseJson["toolVersion"] = VERSION;

        if (errorLevel != 0){
            baseJson["errorMessage"] = errorMsg;
        }
        if (nonCompliantShortDataset) {
            baseJson["nonCompliantShortDataset"] = true;
        }
        if (bitsPerSymbol > 0) {
            baseJson["bitsPerSymbol"] = bitsPerSymbol;
            baseJson["bitsPerSymbolInferred"] = bitsPerSymbolInferred;
        }
        if (subsetRequested) {
            baseJson["subsetIndex"] = (Json::UInt64)subsetIndex;
            baseJson["subsetRequestedSamples"] = (Json::UInt64)subsetRequestedSamples;
            baseJson["subsetActualSamples"] = (Json::Int64)subsetActualSamples;
        }
        if(!filename.empty()) {
            baseJson["filename"] = filename;
        }
        if(!sha256.empty()) {
            baseJson["sha256"] = sha256;
        }
        return baseJson;
    }
};
#endif /* TESTRUN_H */
