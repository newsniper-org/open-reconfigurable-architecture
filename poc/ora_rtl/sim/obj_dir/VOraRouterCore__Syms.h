// Verilated -*- C++ -*-
// DESCRIPTION: Verilator output: Symbol table internal header
//
// Internal details; most calling programs do not need this header,
// unless using verilator public meta comments.

#ifndef VERILATED_VORAROUTERCORE__SYMS_H_
#define VERILATED_VORAROUTERCORE__SYMS_H_  // guard

#include "verilated.h"

// INCLUDE MODEL CLASS

#include "VOraRouterCore.h"

// INCLUDE MODULE CLASSES
#include "VOraRouterCore___024root.h"

// SYMS CLASS (contains all model state)
class alignas(VL_CACHE_LINE_BYTES)VOraRouterCore__Syms final : public VerilatedSyms {
  public:
    // INTERNAL STATE
    VOraRouterCore* const __Vm_modelp;
    VlDeleter __Vm_deleter;
    bool __Vm_didInit = false;

    // MODULE INSTANCE STATE
    VOraRouterCore___024root       TOP;

    // CONSTRUCTORS
    VOraRouterCore__Syms(VerilatedContext* contextp, const char* namep, VOraRouterCore* modelp);
    ~VOraRouterCore__Syms();

    // METHODS
    const char* name() { return TOP.name(); }
};

#endif  // guard
