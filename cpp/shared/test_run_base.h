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
