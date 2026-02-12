# Examples

These examples accompany the [NEM Specification](nem_spec.md) and illustrate the 3 levels of abstractions embodied by ONNX, MLIR NEM and TCB levels .

---

## ONNX Representation

```python
Y0 = Conv(
    X,
    W,
    B,
    strides=(1,1),
    pads=(1,1,1,1),
    dilations=(1,1),
    group=1
)
Y = Relu(Y0)
```

At the ONNX level:
- Execution order, tiling, memory placement, and data movement are implicit.
- Intermediate values are conceptually materialized.
- There is no notion of explicit memory hierarchy or execution overlap

## MLIR Representation (Illustrative)

```
affine.for %t = 0 to %T {
  %x_tile = memref.subview %X[...] : memref<...> to memref<...>
  %y_tile = memref.subview %Y[...] : memref<...> to memref<...>

  %tx = async.execute {
    dma.copy %x_tile -> %x_l1_pingpong[%t mod 2]
  }

  %tw = async.execute {
    dma.copy %W -> %w_l1
  }

  %tc = async.execute [%tx, %tw] {
    %y0 = neupro.conv2d %x_l1, %w_l1, %B {
      pads = ...,
      strides = ...,
      dilations = ...,
      accum = i32
    }
    %y = neupro.relu %y0
    async.yield %y
  }

  %ts = async.execute [%tc] {
    dma.copy %y -> %y_tile
  }
}
```
At the MLIR level:

Tiling is explicit.
- Asynchronous execution and dependencies are explicit.
- Data movement and compute are separated.
- Memory hierarchy is visible but not hardware-bound.

## NEM Implementation

### Device Configuration File (`npm_lite.cfg`)

```text
include "nem_baseline_1.0.nem"

device npm_lite extends nem_baseline_1_0 {
    topology {
        num_engines = 1
        per_engine {
            NMU  = 1
            CSTL = 2
            DMA  = 2
        }
    }

    opcode.mandatory {
        conv2d.int8<i16>.with_bias      # 16-bit output accumulation for Conv2D
        eltwise<i32>.default            # 32-bit elementwise (e.g. bias add before requant)
        dequantize<i8, f32>.default     # dequantize to FP32 for mixed-precision paths
    }
}
```

### NEM Representation
```
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

const tileX_bytes = TiH * TiW * Cin        # 16384
const tileW_bytes = Kh * Kw * Cin * Cout    # 294912
const tileY_bytes = ToH * ToW * Cout        # 25088
const bias_bytes = Cout * 4                 # i32 = 4 bytes per element

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
```

At the NEM level:
- Memory hierarchy is explicit (L2/L1).
- Data movement, compute, and synchronization are explicit.
- Regions are typed, scoped, and reusable.
- Fusion is controlled via @materialized.
- Bounded pipelining is expressed via @max_in_flight.

### Multi-CSTL Pipeline with @resource

This example demonstrates how `@resource` enables expressing intra-engine parallelism
across 4 CSTL instances in a tiled GEMM + post-op pipeline.

Target device: `capabilities.per_engine.units[CSTL] = 4`

#### Device Configuration File (`npm_quad_cstl.cfg`)

```text
include "nem_baseline_1.0.nem"

device npm_quad_cstl extends nem_baseline_1_0 {
    topology {
        num_engines = 1
        per_engine {
            NMU  = 1
            CSTL = 4
            DMA  = 4
        }
    }

    opcode.mandatory {
        eltwise<f32>.default            # FP32 elementwise for high-precision post-ops
        eltwise<bf16>.default           # BF16 elementwise
        view<f32>.default               # FP32 view ops
    }
}
```

#### NEM Program

```text
device "npm_quad_cstl.cfg"

program gemm_relu_multi_cstl:

# --- Compile-time constants ---
const TiM = 64
const K = 256
const N = 128
const T = 8

const elem_bytes = 2                        # f16 = 2 bytes per element
const tileX_bytes = TiM * K * elem_bytes     # 32768
const tileW_bytes = K * N * elem_bytes       # 65536
const tileY_bytes = TiM * N * elem_bytes     # 16384

buffer X_L2 : L2 (size=T * tileX_bytes, align=64)
buffer W_L2 : L2 (size=tileW_bytes, align=64)
buffer Y_L2 : L2 (size=T * tileY_bytes, align=64)

buffer X_L1 : L1 (size=4*tileX_bytes, align=64)   # 4-slot ring buffer
buffer W_L1 : L1 (size=tileW_bytes,   align=64)
buffer Y_L1 : L1 (size=4*tileY_bytes, align=64)   # 4-slot ring buffer

loop i in [0..T-1] @max_in_flight(4):

  let X_slot = region(X_L1, (i mod 4)*tileX_bytes, tileX_bytes)
               elem=f16, shape=[TiM, K], layout=MK
  let Y_slot = region(Y_L1, (i mod 4)*tileY_bytes, tileY_bytes)
               elem=f16, shape=[TiM, N], layout=MN
               @materialized

  let X_tile_i = region(X_L2, i * tileX_bytes, tileX_bytes)
                 elem=f16, shape=[TiM, K], layout=MK
  let Y_tile_i = region(Y_L2, i * tileY_bytes, tileY_bytes)
                 elem=f16, shape=[TiM, N], layout=MN
  let W_l1 = region(W_L1, 0, tileW_bytes)
             elem=f16, shape=[K, N], layout=KN
  let W_l2 = region(W_L2, 0, tileW_bytes)
             elem=f16, shape=[K, N], layout=KN

  tX = transfer.async(dst=X_slot, src=X_tile_i)  @resource(DMA[0])
  tW = transfer.async(dst=W_l1,   src=W_l2)      @resource(DMA[1])
  wait(tX, tW)

  tC = gemm.async
         in  X_slot, W_l1
         out Y_slot
         deps=[tX, tW]
         accum_type=f32
         @resource(NMU[0])

  tR = relu.async
         in  Y_slot
         out Y_slot @materialized
         deps=[tC]
         @resource(CSTL[i mod 4])

  tS = store.async(dst=Y_tile_i, src=Y_slot, deps=[tR])
       @resource(CSTL[i mod 4])

endloop
```

Key observations:

- `@max_in_flight(4)` matches the 4 CSTL instances. Bounded pipelining and resource
  counts work together: 4 iterations can overlap, each using a distinct CSTL.
- Each iteration's post-op chain (relu + store) binds to the same CSTL instance via
  `i mod 4`, matching the hardware's CSTLA→CSTLB pipeline within one CSTL pair.
- The single NMU is the throughput bottleneck: `@resource(NMU[0])` makes this explicit.
  While NMU processes tile `i`, CSTLs concurrently handle post-ops for tiles `i-1`, `i-2`, `i-3`.
- DMA channels are explicitly assigned for prefetch overlap.
- On a device with `units[CSTL] = 2`, the same program remains valid: the binder remaps
  `CSTL[2]` and `CSTL[3]` to available instances per the same-type remap rule. Performance
  degrades gracefully (2-way instead of 4-way CSTL pipelining), but correctness is preserved.

### Future Multi-NMU Extension

The same model extends naturally when an engine has multiple NMU instances:

```text
# Target: capabilities.per_engine.units[NMU] = 2

loop i in [0..T-1] @max_in_flight(2):

  tC = gemm.async
         in  X_slot_i, W_l1
         out Y_slot_i
         accum_type=f32
         @resource(NMU[i mod 2])
  ...
endloop
```

Two GEMM tiles execute concurrently on separate NMU instances. The `@max_in_flight(2)`
bound matches the NMU count, ensuring safe L1 buffer reuse.


## TCB-Level Realization for Conv2D + ReLU

This section shows the packed TCB stream that realizes one NEM tile iteration for a Conv2D+ReLU pipeline.
Two tiles are fully expanded, then we describe a generator rule.

### Conventions Used

#### Packed TCB Header (7 bytes)

As defined by the Sequencer packed TCB format:

- `TaskID`   : 16-bit unsigned
- `TaskLen`  : 8-bit unsigned (number of register updates in this task)
- `SBTS`     : 16-bit unsigned (SYNQ "start/trigger" / dependency mask semantics)
- `SBTP`     : 16-bit unsigned (SYNQ "produce" / completion mask semantics)

Header byte order (byte indices 0..6):

- bytes [0..1] : `TaskLen[7:0]` and `TaskID[15:0]` (per Sequencer spec figure)
- bytes [2..3] : `SBTS[15:0]`
- bytes [4..5] : `SBTP[15:0]`
- byte  [6]    : (the packed TCB format implies header is 7 bytes; interpretation aligns with the Sequencer spec's header diagram)

> Note: The Sequencer spec also defines sequential vs non-sequential mode via TaskID encoding (TID bit patterns). In this example, we use **non-sequential mode** so every (address,value) pair is explicit.

#### Non-Sequential Register Update Encoding

Each register update is encoded as:

- `A` : 8-bit register address index
- `V` : 32-bit value

Packed as: `A0, V0, A1, V1, ...`

The meaning of `A` is "unit-local register address index" consumed by the unit decoder.

For CDMA, we bind `A = addressOffset_bytes / 4` within the unit's shadow register file (word addressing),
which matches the register map's natural 32-bit register alignment.

#### Task IDs (Non-Sequential)

From the Sequencer spec task ID table (non-sequential mode encodings shown as 7-bit patterns embedded in 16-bit TaskID):

- NMU     : `0100001b`
- DMAr0   : `0100010b`
- DMAr1   : `0100011b`
- DMAw    : `0100100b`
- CSTLA0  : `0100101b`
- CSTLB0  : `0101001b`
- DMAr2   : `0101111b` (if used)

We will encode these as 16-bit `TaskID` values with the above 7-bit pattern in the low bits and the rest zero
(typical usage; if your integration uses additional high bits, adjust accordingly).

#### Synchronization Tokens via SBTS/SBTP

`SBTS` and `SBTP` are used by SYNQ.
Exact bit assignments depend on your system-level SYNQ wiring and tag plan.

In this example we define a **concrete illustrative assignment** (so the packed TCB is fully specified):

- `BIT0`: X_TILE_LOADED
- `BIT1`: W_TILE_LOADED
- `BIT2`: CONV_DONE
- `BIT3`: RELU_DONE
- `BIT4`: Y_TILE_STORED

Then:
- tasks that consume prerequisites set `SBTS` to the required bitmask
- tasks that produce completion set `SBTP` to the produced bitmask

> If your SYNQ assigns different bit meanings, you must adjust SBTS/SBTP accordingly. The packed stream structure remains identical.

---

### Tile i=0 : Fully Expanded Packed TCB Stream

We show a minimal but complete pipeline:

1. DMAr0 : load X tile from L2 → L1 ping
2. DMAr1 : load W tile from L2 → L1 (weights)
3. NMU   : run Conv2D for this tile into L1 output ping
4. CSTLA0: run ReLU post-op on the L1 output ping (or fused post-op stage)
5. CSTLB0: store Y tile from L1 ping → L2

#### DMAr0 (X tile load) — Non-Sequential

**Header**
- TaskID  = DMAr0 = 0x0022  (binary low bits `0100010`)
- TaskLen = 0x0C  (12 register writes shown below)
- SBTS    = 0x0000 (no prereq)
- SBTP    = 0x0001 (produce X_TILE_LOADED)

**Register writes (CDMA shadow regs, word addressing)**

CDMA shadow block registers (semantic names from CDMA XML):
- `DTC_CTRL0` @ offset 0x04 → A=0x01
- `DTC_SSA`   @ offset 0x08 → A=0x02  (source start address)
- `DTC_DSA`   @ offset 0x0C → A=0x03  (dest start address)
- `DTC_SBEN`  @ offset 0x10 → A=0x04
- `DTC_DBEN`  @ offset 0x14 → A=0x05
- `DTC_CBN`   @ offset 0x18 → A=0x06
- `DTC_SFCN`  @ offset 0x1C → A=0x07
- `DTC_DFCN`  @ offset 0x20 → A=0x08
- `DTC_SBPM`  @ offset 0x24 → A=0x09
- `DTC_DBPM`  @ offset 0x28 → A=0x0A
- `DTC_CTRL1` @ offset 0x74 → A=0x1D
- `DTC_SSU_ID`@ offset 0x64 → A=0x19

Packed register list:

- A=0x01  V=CTRL0_XREAD(i=0)
- A=0x02  V=SRC_L2_X_BASE + fX(0)
- A=0x03  V=DST_L1_X_PING_BASE
- A=0x04  V=SRC_BURST_MODE_X
- A=0x05  V=DST_BURST_MODE_X
- A=0x06  V=BYTE_COUNT_X_TILE
- A=0x07  V=SRC_STRIDE_CFG_X
- A=0x08  V=DST_STRIDE_CFG_X
- A=0x09  V=SRC_BANK_SEL_X
- A=0x0A  V=DST_BANK_SEL_X
- A=0x1D  V=ARB_HINTS_X
- A=0x19  V=PATH_RESTRICTIONS_X

> Notes:
> - `CTRL0_XREAD` includes transfer direction, enable/start, and mode bits.
> - Burst modes / bank selection / arbitration hints are *microarchitectural policies* that exist in TCB but not in NEM.

---

#### DMAr1 (W tile load) — Non-Sequential

**Header**
- TaskID  = DMAr1 = 0x0023
- TaskLen = 0x0C
- SBTS    = 0x0000
- SBTP    = 0x0002 (produce W_TILE_LOADED)

**Register writes**
(Same register set as above; values differ.)

- A=0x01  V=CTRL0_WREAD(i=0)
- A=0x02  V=SRC_L2_W_BASE + fW(0)
- A=0x03  V=DST_L1_W_BASE
- A=0x04  V=SRC_BURST_MODE_W
- A=0x05  V=DST_BURST_MODE_W
- A=0x06  V=BYTE_COUNT_W_TILE
- A=0x07  V=SRC_STRIDE_CFG_W
- A=0x08  V=DST_STRIDE_CFG_W
- A=0x09  V=SRC_BANK_SEL_W
- A=0x0A  V=DST_BANK_SEL_W
- A=0x1D  V=ARB_HINTS_W
- A=0x19  V=PATH_RESTRICTIONS_W

---

#### NMU (Conv2D compute) — Non-Sequential, R-word Programming

**Header**
- TaskID  = NMU = 0x0021
- TaskLen = 0x20  (example: 32 words; adjust to your exact conv mode requirements)
- SBTS    = 0x0003 (wait for X_TILE_LOADED | W_TILE_LOADED)
- SBTP    = 0x0004 (produce CONV_DONE)

**Register writes**
The Engine CPM IP-XACT exposes the NMU task-programming space as `NMU_TCB: R1..R62`
with 32-bit words at offsets 0x00,0x04,... The packed TCB address byte is:

- `A = (offset_bytes / 4)` i.e., `R1 -> A=0x00`, `R2 -> A=0x01`, ...

We program the required NMU TCB words for Conv2D tile execution:

- A=0x00  V=R1_MODE_CONV2D
- A=0x01  V=R2_DATATYPE_CFG
- A=0x02  V=R3_ACCUM_CFG
- A=0x03  V=R4_IN_BASE_L1_X_PING
- A=0x04  V=R5_W_BASE_L1_W
- A=0x05  V=R6_BIAS_BASE_L2_B
- A=0x06  V=R7_OUT_BASE_L1_Y_PING
- A=0x07  V=R8_DIMS_AND_TILE_GEOM
- A=0x08  V=R9_STRIDES_INPUT
- A=0x09  V=R10_STRIDES_OUTPUT
- A=0x0A  V=R11_PADS_DILATIONS
- A=0x0B  V=R12_GROUPS_CHANNELS
- A=0x0C  V=R13_BANK_SEL_IN
- A=0x0D  V=R14_BANK_SEL_OUT
- A=0x0E  V=R15_ARB_HINTS
- A=0x0F  V=R16_PATH_RESTRICTIONS
- A=0x10  V=R17_STORE_FORMAT_CFG
- A=0x11  V=R18_BURST_HINTS
- A=0x12  V=R19_MISC_CTRL
- A=0x13  V=R20_RESERVED0
- A=0x14  V=R21_RESERVED1
- A=0x15  V=R22_RESERVED2
- A=0x16  V=R23_RESERVED3
- A=0x17  V=R24_RESERVED4
- A=0x18  V=R25_RESERVED5
- A=0x19  V=R26_RESERVED6
- A=0x1A  V=R27_RESERVED7
- A=0x1B  V=R28_RESERVED8
- A=0x1C  V=R29_RESERVED9
- A=0x1D  V=R30_RESERVED10
- A=0x1E  V=R31_RESERVED11
- A=0x1F  V=R32_END

> Important:
> - This is **exact packed TCB structure** for NMU as the sequencer sees it: (A,V) pairs over the NMU_TCB address space.
> - The **semantic meaning of each R-word** (e.g., which word encodes base address, strides, formats, etc.) is defined in the NMU Architecture Spec.
> - The point here is to show that at TCB level you must encode many microarch knobs (store format, arbitration hints, path restrictions) that are not in NEM.

---

#### CSTLA0 (ReLU post-op) — Non-Sequential, R-word Programming

**Header**
- TaskID  = CSTLA0 = 0x0025
- TaskLen = 0x18
- SBTS    = 0x0004 (wait CONV_DONE)
- SBTP    = 0x0008 (produce RELU_DONE)

**Register writes**
CSTL A0 programming space is `CSTL_TCB_A_0: R1..R222` (32-bit words).

Address byte mapping:
- `R1 -> A=0x00`, `R2 -> A=0x01`, ...

Example post-op programming:

- A=0x00  V=R1_MODE_RELU
- A=0x01  V=R2_DATATYPE_CFG
- A=0x02  V=R3_IN_BASE_L1_Y_PING
- A=0x03  V=R4_OUT_BASE_L1_Y_PING   # in-place
- A=0x04  V=R5_DIMS_TILE_GEOM
- A=0x05  V=R6_STRIDES
- A=0x06  V=R7_STORE_FORMAT_CFG
- A=0x07  V=R8_BANK_SEL
- A=0x08  V=R9_ARB_HINTS
- A=0x09  V=R10_PATH_RESTRICTIONS
- A=0x0A  V=R11_MISC_CTRL
- A=0x0B  V=R12_RESERVED0
- ...
- A=0x17  V=R24_END

---

#### CSTLB0 (Store Y tile) — Non-Sequential, R-word Programming

**Header**
- TaskID  = CSTLB0 = 0x0029
- TaskLen = 0x14
- SBTS    = 0x0008 (wait RELU_DONE)
- SBTP    = 0x0010 (produce Y_TILE_STORED)

**Register writes**
CSTL B0 programming space is `CSTL_TCB_B_0: R1..R136` (32-bit words).

- A=0x00  V=R1_MODE_STORE
- A=0x01  V=R2_SRC_BASE_L1_Y_PING
- A=0x02  V=R3_DST_BASE_L2_Y + fY(0)
- A=0x03  V=R4_BYTE_COUNT_Y_TILE
- A=0x04  V=R5_DST_STRIDES
- A=0x05  V=R6_STORE_FORMAT_CFG
- A=0x06  V=R7_BURST_MODE
- A=0x07  V=R8_BANK_SEL
- A=0x08  V=R9_ARB_HINTS
- A=0x09  V=R10_PATH_RESTRICTIONS
- ...
- A=0x13  V=R20_END

---

### Tile i=1 : Fully Expanded (Shows Address Evolution + Ping-Pong)

Only values that change are shown explicitly; structure is identical.

#### DMAr0 (X tile load for i=1)

Header:
- TaskID=DMAr0, TaskLen=0x0C, SBTS=0x0000, SBTP=0x0001

Register deltas vs i=0:
- `DTC_SSA` (A=0x02): `SRC_L2_X_BASE + fX(1)`
- `DTC_DSA` (A=0x03): `DST_L1_X_PONG_BASE`  (ping-pong)
All other control/microarch policy fields remain as chosen.

#### NMU (Conv2D for i=1)

Header:
- TaskID=NMU, TaskLen=0x20, SBTS=0x0003, SBTP=0x0004

Register deltas:
- `R4_IN_BASE_L1_X_PONG`
- `R7_OUT_BASE_L1_Y_PONG`

#### CSTL (ReLU and Store for i=1)

Similarly:
- ReLU operates on `L1_Y_PONG`
- Store writes `DST_L2_Y + fY(1)`

---

### Generator Rule (How the Full Tensor is Realized)

The full layer's TCB stream is produced by unrolling (flatterning) the tile program:

```text
for i in 0..T-1:
  emit(DMAr0_X_load(i))
  emit(DMAr1_W_load(i or hoisted))
  emit(NMU_conv(i))
  emit(CSTLA0_relu(i))
  emit(CSTLB0_store(i))
end
emit(RESET_SEQUENCER header)
```

### Relationship between NEM and TCBs

Lowering from NEM to TCBs binds:
- physical addresses,
- bank and slice selection,
- burst modes,
- store formats,
- arbitration hints,
- synchronization tags and chaining.

These bindings MUST NOT affect the architectural semantics defined by NEM.


---

