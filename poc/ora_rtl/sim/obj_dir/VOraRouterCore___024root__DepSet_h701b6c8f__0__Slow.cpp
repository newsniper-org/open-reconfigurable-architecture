// Verilated -*- C++ -*-
// DESCRIPTION: Verilator output: Design implementation internals
// See VOraRouterCore.h for the primary calling header

#include "VOraRouterCore__pch.h"
#include "VOraRouterCore___024root.h"

VL_ATTR_COLD void VOraRouterCore___024root___eval_static(VOraRouterCore___024root* vlSelf) {
    if (false && vlSelf) {}  // Prevent unused
    VOraRouterCore__Syms* const __restrict vlSymsp VL_ATTR_UNUSED = vlSelf->vlSymsp;
    VL_DEBUG_IF(VL_DBG_MSGF("+    VOraRouterCore___024root___eval_static\n"); );
}

VL_ATTR_COLD void VOraRouterCore___024root___eval_initial(VOraRouterCore___024root* vlSelf) {
    if (false && vlSelf) {}  // Prevent unused
    VOraRouterCore__Syms* const __restrict vlSymsp VL_ATTR_UNUSED = vlSelf->vlSymsp;
    VL_DEBUG_IF(VL_DBG_MSGF("+    VOraRouterCore___024root___eval_initial\n"); );
    // Body
    vlSelf->__Vtrigprevexpr___TOP__clk__0 = vlSelf->clk;
    vlSelf->__Vtrigprevexpr___TOP__reset__0 = vlSelf->reset;
}

VL_ATTR_COLD void VOraRouterCore___024root___eval_final(VOraRouterCore___024root* vlSelf) {
    if (false && vlSelf) {}  // Prevent unused
    VOraRouterCore__Syms* const __restrict vlSymsp VL_ATTR_UNUSED = vlSelf->vlSymsp;
    VL_DEBUG_IF(VL_DBG_MSGF("+    VOraRouterCore___024root___eval_final\n"); );
}

#ifdef VL_DEBUG
VL_ATTR_COLD void VOraRouterCore___024root___dump_triggers__stl(VOraRouterCore___024root* vlSelf);
#endif  // VL_DEBUG
VL_ATTR_COLD bool VOraRouterCore___024root___eval_phase__stl(VOraRouterCore___024root* vlSelf);

VL_ATTR_COLD void VOraRouterCore___024root___eval_settle(VOraRouterCore___024root* vlSelf) {
    if (false && vlSelf) {}  // Prevent unused
    VOraRouterCore__Syms* const __restrict vlSymsp VL_ATTR_UNUSED = vlSelf->vlSymsp;
    VL_DEBUG_IF(VL_DBG_MSGF("+    VOraRouterCore___024root___eval_settle\n"); );
    // Init
    IData/*31:0*/ __VstlIterCount;
    CData/*0:0*/ __VstlContinue;
    // Body
    __VstlIterCount = 0U;
    vlSelf->__VstlFirstIteration = 1U;
    __VstlContinue = 1U;
    while (__VstlContinue) {
        if (VL_UNLIKELY((0x64U < __VstlIterCount))) {
#ifdef VL_DEBUG
            VOraRouterCore___024root___dump_triggers__stl(vlSelf);
#endif
            VL_FATAL_MT("../generated/OraRouterCore.v", 6, "", "Settle region did not converge.");
        }
        __VstlIterCount = ((IData)(1U) + __VstlIterCount);
        __VstlContinue = 0U;
        if (VOraRouterCore___024root___eval_phase__stl(vlSelf)) {
            __VstlContinue = 1U;
        }
        vlSelf->__VstlFirstIteration = 0U;
    }
}

#ifdef VL_DEBUG
VL_ATTR_COLD void VOraRouterCore___024root___dump_triggers__stl(VOraRouterCore___024root* vlSelf) {
    if (false && vlSelf) {}  // Prevent unused
    VOraRouterCore__Syms* const __restrict vlSymsp VL_ATTR_UNUSED = vlSelf->vlSymsp;
    VL_DEBUG_IF(VL_DBG_MSGF("+    VOraRouterCore___024root___dump_triggers__stl\n"); );
    // Body
    if ((1U & (~ (IData)(vlSelf->__VstlTriggered.any())))) {
        VL_DBG_MSGF("         No triggers active\n");
    }
    if ((1ULL & vlSelf->__VstlTriggered.word(0U))) {
        VL_DBG_MSGF("         'stl' region trigger index 0 is active: Internal 'stl' trigger - first iteration\n");
    }
}
#endif  // VL_DEBUG

VL_ATTR_COLD void VOraRouterCore___024root___stl_sequent__TOP__0(VOraRouterCore___024root* vlSelf) {
    if (false && vlSelf) {}  // Prevent unused
    VOraRouterCore__Syms* const __restrict vlSymsp VL_ATTR_UNUSED = vlSelf->vlSymsp;
    VL_DEBUG_IF(VL_DBG_MSGF("+    VOraRouterCore___024root___stl_sequent__TOP__0\n"); );
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
    vlSelf->OraRouterCore__DOT__when_OraRouterCore_l114 
        = (1U & (~ (IData)(vlSelf->OraRouterCore__DOT__active)));
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

VL_ATTR_COLD void VOraRouterCore___024root___eval_stl(VOraRouterCore___024root* vlSelf) {
    if (false && vlSelf) {}  // Prevent unused
    VOraRouterCore__Syms* const __restrict vlSymsp VL_ATTR_UNUSED = vlSelf->vlSymsp;
    VL_DEBUG_IF(VL_DBG_MSGF("+    VOraRouterCore___024root___eval_stl\n"); );
    // Body
    if ((1ULL & vlSelf->__VstlTriggered.word(0U))) {
        VOraRouterCore___024root___stl_sequent__TOP__0(vlSelf);
    }
}

VL_ATTR_COLD void VOraRouterCore___024root___eval_triggers__stl(VOraRouterCore___024root* vlSelf);

VL_ATTR_COLD bool VOraRouterCore___024root___eval_phase__stl(VOraRouterCore___024root* vlSelf) {
    if (false && vlSelf) {}  // Prevent unused
    VOraRouterCore__Syms* const __restrict vlSymsp VL_ATTR_UNUSED = vlSelf->vlSymsp;
    VL_DEBUG_IF(VL_DBG_MSGF("+    VOraRouterCore___024root___eval_phase__stl\n"); );
    // Init
    CData/*0:0*/ __VstlExecute;
    // Body
    VOraRouterCore___024root___eval_triggers__stl(vlSelf);
    __VstlExecute = vlSelf->__VstlTriggered.any();
    if (__VstlExecute) {
        VOraRouterCore___024root___eval_stl(vlSelf);
    }
    return (__VstlExecute);
}

#ifdef VL_DEBUG
VL_ATTR_COLD void VOraRouterCore___024root___dump_triggers__ico(VOraRouterCore___024root* vlSelf) {
    if (false && vlSelf) {}  // Prevent unused
    VOraRouterCore__Syms* const __restrict vlSymsp VL_ATTR_UNUSED = vlSelf->vlSymsp;
    VL_DEBUG_IF(VL_DBG_MSGF("+    VOraRouterCore___024root___dump_triggers__ico\n"); );
    // Body
    if ((1U & (~ (IData)(vlSelf->__VicoTriggered.any())))) {
        VL_DBG_MSGF("         No triggers active\n");
    }
    if ((1ULL & vlSelf->__VicoTriggered.word(0U))) {
        VL_DBG_MSGF("         'ico' region trigger index 0 is active: Internal 'ico' trigger - first iteration\n");
    }
}
#endif  // VL_DEBUG

#ifdef VL_DEBUG
VL_ATTR_COLD void VOraRouterCore___024root___dump_triggers__act(VOraRouterCore___024root* vlSelf) {
    if (false && vlSelf) {}  // Prevent unused
    VOraRouterCore__Syms* const __restrict vlSymsp VL_ATTR_UNUSED = vlSelf->vlSymsp;
    VL_DEBUG_IF(VL_DBG_MSGF("+    VOraRouterCore___024root___dump_triggers__act\n"); );
    // Body
    if ((1U & (~ (IData)(vlSelf->__VactTriggered.any())))) {
        VL_DBG_MSGF("         No triggers active\n");
    }
    if ((1ULL & vlSelf->__VactTriggered.word(0U))) {
        VL_DBG_MSGF("         'act' region trigger index 0 is active: @(posedge clk or posedge reset)\n");
    }
}
#endif  // VL_DEBUG

#ifdef VL_DEBUG
VL_ATTR_COLD void VOraRouterCore___024root___dump_triggers__nba(VOraRouterCore___024root* vlSelf) {
    if (false && vlSelf) {}  // Prevent unused
    VOraRouterCore__Syms* const __restrict vlSymsp VL_ATTR_UNUSED = vlSelf->vlSymsp;
    VL_DEBUG_IF(VL_DBG_MSGF("+    VOraRouterCore___024root___dump_triggers__nba\n"); );
    // Body
    if ((1U & (~ (IData)(vlSelf->__VnbaTriggered.any())))) {
        VL_DBG_MSGF("         No triggers active\n");
    }
    if ((1ULL & vlSelf->__VnbaTriggered.word(0U))) {
        VL_DBG_MSGF("         'nba' region trigger index 0 is active: @(posedge clk or posedge reset)\n");
    }
}
#endif  // VL_DEBUG

VL_ATTR_COLD void VOraRouterCore___024root___ctor_var_reset(VOraRouterCore___024root* vlSelf) {
    if (false && vlSelf) {}  // Prevent unused
    VOraRouterCore__Syms* const __restrict vlSymsp VL_ATTR_UNUSED = vlSelf->vlSymsp;
    VL_DEBUG_IF(VL_DBG_MSGF("+    VOraRouterCore___024root___ctor_var_reset\n"); );
    // Body
    vlSelf->io_inp_valid = VL_RAND_RESET_I(1);
    vlSelf->io_inp_ready = VL_RAND_RESET_I(1);
    vlSelf->io_inp_payload = VL_RAND_RESET_I(32);
    vlSelf->io_out_valid = VL_RAND_RESET_I(1);
    vlSelf->io_out_ready = VL_RAND_RESET_I(1);
    vlSelf->io_out_payload = VL_RAND_RESET_I(32);
    vlSelf->io_eject_valid = VL_RAND_RESET_I(1);
    vlSelf->io_eject_ready = VL_RAND_RESET_I(1);
    vlSelf->io_eject_payload = VL_RAND_RESET_I(32);
    vlSelf->clk = VL_RAND_RESET_I(1);
    vlSelf->reset = VL_RAND_RESET_I(1);
    vlSelf->OraRouterCore__DOT__active = VL_RAND_RESET_I(1);
    vlSelf->OraRouterCore__DOT__outVc = VL_RAND_RESET_I(2);
    vlSelf->OraRouterCore__DOT__doChain = VL_RAND_RESET_I(1);
    vlSelf->OraRouterCore__DOT__hdrFwd = VL_RAND_RESET_I(1);
    vlSelf->OraRouterCore__DOT___zz_io_out_payload_3 = VL_RAND_RESET_I(32);
    vlSelf->OraRouterCore__DOT___zz_io_out_payload_4 = VL_RAND_RESET_I(32);
    vlSelf->OraRouterCore__DOT__io_inp_fire = VL_RAND_RESET_I(1);
    vlSelf->OraRouterCore__DOT__when_OraRouterCore_l114 = VL_RAND_RESET_I(1);
    vlSelf->OraRouterCore__DOT___zz_outVc_2 = VL_RAND_RESET_I(32);
    vlSelf->OraRouterCore__DOT____VdfgTmp_he29cc4cd__0 = 0;
    vlSelf->__Vtrigprevexpr___TOP__clk__0 = VL_RAND_RESET_I(1);
    vlSelf->__Vtrigprevexpr___TOP__reset__0 = VL_RAND_RESET_I(1);
}
