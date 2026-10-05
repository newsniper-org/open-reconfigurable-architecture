// Generator : SpinalHDL v1.10.2a    git head : a348a60b7e8b6a455c72e1536ec3d74a2ea16935
// Component : OraRouterCore

`timescale 1ns/1ps

module OraRouterCore (
  input  wire          io_inp_valid,
  output wire          io_inp_ready,
  input  wire [31:0]   io_inp_payload,
  output reg           io_out_valid,
  input  wire          io_out_ready,
  output reg  [31:0]   io_out_payload,
  output wire          io_eject_valid,
  input  wire          io_eject_ready,
  output wire [31:0]   io_eject_payload,
  input  wire          clk,
  input  wire          reset
);

  wire       [2:0]    _zz__zz_io_out_payload_3;
  wire       [2:0]    _zz__zz_io_out_payload_3_1;
  wire       [17:0]   _zz__zz_io_out_payload_3_2;
  wire       [17:0]   _zz__zz_io_out_payload_3_3;
  wire       [1:0]    _zz__zz_io_out_payload_4;
  wire       [2:0]    _zz__zz_io_out_payload_4_1;
  wire       [2:0]    _zz__zz_io_out_payload_4_2;
  wire       [2:0]    _zz__zz_outVc_2;
  wire       [2:0]    _zz__zz_outVc_2_1;
  wire       [17:0]   _zz__zz_outVc_2_2;
  wire       [17:0]   _zz__zz_outVc_2_3;
  reg                 active;
  reg        [1:0]    outVc;
  wire                isHdr;
  wire                isAer;
  wire                isTail;
  wire                hopZero;
  wire                aerHopZero;
  wire                doChain;
  wire                doEject;
  wire                streamFwd;
  wire                hdrFwd;
  wire                aerFwd;
  reg        [31:0]   _zz_io_out_payload;
  wire       [2:0]    _zz_io_out_payload_1;
  wire                _zz_io_out_payload_2;
  reg        [31:0]   _zz_io_out_payload_3;
  reg        [31:0]   _zz_io_out_payload_4;
  wire                ejectAct;
  wire                fwdAct;
  wire                io_inp_fire;
  wire                when_OraRouterCore_l114;
  wire       [2:0]    _zz_outVc;
  wire                _zz_outVc_1;
  reg        [31:0]   _zz_outVc_2;

  assign _zz__zz_io_out_payload_3 = (io_inp_payload[27 : 25] - 3'b001);
  assign _zz__zz_io_out_payload_3_1 = (_zz_io_out_payload_1 - 3'b001);
  assign _zz__zz_io_out_payload_3_2 = _zz__zz_io_out_payload_3_3;
  assign _zz__zz_io_out_payload_3_3 = (io_inp_payload[20 : 0] >>> 2'd3);
  assign _zz__zz_io_out_payload_4 = (io_inp_payload[27 : 26] - 2'b01);
  assign _zz__zz_io_out_payload_4_1 = _zz__zz_io_out_payload_4_2;
  assign _zz__zz_io_out_payload_4_2 = (io_inp_payload[25 : 20] >>> 2'd3);
  assign _zz__zz_outVc_2 = (io_inp_payload[27 : 25] - 3'b001);
  assign _zz__zz_outVc_2_1 = (_zz_outVc - 3'b001);
  assign _zz__zz_outVc_2_2 = _zz__zz_outVc_2_3;
  assign _zz__zz_outVc_2_3 = (io_inp_payload[20 : 0] >>> 2'd3);
  assign isHdr = (io_inp_payload[31 : 30] == 2'b00);
  assign isAer = (io_inp_payload[31 : 30] == 2'b11);
  assign isTail = (io_inp_payload[31 : 30] == 2'b10);
  assign hopZero = (io_inp_payload[27 : 25] == 3'b000);
  assign aerHopZero = (io_inp_payload[27 : 26] == 2'b00);
  assign doChain = ((isHdr && hopZero) && io_inp_payload[24]);
  assign doEject = (((isHdr && hopZero) && (! io_inp_payload[24])) || (isAer && aerHopZero));
  assign streamFwd = ((active && io_inp_valid) && (! doChain));
  assign hdrFwd = ((((! active) && io_inp_valid) && isHdr) && (! hopZero));
  assign aerFwd = ((((! active) && io_inp_valid) && isAer) && (! aerHopZero));
  always @(*) begin
    io_out_valid = (hdrFwd || streamFwd);
    if(aerFwd) begin
      io_out_valid = 1'b1;
    end
  end

  always @(*) begin
    _zz_io_out_payload = io_inp_payload;
    _zz_io_out_payload[29 : 28] = outVc;
  end

  assign _zz_io_out_payload_1 = io_inp_payload[23 : 21];
  assign _zz_io_out_payload_2 = (_zz_io_out_payload_1 == 3'b000);
  always @(*) begin
    _zz_io_out_payload_3[31 : 30] = io_inp_payload[31 : 30];
    _zz_io_out_payload_3[29 : 28] = (_zz_io_out_payload_2 ? 2'b01 : io_inp_payload[29 : 28]);
    _zz_io_out_payload_3[27 : 25] = _zz__zz_io_out_payload_3;
    _zz_io_out_payload_3[24] = io_inp_payload[24];
    _zz_io_out_payload_3[23 : 21] = (_zz_io_out_payload_2 ? 3'b111 : ((_zz_io_out_payload_1 == 3'b111) ? _zz_io_out_payload_1 : _zz__zz_io_out_payload_3_1));
    _zz_io_out_payload_3[20 : 0] = {3'd0, _zz__zz_io_out_payload_3_2};
  end

  always @(*) begin
    io_out_payload = (active ? _zz_io_out_payload : _zz_io_out_payload_3);
    if(aerFwd) begin
      io_out_payload = _zz_io_out_payload_4;
    end
  end

  always @(*) begin
    _zz_io_out_payload_4 = io_inp_payload;
    _zz_io_out_payload_4[27 : 26] = _zz__zz_io_out_payload_4;
    _zz_io_out_payload_4[25 : 20] = {3'd0, _zz__zz_io_out_payload_4_1};
  end

  assign ejectAct = ((((! active) && io_inp_valid) && doEject) && (! isAer));
  assign io_eject_valid = ejectAct;
  assign io_eject_payload = io_inp_payload;
  assign fwdAct = ((hdrFwd || streamFwd) || aerFwd);
  assign io_inp_ready = ((doChain || (fwdAct && io_out_ready)) || (ejectAct && io_eject_ready));
  assign io_inp_fire = (io_inp_valid && io_inp_ready);
  assign when_OraRouterCore_l114 = (! active);
  assign _zz_outVc = io_inp_payload[23 : 21];
  assign _zz_outVc_1 = (_zz_outVc == 3'b000);
  always @(*) begin
    _zz_outVc_2[31 : 30] = io_inp_payload[31 : 30];
    _zz_outVc_2[29 : 28] = (_zz_outVc_1 ? 2'b01 : io_inp_payload[29 : 28]);
    _zz_outVc_2[27 : 25] = _zz__zz_outVc_2;
    _zz_outVc_2[24] = io_inp_payload[24];
    _zz_outVc_2[23 : 21] = (_zz_outVc_1 ? 3'b111 : ((_zz_outVc == 3'b111) ? _zz_outVc : _zz__zz_outVc_2_1));
    _zz_outVc_2[20 : 0] = {3'd0, _zz__zz_outVc_2_2};
  end

  always @(posedge clk or posedge reset) begin
    if(reset) begin
      active <= 1'b0;
      outVc <= 2'b00;
    end else begin
      if(io_inp_fire) begin
        if(when_OraRouterCore_l114) begin
          if(hdrFwd) begin
            active <= 1'b1;
            outVc <= _zz_outVc_2[29 : 28];
          end
        end else begin
          if(isTail) begin
            active <= 1'b0;
          end
        end
      end
    end
  end


endmodule
