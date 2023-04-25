pll_u (
       .rst      (~pb[1]),
       .refclk   (clk125),
       .locked   (),
       .outclk_0 (clk),
       .outclk_1 (_instruc_clk),
       .outclk_2 (layeriomem_clk),
       .outclk_3 (weightmem_clk),
       .outclk_4 (_quantization_clk),
       .outclk_5 (_pooling_clk),
       .outclk_6 (_padding_clk)
       );
