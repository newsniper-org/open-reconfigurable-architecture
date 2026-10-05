// ORA-N 2-router chain co-simulation testbench (Verilator)
//
// Two OraRouter instances, wired R0.EAST(2) <-> R1.WEST(4). Each router has
// a local injector on port 0 that offers one flit per cycle, held until the
// router's input FIFO for the flit's VC reports a credit. The per-cycle
// protocol and the trace format are identical to gen_chain_scenarios.py:
//
//   1. Credits: outCredit of each router = inCredit of its link partner
//      (register-derived, valid since the previous edge).
//   2. Injection decision from the local port's inCredit.
//   3. eval -> outValid/outData settle (they depend on registers + credits).
//   4. Link inputs: inValid/inData of each router = partner's outputs; eval.
//   5. Log: per router ascending, INJ line then ports ascending.
//   6. Rising edge commits FIFOs, locks, RR pointers.
//
// argv: <scenario.chain.stim> <trace.out>
//   stim format: "cycles N" then "<router> <hex flit>" lines (per-router order)

#include "VOraRouter.h"
#include "verilated.h"
#include <cstdint>
#include <cstdio>
#include <deque>
#include <vector>

static const int NUM_ROUTERS = 2;
static const int NUM_PORTS = 7;
static const int PORT_EAST = 2;
static const int PORT_WEST = 4;

struct Link {
    int a, a_port, b, b_port; // a.out[a_port] -> b.in[b_port]
};

// Both directions of the single physical link
static const Link LINKS[] = {
    {0, PORT_EAST, 1, PORT_WEST},
    {1, PORT_WEST, 0, PORT_EAST},
};

static int flit_vc(uint32_t f) {
    return ((f >> 30) & 3u) == 3u ? 0 : (int)((f >> 28) & 3u);
}

static void eval_all(VOraRouter **r) {
    for (int i = 0; i < NUM_ROUTERS; i++) r[i]->eval();
}

int main(int argc, char **argv) {
    Verilated::commandArgs(argc, argv);
    if (argc < 3) { fprintf(stderr, "usage: %s <stim> <trace>\n", argv[0]); return 2; }

    FILE *fin = fopen(argv[1], "r");
    FILE *fout = fopen(argv[2], "w");
    if (!fin || !fout) { fprintf(stderr, "io error\n"); return 2; }

    int cycles = 0;
    if (fscanf(fin, "cycles %d", &cycles) != 1) { fprintf(stderr, "bad stim header\n"); return 2; }
    std::deque<uint32_t> pending[NUM_ROUTERS];
    int rid;
    unsigned int w;
    while (fscanf(fin, "%d %x", &rid, &w) == 2) {
        if (rid < 0 || rid >= NUM_ROUTERS) { fprintf(stderr, "bad router id\n"); return 2; }
        pending[rid].push_back((uint32_t)w);
    }
    fclose(fin);

    VOraRouter *r[NUM_ROUTERS];
    for (int i = 0; i < NUM_ROUTERS; i++) {
        r[i] = new VOraRouter;
        r[i]->clk = 0;
        r[i]->reset = 1;
        r[i]->io_inValid = 0;
        r[i]->io_outCredit = 0;
        for (int p = 0; p < NUM_PORTS; p++) r[i]->io_inData[p] = 0;
    }
    for (int k = 0; k < 4; k++) {
        for (int i = 0; i < NUM_ROUTERS; i++) r[i]->clk = !r[i]->clk;
        eval_all(r);
    }
    for (int i = 0; i < NUM_ROUTERS; i++) { r[i]->reset = 0; r[i]->clk = 0; }
    eval_all(r);

    for (int cyc = 0; cyc < cycles; cyc++) {
        // 1. Credits across links (unconnected ports: no credit)
        uint32_t out_credit[NUM_ROUTERS] = {0};
        for (const Link &l : LINKS) {
            uint32_t partner = r[l.b]->io_inCredit;
            uint32_t bits = (partner >> (l.b_port * 2)) & 3u;
            out_credit[l.a] |= bits << (l.a_port * 2);
        }
        for (int i = 0; i < NUM_ROUTERS; i++) r[i]->io_outCredit = out_credit[i];

        // 2. Local injection decision from start-of-cycle credit
        bool inj[NUM_ROUTERS] = {false};
        uint32_t inj_flit[NUM_ROUTERS] = {0};
        for (int i = 0; i < NUM_ROUTERS; i++) {
            if (pending[i].empty()) continue;
            uint32_t f = pending[i].front();
            int vc = flit_vc(f);
            if ((r[i]->io_inCredit >> (0 * 2 + vc)) & 1u) {
                inj[i] = true;
                inj_flit[i] = f;
                pending[i].pop_front();
            }
        }
        uint32_t in_valid[NUM_ROUTERS] = {0};
        for (int i = 0; i < NUM_ROUTERS; i++) {
            if (inj[i]) {
                in_valid[i] |= 1u;
                r[i]->io_inData[0] = inj_flit[i];
            } else {
                r[i]->io_inData[0] = 0;
            }
            r[i]->io_inValid = in_valid[i];
        }

        // 3. Settle router outputs
        eval_all(r);

        // 4. Drive link inputs from partner outputs, then settle again
        for (const Link &l : LINKS) {
            bool v = (r[l.a]->io_outValid >> l.a_port) & 1u;
            if (v) in_valid[l.b] |= 1u << l.b_port;
            r[l.b]->io_inData[l.b_port] = v ? (uint32_t)r[l.a]->io_outData[l.a_port] : 0u;
        }
        for (int i = 0; i < NUM_ROUTERS; i++) r[i]->io_inValid = in_valid[i];
        eval_all(r);

        // 5. Log pre-edge events
        for (int i = 0; i < NUM_ROUTERS; i++) {
            if (inj[i]) fprintf(fout, "%d R%d INJ %08x\n", cyc, i, inj_flit[i]);
            for (int p = 0; p < NUM_PORTS; p++) {
                if ((r[i]->io_outValid >> p) & 1u)
                    fprintf(fout, "%d R%d P%d %08x\n", cyc, i, p, (uint32_t)r[i]->io_outData[p]);
            }
        }

        // 6. Clock edge
        for (int i = 0; i < NUM_ROUTERS; i++) r[i]->clk = 1;
        eval_all(r);
        for (int i = 0; i < NUM_ROUTERS; i++) r[i]->clk = 0;
        eval_all(r);
    }

    int left = 0;
    for (int i = 0; i < NUM_ROUTERS; i++) left += (int)pending[i].size();
    if (left) fprintf(stderr, "warning: %d flits never injected\n", left);

    fclose(fout);
    for (int i = 0; i < NUM_ROUTERS; i++) delete r[i];
    return 0;
}
