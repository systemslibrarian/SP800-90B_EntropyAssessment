// Harness: call ea_restart's own simulateBound() (unmodified source, included verbatim) and print X_cutoff.
#define main restart_main_orig
#include "restart_main.cpp"
#undef main
int main(int argc, char **argv) {
    double H_I = atof(argv[1]);
    int k = atoi(argv[2]);
    unsigned long rounds = strtoul(argv[3], NULL, 10);
    int reps = atoi(argv[4]);
    double alpha = 1 - exp(log(0.99) / (1000 + 1000));
    for (int i = 0; i < reps; i++) {
        int c = simulateBound(alpha, k, H_I, rounds);
        printf("H_I=%.17g k=%d rounds=%lu threads=%d X_cutoff=%d\n", H_I, k, rounds, omp_get_max_threads(), c);
        fflush(stdout);
    }
    return 0;
}
