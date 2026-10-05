// Verilated -*- C++ -*-
// DESCRIPTION: Verilator output: Design internal header
// See VOraRouterCore.h for the primary calling header

#ifndef VERILATED_VORAROUTERCORE___024ROOT_H_
#define VERILATED_VORAROUTERCORE___024ROOT_H_  // guard

#include "verilated.h"


class VOraRouterCore__Syms;

class alignas(VL_CACHE_LINE_BYTES) VOraRouterCore___024root final : public VerilatedModule {
  public:

    // DESIGN SPECIFIC STATE
    VL_IN8(clk,0,0);
    VL_IN8(reset,0,0);
    VL_IN8(io_inp_valid,0,0);
    VL_OUT8(io_inp_ready,0,0);
    VL_OUT8(io_out_valid,0,0);
    VL_IN8(io_out_ready,0,0);
    VL_OUT8(io_eject_valid,0,0);
    VL_IN8(io_eject_ready,0,0);
    CData/*0:0*/ OraRouterCore__DOT__active;
    CData/*1:0*/ OraRouterCore__DOT__outVc;
    CData/*0:0*/ OraRouterCore__DOT__doChain;
    CData/*0:0*/ OraRouterCore__DOT__hdrFwd;
    CData/*0:0*/ OraRouterCore__DOT__io_inp_fire;
    CData/*0:0*/ OraRouterCore__DOT__when_OraRouterCore_l114;
    CData/*0:0*/ OraRouterCore__DOT____VdfgTmp_he29cc4cd__0;
    CData/*0:0*/ __VstlFirstIteration;
    CData/*0:0*/ __VicoFirstIteration;
    CData/*0:0*/ __Vtrigprevexpr___TOP__clk__0;
    CData/*0:0*/ __Vtrigprevexpr___TOP__reset__0;
    CData/*0:0*/ __VactContinue;
    VL_IN(io_inp_payload,31,0);
    VL_OUT(io_out_payload,31,0);
    VL_OUT(io_eject_payload,31,0);
    IData/*31:0*/ OraRouterCore__DOT___zz_io_out_payload_3;
    IData/*31:0*/ OraRouterCore__DOT___zz_io_out_payload_4;
    IData/*31:0*/ OraRouterCore__DOT___zz_outVc_2;
    IData/*31:0*/ __VactIterCount;
    VlTriggerVec<1> __VstlTriggered;
    VlTriggerVec<1> __VicoTriggered;
    VlTriggerVec<1> __VactTriggered;
    VlTriggerVec<1> __VnbaTriggered;

    // INTERNAL VARIABLES
    VOraRouterCore__Syms* const vlSymsp;

    // CONSTRUCTORS
    VOraRouterCore___024root(VOraRouterCore__Syms* symsp, const char* v__name);
    ~VOraRouterCore___024root();
    VL_UNCOPYABLE(VOraRouterCore___024root);

    // INTERNAL METHODS
    void __Vconfigure(bool first);
};


#endif  // guard
