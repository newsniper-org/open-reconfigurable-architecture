// Verilated -*- C++ -*-
// DESCRIPTION: Verilator output: Symbol table implementation internals

#include "VOraRouterCore__pch.h"
#include "VOraRouterCore.h"
#include "VOraRouterCore___024root.h"

// FUNCTIONS
VOraRouterCore__Syms::~VOraRouterCore__Syms()
{
}

VOraRouterCore__Syms::VOraRouterCore__Syms(VerilatedContext* contextp, const char* namep, VOraRouterCore* modelp)
    : VerilatedSyms{contextp}
    // Setup internal state of the Syms class
    , __Vm_modelp{modelp}
    // Setup module instances
    , TOP{this, namep}
{
    // Configure time unit / time precision
    _vm_contextp__->timeunit(-9);
    _vm_contextp__->timeprecision(-12);
    // Setup each module's pointers to their submodules
    // Setup each module's pointer back to symbol table (for public functions)
    TOP.__Vconfigure(true);
}
