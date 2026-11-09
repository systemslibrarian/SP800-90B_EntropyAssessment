#ifndef NONIIDTESTCASE_H
#define NONIIDTESTCASE_H

#include <string>
#include <json/json.h>

#include "../shared/test_case_base.h"

using namespace std;

class NonIidTestCase : public TestCaseBase {
public:

    double bin_t_tuple_res = -1.0;
    double t_tuple_res = -1.0;
    double bin_lrs_res = -1.0;
    double lrs_res = -1.0;
    double h_r = -1.0;
    double h_c = -1.0;
    double h_i = -1.0;
    // ea_restart runs each literal estimator on the rows and again on the
    // columns of the restart matrix, and either run can decline the way F05
    // records for ea_non_iid (test_case_base.h, literal_not_run). Until
    // 2026-11-08 the declined half simply left h_r or h_c out, so H_r or H_c
    // was a minimum over fewer estimators than SP 800-90B 6.2 lists with
    // nothing in the report saying so. These say which half declined. Same
    // rule as F05: a statement of fact about the run, not an error (audit
    // 2026-11-07, PROV-10).
    bool row_not_run = false;
    bool col_not_run = false;
    double n_in = -1.0;
    double n_out = -1.0;
    double nw = -1.0;
    double h_in = -1.0;
    double h_out = -1.0;
    double h_p = -1.0;
    //bool vetted = true;
    
    Json::Value GetAsJson() {
        Json::Value json = TestCaseBase::GetBaseJson();
        
        if(bin_t_tuple_res != -1)
            json["binTTupleRes"] = bin_t_tuple_res;
        if(t_tuple_res != -1)
            json["tTupleRes"] = t_tuple_res;
        if(bin_lrs_res != -1)
            json["binLrsRes"] = bin_lrs_res;
        if(lrs_res != -1)
            json["lrsRes"] = lrs_res;
        if(h_r != -1)
            json["h_r"] = h_r;
        if(h_c != -1)
            json["h_c"] = h_c;
        if(row_not_run)
            json["rowEstimateNotRun"] = true;
        if(col_not_run)
            json["columnEstimateNotRun"] = true;
        if(h_i != -1)
            json["h_i"] = h_i;
        if(n_in != -1)
            json["n_in"] = n_in;
        if(n_out != -1)
            json["n_out"] = n_out;
        if(nw != -1)
            json["nw"] = nw;
        if(h_in != -1)
            json["h_in"] = h_in;
        if(h_out != -1)
            json["h_out"] = h_out;
        if(h_p != -1)
            json["h_p"] = h_p;
        //if(vetted != -1)
        //    json["vetted"] = vetted;
        
        return json;
    }
};
#endif /* NONIIDTESTCASE_H */
