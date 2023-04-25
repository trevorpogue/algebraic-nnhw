dsp (.ay(ayz_), .by(byz_),
     .ax(ax_), .bx(bx_),
     .resulta(res), .chainout(dsp_chainout[I][J]),
     .clk0(clk), .clk1(clk), .clk2(clk),
     .aclr0(~resetn), .aclr1(~resetn), .ena('1));
