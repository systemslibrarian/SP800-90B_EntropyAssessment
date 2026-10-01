#ifndef TESTCASE_H
#define TESTCASE_H

#include <cstdlib>
#include <string>
#include <json/json.h>

using namespace std;

class TestCaseBase {
public:
    double h_original = -1.0;
    double h_bitstring = -1.0;
    double h_assessed = -1.0;

    double mcv_estimate_mode = -1.0;
    double mcv_estimate_p_hat = -1.0;
    double mcv_estimate_p_u = -1.0;
    bool literal_mcv_estimate = false;
    
    double ret_min_entropy = -1.0;
    double data_word_size = -1.0;

    string testCaseNumber;

    // Set when an estimator was applicable to this dataset but could not
    // produce a value, as opposed to simply not applying to this branch. The
    // JSON otherwise omits both cases identically, so a consumer could not
    // tell that the reported minimum had been taken over fewer estimators
    // than the standard lists, which can only make the figure higher.
    //
    // This is deliberately not an error. @joshuaehill on #255: "There are
    // instances where binary estimators can't produce an estimate but where
    // the result is not an error ... This is not an error, and should not be
    // flagged as one." errorLevel is untouched; this is a statement of fact
    // about the run.
    bool literal_not_run = false;
    bool bitstring_not_run = false;

protected:
    Json::Value GetBaseJson() {
        Json::Value baseJson;
        baseJson["testCaseDesc"] = testCaseNumber;
        if(literal_not_run)
            baseJson["literalEstimateNotRun"] = true;
        if(bitstring_not_run)
            baseJson["bitstringEstimateNotRun"] = true;
        if(ret_min_entropy != -1)
            baseJson["retMinEntropy"] = ret_min_entropy;
        if(data_word_size != -1)
            baseJson["dataWordSize"] = data_word_size;
        if(h_original != -1)
            baseJson["hOriginal"] = h_original;
        if(h_bitstring != -1)
            baseJson["hBitstring"] = h_bitstring;
        if(h_assessed != -1)
            baseJson["hAssessed"] = h_assessed;

        if(mcv_estimate_mode != -1)
            baseJson["mcvEstimateMode"] = mcv_estimate_mode;
        if(mcv_estimate_p_hat != -1)
            baseJson["mcvEstimatePHat"] = mcv_estimate_p_hat;
        if(mcv_estimate_p_u != -1)
            baseJson["mcvEstimatePU"] = mcv_estimate_p_u;

        // not needed in every test case, easier to exclude for now
        //baseJson["mcvEstimate"] = literal_mcv_estimate ? "literal" : "bitstring";

        return baseJson;
    }
};
#endif /* TESTCASE_H */
