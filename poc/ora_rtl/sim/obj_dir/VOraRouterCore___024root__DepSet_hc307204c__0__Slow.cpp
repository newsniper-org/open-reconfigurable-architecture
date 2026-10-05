// Verilated -*- C++ -*-
// DESCRIPTION: Verilator output: Design implementation internals
// See VOraRouterCore.h for the primary calling header

#include "VOraRouterCore__pch.h"
#include "VOraRouterCore__Syms.h"
#include "VOraRouterCore___024root.h"

#ifdef VL_DEBUG
VL_ATTR_COLD void VOraRouterCore___024root___dump_triggers__stl(VOraRouterCore___024root* vlSelf);
#endif  // VL_DEBUG

VL_ATTR_COLD void VOraRouterCore___024root___eval_triggers__stl(VOraRouterCore___024root* vlSelf) {
    if (false && vlSelf) {}  // Prevent unused
    VOraRouterCore__Syms* const __restrict vlSymsp VL_ATTR_UNUSED = vlSelf->vlSymsp;
    VL_DEBUG_IF(VL_DBG_MSGF("+    VOraRouterCore___024root___eval_triggers__stl\n"); );
    // Body
    vlSelf->__VstlTriggered.set(0U, (IData)(vlSelf->__VstlFirstIteration));
#ifdef VL_DEBUG
    if (VL_UNLIKELY(vlSymsp->_vm_contextp__->debug())) {
        VOraRouterCore___024root___dump_triggers__stl(vlSelf);
    }
#endif
}
