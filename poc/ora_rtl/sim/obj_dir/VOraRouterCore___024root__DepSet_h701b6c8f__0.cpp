// Verilated -*- C++ -*-
// DESCRIPTION: Verilator output: Design implementation internals
// See VOraRouterCore.h for the primary calling header

#include "VOraRouterCore__pch.h"
#include "VOraRouterCore___024root.h"

VL_INLINE_OPT void VOraRouterCore___024root___ico_sequent__TOP__0(VOraRouterCore___024root* vlSelf) {
    if (false && vlSelf) {}  // Prevent unused
    VOraRouterCore__Syms* const __restrict vlSymsp VL_ATTR_UNUSED = vlSelf->vlSymsp;
    VL_DEBUG_IF(VL_DBG_MSGF("+    VOraRouterCore___024root___ico_sequent__TOP__0\n"); );
    // Init
    CData/*0:0*/ OraRouterCore__DOT__aerFwd;
    OraRouterCore__DOT__aerFwd = 0;
    IData/*31:0*/ OraRouterCore__DOT___zz_io_out_payload;
    OraRouterCore__DOT___zz_io_out_payload = 0;
    CData/*0:0*/ OraRouterCore__DOT____VdfgExtracted_hca4f6894__0;
    OraRouterCore__DOT____VdfgExtracted_hca4f6894__0 = 0;
    CData/*2:0*/ OraRouterCore__DOT____VdfgExtracted_h2347b4b0__0;
    OraRouterCore__DOT____VdfgExtracted_h2347b4b0__0 = 0;
    CData/*0:0*/ OraRouterCore__DOT____VdfgTmp_h5cf3681f__0;
    OraRouterCore__DOT____VdfgTmp_h5cf3681f__0 = 0;
    // Body
    vlSelf->io_eject_payload = vlSelf->io_inp_payload;
    vlSelf->OraRouterCore__DOT___zz_io_out_payload_4 
        = vlSelf->io_inp_payload;
    vlSelf->OraRouterCore__DOT___zz_io_out_payload_4 
        = ((0xf00fffffU & vlSelf->OraRouterCore__DOT___zz_io_out_payload_4) 
           | ((0xc000000U & (((vlSelf->io_inp_payload 
                               >> 0x1aU) - (IData)(1U)) 
                             << 0x1aU)) | (0x700000U 
                                           & (vlSelf->io_inp_payload 
                                              >> 3U))));
    OraRouterCore__DOT___zz_io_out_payload = vlSelf->io_inp_payload;
    OraRouterCore__DOT___zz_io_out_payload = ((0xcfffffffU 
                                               & OraRouterCore__DOT___zz_io_out_payload) 
                                              | ((IData)(vlSelf->OraRouterCore__DOT__outVc) 
                                                 << 0x1cU));
    OraRouterCore__DOT____VdfgExtracted_h2347b4b0__0 
        = ((0U == (7U & (vlSelf->io_inp_payload >> 0x15U)))
            ? 7U : (7U & ((7U == (7U & (vlSelf->io_inp_payload 
                                        >> 0x15U)))
                           ? (vlSelf->io_inp_payload 
                              >> 0x15U) : ((vlSelf->io_inp_payload 
                                            >> 0x15U) 
                                           - (IData)(1U)))));
    vlSelf->OraRouterCore__DOT____VdfgTmp_he29cc4cd__0 
        = (IData)((0U == (0xce000000U & vlSelf->io_inp_payload)));
    OraRouterCore__DOT____VdfgTmp_h5cf3681f__0 = ((~ (IData)(vlSelf->OraRouterCore__DOT__active)) 
                                                  & (IData)(vlSelf->io_inp_valid));
    vlSelf->OraRouterCore__DOT___zz_outVc_2 = ((0xfffffffU 
                                                & vlSelf->OraRouterCore__DOT___zz_outVc_2) 
                                               | ((0xc0000000U 
                                                   & vlSelf->io_inp_payload) 
                                                  | (((0U 
                                                       == 
                                                       (7U 
                                                        & (vlSelf->io_inp_payload 
                                                           >> 0x15U)))
                                                       ? 1U
                                                       : 
                                                      (3U 
                                                       & (vlSelf->io_inp_payload 
                                                          >> 0x1cU))) 
                                                     << 0x1cU)));
    vlSelf->OraRouterCore__DOT___zz_outVc_2 = ((0xf01fffffU 
                                                & vlSelf->OraRouterCore__DOT___zz_outVc_2) 
                                               | ((0xe000000U 
                                                   & (((vlSelf->io_inp_payload 
                                                        >> 0x19U) 
                                                       - (IData)(1U)) 
                                                      << 0x19U)) 
                                                  | ((0x1000000U 
                                                      & vlSelf->io_inp_payload) 
                                                     | ((IData)(OraRouterCore__DOT____VdfgExtracted_h2347b4b0__0) 
                                                        << 0x15U))));
    vlSelf->OraRouterCore__DOT___zz_outVc_2 = ((0xffe00000U 
                                                & vlSelf->OraRouterCore__DOT___zz_outVc_2) 
                                               | (0x3ffffU 
                                                  & (vlSelf->io_inp_payload 
                                                     >> 3U)));
    vlSelf->OraRouterCore__DOT___zz_io_out_payload_3 
        = ((0xfffffffU & vlSelf->OraRouterCore__DOT___zz_io_out_payload_3) 
           | ((0xc0000000U & vlSelf->io_inp_payload) 
              | (((0U == (7U & (vlSelf->io_inp_payload 
                                >> 0x15U))) ? 1U : 
                  (3U & (vlSelf->io_inp_payload >> 0x1cU))) 
                 << 0x1cU)));
    vlSelf->OraRouterCore__DOT___zz_io_out_payload_3 
        = ((0xf01fffffU & vlSelf->OraRouterCore__DOT___zz_io_out_payload_3) 
           | ((0xe000000U & (((vlSelf->io_inp_payload 
                               >> 0x19U) - (IData)(1U)) 
                             << 0x19U)) | ((0x1000000U 
                                            & vlSelf->io_inp_payload) 
                                           | ((IData)(OraRouterCore__DOT____VdfgExtracted_h2347b4b0__0) 
                                              << 0x15U))));
    vlSelf->OraRouterCore__DOT___zz_io_out_payload_3 
        = ((0xffe00000U & vlSelf->OraRouterCore__DOT___zz_io_out_payload_3) 
           | (0x3ffffU & (vlSelf->io_inp_payload >> 3U)));
    vlSelf->OraRouterCore__DOT__doChain = ((IData)(vlSelf->OraRouterCore__DOT____VdfgTmp_he29cc4cd__0) 
                                           & (vlSelf->io_inp_payload 
                                              >> 0x18U));
    vlSelf->io_eject_valid = ((IData)(OraRouterCore__DOT____VdfgTmp_h5cf3681f__0) 
                              & ((3U != (vlSelf->io_inp_payload 
                                         >> 0x1eU)) 
                                 & (((~ (vlSelf->io_inp_payload 
                                         >> 0x18U)) 
                                     & (IData)(vlSelf->OraRouterCore__DOT____VdfgTmp_he29cc4cd__0)) 
                                    | (IData)((0xc0000000U 
                                               == (0xcc000000U 
                                                   & vlSelf->io_inp_payload))))));
    vlSelf->OraRouterCore__DOT__hdrFwd = ((IData)(OraRouterCore__DOT____VdfgTmp_h5cf3681f__0) 
                                          & ((0U != 
                                              (7U & 
                                               (vlSelf->io_inp_payload 
                                                >> 0x19U))) 
                                             & (0U 
                                                == 
                                                (vlSelf->io_inp_payload 
                                                 >> 0x1eU))));
    OraRouterCore__DOT__aerFwd = ((IData)(OraRouterCore__DOT____VdfgTmp_h5cf3681f__0) 
                                  & ((0U != (3U & (vlSelf->io_inp_payload 
                                                   >> 0x1aU))) 
                                     & (3U == (vlSelf->io_inp_payload 
                                               >> 0x1eU))));
    OraRouterCore__DOT____VdfgExtracted_hca4f6894__0 
        = ((IData)(vlSelf->OraRouterCore__DOT__hdrFwd) 
           | ((IData)(vlSelf->OraRouterCore__DOT__active) 
              & ((~ (IData)(vlSelf->OraRouterCore__DOT__doChain)) 
                 & (IData)(vlSelf->io_inp_valid))));
    vlSelf->io_out_payload = ((IData)(vlSelf->OraRouterCore__DOT__active)
                               ? OraRouterCore__DOT___zz_io_out_payload
                               : vlSelf->OraRouterCore__DOT___zz_io_out_payload_3);
    vlSelf->io_out_valid = OraRouterCore__DOT____VdfgExtracted_hca4f6894__0;
    if (OraRouterCore__DOT__aerFwd) {
        vlSelf->io_out_payload = vlSelf->OraRouterCore__DOT___zz_io_out_payload_4;
        vlSelf->io_out_valid = 1U;
    }
    vlSelf->io_inp_ready = ((IData)(vlSelf->OraRouterCore__DOT__doChain) 
                            | ((((IData)(OraRouterCore__DOT____VdfgExtracted_hca4f6894__0) 
                                 | (IData)(OraRouterCore__DOT__aerFwd)) 
                                & (IData)(vlSelf->io_out_ready)) 
                               | ((IData)(vlSelf->io_eject_valid) 
                                  & (IData)(vlSelf->io_eject_ready))));
    vlSelf->OraRouterCore__DOT__io_inp_fire = ((IData)(vlSelf->io_inp_valid) 
                                               & (IData)(vlSelf->io_inp_ready));
}

void VOraRouterCore___024root___eval_ico(VOraRouterCore___024root* vlSelf) {
    if (false && vlSelf) {}  // Prevent unused
    VOraRouterCore__Syms* const __restrict vlSymsp VL_ATTR_UNUSED = vlSelf->vlSymsp;
    VL_DEBUG_IF(VL_DBG_MSGF("+    VOraRouterCore___024root___eval_ico\n"); );
    // Body
    if ((1ULL & vlSelf->__VicoTriggered.word(0U))) {
        VOraRouterCore___024root___ico_sequent__TOP__0(vlSelf);
    }
}

void VOraRouterCore___024root___eval_triggers__ico(VOraRouterCore___024root* vlSelf);

bool VOraRouterCore___024root___eval_phase__ico(VOraRouterCore___024root* vlSelf) {
    if (false && vlSelf) {}  // Prevent unused
    VOraRouterCore__Syms* const __restrict vlSymsp VL_ATTR_UNUSED = vlSelf->vlSymsp;
    VL_DEBUG_IF(VL_DBG_MSGF("+    VOraRouterCore___024root___eval_phase__ico\n"); );
    // Init
    CData/*0:0*/ __VicoExecute;
    // Body
    VOraRouterCore___024root___eval_triggers__ico(vlSelf);
    __VicoExecute = vlSelf->__VicoTriggered.any();
    if (__VicoExecute) {
        VOraRouterCore___024root___eval_ico(vlSelf);
    }
    return (__VicoExecute);
}

void VOraRouterCore___024root___eval_act(VOraRouterCore___024root* vlSelf) {
    if (false && vlSelf) {}  // Prevent unused
    VOraRouterCore__Syms* const __restrict vlSymsp VL_ATTR_UNUSED = vlSelf->vlSymsp;
    VL_DEBUG_IF(VL_DBG_MSGF("+    VOraRouterCore___024root___eval_act\n"); );
}

VL_INLINE_OPT void VOraRouterCore___024root___nba_sequent__TOP__0(VOraRouterCore___024root* vlSelf) {
    if (false && vlSelf) {}  // Prevent unused
    VOraRouterCore__Syms* const __restrict vlSymsp VL_ATTR_UNUSED = vlSelf->vlSymsp;
    VL_DEBUG_IF(VL_DBG_MSGF("+    VOraRouterCore___024root___nba_sequent__TOP__0\n"); );
    // Init
    CData/*0:0*/ OraRouterCore__DOT__aerFwd;
    OraRouterCore__DOT__aerFwd = 0;
    IData/*31:0*/ OraRouterCore__DOT___zz_io_out_payload;
    OraRouterCore__DOT___zz_io_out_payload = 0;
    CData/*0:0*/ OraRouterCore__DOT____VdfgExtracted_hca4f6894__0;
    OraRouterCore__DOT____VdfgExtracted_hca4f6894__0 = 0;
    CData/*0:0*/ OraRouterCore__DOT____VdfgTmp_h5cf3681f__0;
    OraRouterCore__DOT____VdfgTmp_h5cf3681f__0 = 0;
    // Body
    if (vlSelf->reset) {
        vlSelf->OraRouterCore__DOT__outVc = 0U;
        vlSelf->OraRouterCore__DOT__active = 0U;
    } else if (vlSelf->OraRouterCore__DOT__io_inp_fire) {
        if ((1U & (~ (IData)(vlSelf->OraRouterCore__DOT__active)))) {
            if (vlSelf->OraRouterCore__DOT__hdrFwd) {
                vlSelf->OraRouterCore__DOT__outVc = 
                    (3U & (vlSelf->OraRouterCore__DOT___zz_outVc_2 
                           >> 0x1cU));
            }
        }
        if (vlSelf->OraRouterCore__DOT__when_OraRouterCore_l114) {
            if (vlSelf->OraRouterCore__DOT__hdrFwd) {
                vlSelf->OraRouterCore__DOT__active = 1U;
            }
        } else if ((2U == (vlSelf->io_inp_payload >> 0x1eU))) {
            vlSelf->OraRouterCore__DOT__active = 0U;
        }
    }
    OraRouterCore__DOT___zz_io_out_payload = vlSelf->io_inp_payload;
    OraRouterCore__DOT___zz_io_out_payload = ((0xcfffffffU 
                                               & OraRouterCore__DOT___zz_io_out_payload) 
                                              | ((IData)(vlSelf->OraRouterCore__DOT__outVc) 
                                                 << 0x1cU));
    vlSelf->OraRouterCore__DOT__when_OraRouterCore_l114 
        = (1U & (~ (IData)(vlSelf->OraRouterCore__DOT__active)));
    OraRouterCore__DOT____VdfgTmp_h5cf3681f__0 = ((~ (IData)(vlSelf->OraRouterCore__DOT__active)) 
                                                  & (IData)(vlSelf->io_inp_valid));
    vlSelf->io_eject_valid = ((IData)(OraRouterCore__DOT____VdfgTmp_h5cf3681f__0) 
                              & ((3U != (vlSelf->io_inp_payload 
                                         >> 0x1eU)) 
                                 & (((~ (vlSelf->io_inp_payload 
                                         >> 0x18U)) 
                                     & (IData)(vlSelf->OraRouterCore__DOT____VdfgTmp_he29cc4cd__0)) 
                                    | (IData)((0xc0000000U 
                                               == (0xcc000000U 
                                                   & vlSelf->io_inp_payload))))));
    vlSelf->OraRouterCore__DOT__hdrFwd = ((IData)(OraRouterCore__DOT____VdfgTmp_h5cf3681f__0) 
                                          & ((0U != 
                                              (7U & 
                                               (vlSelf->io_inp_payload 
                                                >> 0x19U))) 
                                             & (0U 
                                                == 
                                                (vlSelf->io_inp_payload 
                                                 >> 0x1eU))));
    OraRouterCore__DOT__aerFwd = ((IData)(OraRouterCore__DOT____VdfgTmp_h5cf3681f__0) 
                                  & ((0U != (3U & (vlSelf->io_inp_payload 
                                                   >> 0x1aU))) 
                                     & (3U == (vlSelf->io_inp_payload 
                                               >> 0x1eU))));
    OraRouterCore__DOT____VdfgExtracted_hca4f6894__0 
        = ((IData)(vlSelf->OraRouterCore__DOT__hdrFwd) 
           | ((IData)(vlSelf->OraRouterCore__DOT__active) 
              & ((~ (IData)(vlSelf->OraRouterCore__DOT__doChain)) 
                 & (IData)(vlSelf->io_inp_valid))));
    vlSelf->io_out_payload = ((IData)(vlSelf->OraRouterCore__DOT__active)
                               ? OraRouterCore__DOT___zz_io_out_payload
                               : vlSelf->OraRouterCore__DOT___zz_io_out_payload_3);
    vlSelf->io_out_valid = OraRouterCore__DOT____VdfgExtracted_hca4f6894__0;
    if (OraRouterCore__DOT__aerFwd) {
        vlSelf->io_out_payload = vlSelf->OraRouterCore__DOT___zz_io_out_payload_4;
        vlSelf->io_out_valid = 1U;
    }
    vlSelf->io_inp_ready = ((IData)(vlSelf->OraRouterCore__DOT__doChain) 
                            | ((((IData)(OraRouterCore__DOT____VdfgExtracted_hca4f6894__0) 
                                 | (IData)(OraRouterCore__DOT__aerFwd)) 
                                & (IData)(vlSelf->io_out_ready)) 
                               | ((IData)(vlSelf->io_eject_valid) 
                                  & (IData)(vlSelf->io_eject_ready))));
    vlSelf->OraRouterCore__DOT__io_inp_fire = ((IData)(vlSelf->io_inp_valid) 
                                               & (IData)(vlSelf->io_inp_ready));
}

void VOraRouterCore___024root___eval_nba(VOraRouterCore___024root* vlSelf) {
    if (false && vlSelf) {}  // Prevent unused
    VOraRouterCore__Syms* const __restrict vlSymsp VL_ATTR_UNUSED = vlSelf->vlSymsp;
    VL_DEBUG_IF(VL_DBG_MSGF("+    VOraRouterCore___024root___eval_nba\n"); );
    // Body
    if ((1ULL & vlSelf->__VnbaTriggered.word(0U))) {
        VOraRouterCore___024root___nba_sequent__TOP__0(vlSelf);
    }
}

void VOraRouterCore___024root___eval_triggers__act(VOraRouterCore___024root* vlSelf);

bool VOraRouterCore___024root___eval_phase__act(VOraRouterCore___024root* vlSelf) {
    if (false && vlSelf) {}  // Prevent unused
    VOraRouterCore__Syms* const __restrict vlSymsp VL_ATTR_UNUSED = vlSelf->vlSymsp;
    VL_DEBUG_IF(VL_DBG_MSGF("+    VOraRouterCore___024root___eval_phase__act\n"); );
    // Init
    VlTriggerVec<1> __VpreTriggered;
    CData/*0:0*/ __VactExecute;
    // Body
    VOraRouterCore___024root___eval_triggers__act(vlSelf);
    __VactExecute = vlSelf->__VactTriggered.any();
    if (__VactExecute) {
        __VpreTriggered.andNot(vlSelf->__VactTriggered, vlSelf->__VnbaTriggered);
        vlSelf->__VnbaTriggered.thisOr(vlSelf->__VactTriggered);
        VOraRouterCore___024root___eval_act(vlSelf);
    }
    return (__VactExecute);
}

bool VOraRouterCore___024root___eval_phase__nba(VOraRouterCore___024root* vlSelf) {
    if (false && vlSelf) {}  // Prevent unused
    VOraRouterCore__Syms* const __restrict vlSymsp VL_ATTR_UNUSED = vlSelf->vlSymsp;
    VL_DEBUG_IF(VL_DBG_MSGF("+    VOraRouterCore___024root___eval_phase__nba\n"); );
    // Init
    CData/*0:0*/ __VnbaExecute;
    // Body
    __VnbaExecute = vlSelf->__VnbaTriggered.any();
    if (__VnbaExecute) {
        VOraRouterCore___024root___eval_nba(vlSelf);
        vlSelf->__VnbaTriggered.clear();
    }
    return (__VnbaExecute);
}

#ifdef VL_DEBUG
VL_ATTR_COLD void VOraRouterCore___024root___dump_triggers__ico(VOraRouterCore___024root* vlSelf);
#endif  // VL_DEBUG
#ifdef VL_DEBUG
VL_ATTR_COLD void VOraRouterCore___024root___dump_triggers__nba(VOraRouterCore___024root* vlSelf);
#endif  // VL_DEBUG
#ifdef VL_DEBUG
VL_ATTR_COLD void VOraRouterCore___024root___dump_triggers__act(VOraRouterCore___024root* vlSelf);
#endif  // VL_DEBUG

void VOraRouterCore___024root___eval(VOraRouterCore___024root* vlSelf) {
    if (false && vlSelf) {}  // Prevent unused
    VOraRouterCore__Syms* const __restrict vlSymsp VL_ATTR_UNUSED = vlSelf->vlSymsp;
    VL_DEBUG_IF(VL_DBG_MSGF("+    VOraRouterCore___024root___eval\n"); );
    // Init
    IData/*31:0*/ __VicoIterCount;
    CData/*0:0*/ __VicoContinue;
    IData/*31:0*/ __VnbaIterCount;
    CData/*0:0*/ __VnbaContinue;
    // Body
    __VicoIterCount = 0U;
    vlSelf->__VicoFirstIteration = 1U;
    __VicoContinue = 1U;
    while (__VicoContinue) {
        if (VL_UNLIKELY((0x64U < __VicoIterCount))) {
#ifdef VL_DEBUG
            VOraRouterCore___024root___dump_triggers__ico(vlSelf);
#endif
            VL_FATAL_MT("../generated/OraRouterCore.v", 6, "", "Input combinational region did not converge.");
        }
        __VicoIterCount = ((IData)(1U) + __VicoIterCount);
        __VicoContinue = 0U;
        if (VOraRouterCore___024root___eval_phase__ico(vlSelf)) {
            __VicoContinue = 1U;
        }
        vlSelf->__VicoFirstIteration = 0U;
    }
    __VnbaIterCount = 0U;
    __VnbaContinue = 1U;
    while (__VnbaContinue) {
        if (VL_UNLIKELY((0x64U < __VnbaIterCount))) {
#ifdef VL_DEBUG
            VOraRouterCore___024root___dump_triggers__nba(vlSelf);
#endif
            VL_FATAL_MT("../generated/OraRouterCore.v", 6, "", "NBA region did not converge.");
        }
        __VnbaIterCount = ((IData)(1U) + __VnbaIterCount);
        __VnbaContinue = 0U;
        vlSelf->__VactIterCount = 0U;
        vlSelf->__VactContinue = 1U;
        while (vlSelf->__VactContinue) {
            if (VL_UNLIKELY((0x64U < vlSelf->__VactIterCount))) {
#ifdef VL_DEBUG
                VOraRouterCore___024root___dump_triggers__act(vlSelf);
#endif
                VL_FATAL_MT("../generated/OraRouterCore.v", 6, "", "Active region did not converge.");
            }
            vlSelf->__VactIterCount = ((IData)(1U) 
                                       + vlSelf->__VactIterCount);
            vlSelf->__VactContinue = 0U;
            if (VOraRouterCore___024root___eval_phase__act(vlSelf)) {
                vlSelf->__VactContinue = 1U;
            }
        }
        if (VOraRouterCore___024root___eval_phase__nba(vlSelf)) {
            __VnbaContinue = 1U;
        }
    }
}

#ifdef VL_DEBUG
void VOraRouterCore___024root___eval_debug_assertions(VOraRouterCore___024root* vlSelf) {
    if (false && vlSelf) {}  // Prevent unused
    VOraRouterCore__Syms* const __restrict vlSymsp VL_ATTR_UNUSED = vlSelf->vlSymsp;
    VL_DEBUG_IF(VL_DBG_MSGF("+    VOraRouterCore___024root___eval_debug_assertions\n"); );
    // Body
    if (VL_UNLIKELY((vlSelf->io_inp_valid & 0xfeU))) {
        Verilated::overWidthError("io_inp_valid");}
    if (VL_UNLIKELY((vlSelf->io_out_ready & 0xfeU))) {
        Verilated::overWidthError("io_out_ready");}
    if (VL_UNLIKELY((vlSelf->io_eject_ready & 0xfeU))) {
        Verilated::overWidthError("io_eject_ready");}
    if (VL_UNLIKELY((vlSelf->clk & 0xfeU))) {
        Verilated::overWidthError("clk");}
    if (VL_UNLIKELY((vlSelf->reset & 0xfeU))) {
        Verilated::overWidthError("reset");}
}
#endif  // VL_DEBUG
