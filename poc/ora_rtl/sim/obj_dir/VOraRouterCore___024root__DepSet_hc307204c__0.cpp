// Verilated -*- C++ -*-
// DESCRIPTION: Verilator output: Design implementation internals
// See VOraRouterCore.h for the primary calling header

#include "VOraRouterCore__pch.h"
#include "VOraRouterCore__Syms.h"
#include "VOraRouterCore___024root.h"

#ifdef VL_DEBUG
VL_ATTR_COLD void VOraRouterCore___024root___dump_triggers__ico(VOraRouterCore___024root* vlSelf);
#endif  // VL_DEBUG

void VOraRouterCore___024root___eval_triggers__ico(VOraRouterCore___024root* vlSelf) {
    if (false && vlSelf) {}  // Prevent unused
    VOraRouterCore__Syms* const __restrict vlSymsp VL_ATTR_UNUSED = vlSelf->vlSymsp;
    VL_DEBUG_IF(VL_DBG_MSGF("+    VOraRouterCore___024root___eval_triggers__ico\n"); );
    // Body
    vlSelf->__VicoTriggered.set(0U, (IData)(vlSelf->__VicoFirstIteration));
#ifdef VL_DEBUG
    if (VL_UNLIKELY(vlSymsp->_vm_contextp__->debug())) {
        VOraRouterCore___024root___dump_triggers__ico(vlSelf);
    }
#endif
}

#ifdef VL_DEBUG
VL_ATTR_COLD void VOraRouterCore___024root___dump_triggers__act(VOraRouterCore___024root* vlSelf);
#endif  // VL_DEBUG

void VOraRouterCore___024root___eval_triggers__act(VOraRouterCore___024root* vlSelf) {
    if (false && vlSelf) {}  // Prevent unused
    VOraRouterCore__Syms* const __restrict vlSymsp VL_ATTR_UNUSED = vlSelf->vlSymsp;
    VL_DEBUG_IF(VL_DBG_MSGF("+    VOraRouterCore___024root___eval_triggers__act\n"); );
    // Body
    vlSelf->__VactTriggered.set(0U, (((IData)(vlSelf->clk) 
                                      & (~ (IData)(vlSelf->__Vtrigprevexpr___TOP__clk__0))) 
                                     | ((IData)(vlSelf->reset) 
                                        & (~ (IData)(vlSelf->__Vtrigprevexpr___TOP__reset__0)))));
    vlSelf->__Vtrigprevexpr___TOP__clk__0 = vlSelf->clk;
    vlSelf->__Vtrigprevexpr___TOP__reset__0 = vlSelf->reset;
#ifdef VL_DEBUG
    if (VL_UNLIKELY(vlSymsp->_vm_contextp__->debug())) {
        VOraRouterCore___024root___dump_triggers__act(vlSelf);
    }
#endif
}
