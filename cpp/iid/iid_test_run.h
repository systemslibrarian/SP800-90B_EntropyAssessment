#ifndef IIDTESTRUN_H
#define IIDTESTRUN_H

#include <string>
#include <vector>
#include "../shared/test_run_base.h"
#include "iid_test_case.h"

using namespace std;

class IidTestRun : public TestRunBase {
public:
    string GetAsJson() {
        Json::Value json = TestRunBase::GetBaseJson();
        // "IID" is a verdict, not merely the mode selected on the command
        // line. Before #252 it was a constant true even when required tests
        // failed. assessmentComplete distinguishes an explicit failed verdict
        // from an input/tool error before the battery completed.
        json["IID"] = iidClaimAccepted;
        json["assessmentComplete"] = assessmentComplete;
        json["assessmentMode"] = "IID";

        Json::Value testCasesJson;
        for (int i = 0; i < (int)testCases.size(); i++){
            testCasesJson[i] = testCases[i].GetAsJson();
        }

        json["testCases"] = testCasesJson;

        Json::StyledWriter styled;
        return styled.write(json);
    }

    bool iidClaimAccepted = false;
    bool assessmentComplete = false;
    vector<IidTestCase> testCases;
};
#endif /* IIDTESTRUN_H */
