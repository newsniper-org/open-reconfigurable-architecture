// Verilated -*- C++ -*-
// DESCRIPTION: Verilator output: Model implementation (design independent parts)

#include "VOraRouterCore__pch.h"

//============================================================
// Constructors

VOraRouterCore::VOraRouterCore(VerilatedContext* _vcontextp__, const char* _vcname__)
    : VerilatedModel{*_vcontextp__}
    , vlSymsp{new VOraRouterCore__Syms(contextp(), _vcname__, this)}
    , clk{vlSymsp->TOP.clk}
    , reset{vlSymsp->TOP.reset}
    , io_inp_valid{vlSymsp->TOP.io_inp_valid}
    , io_inp_ready{vlSymsp->TOP.io_inp_ready}
    , io_out_valid{vlSymsp->TOP.io_out_valid}
    , io_out_ready{vlSymsp->TOP.io_out_ready}
    , io_eject_valid{vlSymsp->TOP.io_eject_valid}
    , io_eject_ready{vlSymsp->TOP.io_eject_ready}
    , io_inp_payload{vlSymsp->TOP.io_inp_payload}
    , io_out_payload{vlSymsp->TOP.io_out_payload}
    , io_eject_payload{vlSymsp->TOP.io_eject_payload}
    , rootp{&(vlSymsp->TOP)}
{
    // Register model with the context
    contextp()->addModel(this);
}

VOraRouterCore::VOraRouterCore(const char* _vcname__)
    : VOraRouterCore(Verilated::threadContextp(), _vcname__)
{
}

//============================================================
// Destructor

VOraRouterCore::~VOraRouterCore() {
    delete vlSymsp;
}

//============================================================
// Evaluation function

#ifdef VL_DEBUG
void VOraRouterCore___024root___eval_debug_assertions(VOraRouterCore___024root* vlSelf);
#endif  // VL_DEBUG
void VOraRouterCore___024root___eval_static(VOraRouterCore___024root* vlSelf);
void VOraRouterCore___024root___eval_initial(VOraRouterCore___024root* vlSelf);
void VOraRouterCore___024root___eval_settle(VOraRouterCore___024root* vlSelf);
void VOraRouterCore___024root___eval(VOraRouterCore___024root* vlSelf);

void VOraRouterCore::eval_step() {
    VL_DEBUG_IF(VL_DBG_MSGF("+++++TOP Evaluate VOraRouterCore::eval_step\n"); );
#ifdef VL_DEBUG
    // Debug assertions
    VOraRouterCore___024root___eval_debug_assertions(&(vlSymsp->TOP));
#endif  // VL_DEBUG
    vlSymsp->__Vm_deleter.deleteAll();
    if (VL_UNLIKELY(!vlSymsp->__Vm_didInit)) {
        vlSymsp->__Vm_didInit = true;
        VL_DEBUG_IF(VL_DBG_MSGF("+ Initial\n"););
        VOraRouterCore___024root___eval_static(&(vlSymsp->TOP));
        VOraRouterCore___024root___eval_initial(&(vlSymsp->TOP));
        VOraRouterCore___024root___eval_settle(&(vlSymsp->TOP));
    }
    VL_DEBUG_IF(VL_DBG_MSGF("+ Eval\n"););
    VOraRouterCore___024root___eval(&(vlSymsp->TOP));
    // Evaluate cleanup
    Verilated::endOfEval(vlSymsp->__Vm_evalMsgQp);
}

//============================================================
// Events and timing
bool VOraRouterCore::eventsPending() { return false; }

uint64_t VOraRouterCore::nextTimeSlot() {
    VL_FATAL_MT(__FILE__, __LINE__, "", "%Error: No delays in the design");
    return 0;
}

//============================================================
// Utilities

const char* VOraRouterCore::name() const {
    return vlSymsp->name();
}

//============================================================
// Invoke final blocks

void VOraRouterCore___024root___eval_final(VOraRouterCore___024root* vlSelf);

VL_ATTR_COLD void VOraRouterCore::final() {
    VOraRouterCore___024root___eval_final(&(vlSymsp->TOP));
}

//============================================================
// Implementations of abstract methods from VerilatedModel

const char* VOraRouterCore::hierName() const { return vlSymsp->name(); }
const char* VOraRouterCore::modelName() const { return "VOraRouterCore"; }
unsigned VOraRouterCore::threads() const { return 1; }
void VOraRouterCore::prepareClone() const { contextp()->prepareClone(); }
void VOraRouterCore::atClone() const {
    contextp()->threadPoolpOnClone();
}

//============================================================
// Trace configuration

VL_ATTR_COLD void VOraRouterCore::trace(VerilatedVcdC* tfp, int levels, int options) {
    vl_fatal(__FILE__, __LINE__, __FILE__,"'VOraRouterCore::trace()' called on model that was Verilated without --trace option");
}
