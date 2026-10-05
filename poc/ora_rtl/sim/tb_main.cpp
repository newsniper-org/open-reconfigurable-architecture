// ORA-N co-simulation testbench (Verilator)
//
// Drives OraRouterCore cycle-by-cycle with a flit sequence. Combinational
// outputs are sampled BEFORE the rising edge (matching the Python model's
// evaluate-then-commit semantics), then the edge commits register updates.
//
// argv: <stimulus.hex> <trace.out> [ready.pattern]
//   ready.pattern: per-cycle out_ready bits, repeating (default "1").
//   STALL events are logged when the DUT does not accept the offered flit.

#include "VOraRouterCore.h"
#include "verilated.h"
#include <cstdio>
#include <cstdint>
#include <cstring>
#include <vector>

static const int MAX_CYCLES = 8192;

int main(int argc, char **argv) {
    Verilated::commandArgs(argc, argv);
    auto *dut = new VOraRouterCore;

    FILE *fin = fopen(argv[1], "r");
    FILE *fout = fopen(argv[2], "w");
    if (!fin || !fout) { fprintf(stderr, "io error\n"); return 2; }

    // Optional out_ready pattern (repeating bits, default always ready)
    const char *rdy_pat = (argc > 3) ? argv[3] : "1";
    int rdy_len = strlen(rdy_pat);

    std::vector<uint32_t> stimulus;
    uint32_t w;
    while (fscanf(fin, "%x", &w) == 1) stimulus.push_back(w);
    fclose(fin);

    // Reset
    dut->clk = 0; dut->reset = 1;
    dut->io_inp_valid = 0; dut->io_inp_payload = 0;
    dut->io_out_ready = 1; dut->io_eject_ready = 1;
    for (int i = 0; i < 4; i++) { dut->clk = !dut->clk; dut->eval(); }
    dut->reset = 0;
    dut->clk = 0; dut->eval();

    size_t idx = 0;
    bool have_pending = false;
    uint32_t pending = 0;
    int idle_after_done = 0;

    for (int cyc = 0; cyc < MAX_CYCLES; cyc++) {
        // Drive the out_ready pattern for this cycle
        int out_rdy = rdy_pat[cyc % rdy_len] - '0';
        dut->io_out_ready = out_rdy;
        dut->io_eject_ready = 1;

        // Offer the pending (or next) flit
        if (!have_pending && idx < stimulus.size()) {
            pending = stimulus[idx];
            have_pending = true;
        }
        dut->io_inp_valid = have_pending ? 1 : 0;
        dut->io_inp_payload = have_pending ? pending : 0;

        // Settle combinational logic (pre-edge state)
        dut->eval();

        // Sample this cycle's combinational outputs (pre-edge)
        uint32_t outv = 0, ejecv = 0;
        bool out_fired = dut->io_out_valid && dut->io_out_ready;
        bool ejec_fired = dut->io_eject_valid && dut->io_eject_ready;
        if (out_fired) outv = dut->io_out_payload;
        if (ejec_fired) ejecv = dut->io_eject_payload;

        // Did the DUT accept the offered flit?
        bool accepted = have_pending && dut->io_inp_ready;

        if (have_pending && !accepted) {
            fprintf(fout, "%d STALL\n", cyc);
        } else if (out_fired || ejec_fired) {
            fprintf(fout, "%d", cyc);
            if (out_fired) fprintf(fout, " FWD %08x", outv);
            if (ejec_fired) fprintf(fout, " EJECT %08x", ejecv);
            fprintf(fout, "\n");
        }

        // Rising edge: commit register updates
        dut->clk = 1; dut->eval();
        // Falling edge: settle
        dut->clk = 0; dut->eval();

        if (have_pending && accepted) {
            have_pending = false;
            idx++;
        }

        // Termination: all stimulus consumed, no pending, outputs quiet
        if (!have_pending && idx >= stimulus.size()) {
            bool quiet = (!dut->io_out_valid || !dut->io_out_ready) &&
                         (!dut->io_eject_valid || !dut->io_eject_ready);
            if (quiet) {
                idle_after_done++;
                if (idle_after_done >= 4) break;
            } else {
                idle_after_done = 0;
            }
        }
    }

    fclose(fout);
    delete dut;
    return 0;
}
