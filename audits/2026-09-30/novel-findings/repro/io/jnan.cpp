#include <json/json.h>
#include <cmath>
#include <iostream>
int main(){ Json::Value v; v["nan"]=NAN; v["inf"]=INFINITY; v["ninf"]=-INFINITY; v["nzero"]=-0.0; v["big"]=1e308; Json::StyledWriter w; std::cout<<w.write(v); }
