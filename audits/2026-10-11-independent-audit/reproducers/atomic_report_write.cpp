// oac-13: is the report write atomic from a reader's point of view?
//
// Both implementations are compiled in: OLD streams straight into the
// operator's path, NEW writes a sibling temporary and renames over it. The
// harness pre-places a known-good report, writes a large one over it, and is
// killed part-way. The question is what a reader finds at the path afterwards:
// the previous complete report, the new complete report, or a PREFIX.
//
//   atomic_report_write old|new <path> <megabytes>
#include <cstdio>
#include <cstdlib>
#include <string>
#include <fstream>
#include <unistd.h>
using namespace std;

static bool write_old(const string &path, const string &json) {
    ofstream o; o.open(path.c_str());
    if (!o) return false;
    o << json; o.close();
    return (bool)o;
}
static bool write_new(const string &path, const string &json) {
    const string tmp = path + ".tmp." + std::to_string((long)getpid());
    { ofstream o; o.open(tmp.c_str(), ios::out | ios::trunc | ios::binary);
      if (!o) return false;
      o << json; o.close();
      if (!o) { remove(tmp.c_str()); return false; } }
    if (rename(tmp.c_str(), path.c_str()) != 0) { remove(tmp.c_str()); return false; }
    return true;
}
int main(int argc, char **argv) {
    if (argc != 4) { fprintf(stderr, "usage: %s old|new <path> <MB>\n", argv[0]); return 2; }
    const string mode = argv[1], path = argv[2];
    const size_t mb = (size_t)atol(argv[3]);
    // A syntactically valid JSON document whose completeness is checkable: the
    // closing brace only exists if the whole thing was written.
    string json = "{\"pad\":\"";
    json.append(mb * 1024u * 1024u, 'x');
    json += "\",\"complete\":true}";
    bool ok = (mode == "old") ? write_old(path, json) : write_new(path, json);
    printf("%s write returned %d\n", mode.c_str(), (int)ok);
    return ok ? 0 : 1;
}
