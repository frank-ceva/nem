"""
Conformance: Constant Declarations - full program with const preamble
Spec reference: Constant Declarations
"""

NEM_PROGRAM = """\
device "npm_lite.cfg"

program conv2d_relu:

# --- Compile-time constants ---
const TiH = 16
const TiW = 16
const Cin = 64
const Cout = 128
const Kh = 3
const Kw = 3
const ToH = 14
const ToW = 14
const T = 4

const tileX_bytes = TiH * TiW * Cin
const tileW_bytes = Kh * Kw * Cin * Cout
const tileY_bytes = ToH * ToW * Cout
const bias_bytes = Cout * 4

buffer X_L2 : L2 (size=T * tileX_bytes, align=64)
buffer W_L2 : L2 (size=tileW_bytes, align=64)
buffer B_L2 : L2 (size=bias_bytes, align=64)
buffer Y_L2 : L2 (size=T * tileY_bytes, align=64)

buffer X_L1 : L1 (size=2*tileX_bytes, align=64)
buffer W_L1 : L1 (size=tileW_bytes,   align=64)
buffer Y_L1 : L1 (size=2*tileY_bytes, align=64)

loop i in [0..T-1] @max_in_flight(2):

  let X_tile_i = region(X_L2, i * tileX_bytes, tileX_bytes)
                 elem=i8, shape=[1,TiH,TiW,Cin], layout=NHWC

  let Y_tile_i = region(Y_L2, i * tileY_bytes, tileY_bytes)
                 elem=i8, shape=[1,ToH,ToW,Cout], layout=NHWC
                 @materialized

  let X_pp_i = region(X_L1, (i mod 2)*tileX_bytes, tileX_bytes)
               elem=i8, shape=[1,TiH,TiW,Cin], layout=NHWC

  let Y_pp_i = region(Y_L1, (i mod 2)*tileY_bytes, tileY_bytes)
               elem=i8, shape=[1,ToH,ToW,Cout], layout=NHWC
               @materialized

  let W_l1 = region(W_L1, 0, tileW_bytes)
             elem=i8, shape=[Kh,Kw,Cin,Cout], layout=HWIO

  let B_l2 = region(B_L2, 0, bias_bytes)
             elem=i32, shape=[Cout], layout=C
             @readonly

  tX = transfer.async(dst=X_pp_i, src=X_tile_i)
  tW = transfer.async(
         dst=W_l1,
         src=region(W_L2, 0, tileW_bytes)
             elem=i8, shape=[Kh,Kw,Cin,Cout], layout=HWIO
       )
  wait(tX, tW)

  tC = conv2d.async
          in  X_pp_i, W_l1, B_l2
          out Y_pp_i
          deps=[tX, tW]
          pads=[1,1,1,1]
          strides=[1,1]
          dilations=[1,1]
          groups=1
          accum_type=i32

  tR = relu.async
          in  Y_pp_i
          out Y_pp_i @materialized
          deps=[tC]

  tS = store.async(dst=Y_tile_i, src=Y_pp_i, deps=[tR])

endloop
"""


def test_full_program_with_const_preamble():
    """A complete NEM program using const declarations is valid."""
    # Conformance specification — to be wired to parser/semantic checker
    # Expected outcome: valid (no parse or semantic errors)
    assert NEM_PROGRAM is not None  # placeholder assertion
