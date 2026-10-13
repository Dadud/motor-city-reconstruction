# Owned-part condition, repair cost and scrap value

This is the post-load calculation in original `0x66f7d0`, after owned-instance,
branded metadata, abstract-type and physics loading. `client.owned_valuation`
reconstructs this stage; it does not establish all pricing rules or implement
complete repair/scrap transactions. The calculation skips slots with zero
PartID or BrandedPartID and updates only RepairCost (`0x62c`) and ScrapValue
(`0x630`). It preserves instance damage and wear.

## Inputs and factors

| Symbol | Original input |
| --- | --- |
| P | Intermediate retail price, signed int32 at `0x1eb` |
| D | PercentDamage, signed int32 at `0x610` |
| W | ItemWear, signed int32 at `0x614` |
| M | MaxItemWear, signed int32 at `0x1ef`, replaced by physics loading |
| R | Server double at `0x1e` in data reply `0x186` |
| S | Server double at `0x26` in that reply |
| V11 | Physics Val11, float32 at owned-part offset `0x454` |

Original getters `0x4bec70` and `0x4bec30` return R and S. An absent data
lookup supplies 0.1 and 0.75; a present zero factor stays zero.
`PartValuationRates.from_reply` accepts a decoded `MCOTSFixed186Record`, or
explicit `None` for the absent-data case. Nonfinite factors are rejected by
the authored API. The separately loaded abstract-type RepairCostModifier and
ScrapValueModifier at `0x1db` and `0x1df` are not read by this calculation.
Their names do not justify substituting them for R and S.

## Calculation sequence

`f32` denotes a float32 store/reload. `T` denotes the original `__ftol` bits
consumed by these callers. The percentage constant is float32
`0.009999999776482582`, rather than exact decimal 0.01.

1. If M is zero, wear condition C is 1. Otherwise,
   `C = f32(1 - W / M)`. The original does not clamp it to 0–1.
2. If D is zero, repair cost A is zero. Otherwise,
   `A = max(1, T((R * P) * (D * percentage_constant) + 0.5))`.
3. Compute `B = T((S * P) * C + 0.5)`.
4. Compute the floating remainder `B - f32(A)`. If negative, initial scrap Q
   is zero; otherwise Q is `T(remainder)`.
5. For abstract type IDs 20001 through 20999 inclusive, replace Q with
   `T(S * V11 + Q)`. This term has neither a 0.5 rounding addition nor a
   final nonnegative clamp. Val11's broader physical/business meaning remains
   unresolved; this consumer establishes its role here.
6. Write A and Q back. The original recalculates A before its final store;
   fixed factors produce the same result.

The oracle uses x87 53-bit precision, preserves operation order, and executes
the original getters, arithmetic and conversion routine. Float32 stores for
condition and repair subtraction matter. `__ftol` selects truncation toward
zero and writes signed int64; these callers use signed low 32 bits in EAX.
Out-of-range x87 integer conversion produces indefinite int64, whose low
word is zero. The authored implementation reproduces those consumed bits
rather than substituting integer saturation.

At P=500, D=20, W=250, M=1000, R=0.1 and S=0.75, the result is condition
0.75, repair cost 10 and scrap value 271. A body-range type with Val11=123.25
gets final scrap 363. At P=500 and D=17, the percentage constant makes the
repair expression slightly less than 9 after adding 0.5, so truncation gives
8. Exact decimal 0.01 would give 9. P=25 and D=100 similarly gives repair
cost 2 rather than 3. Ordinary decimal rounding would change original behavior.

## Integration and verification

`fetch_valuation_data(data_client)` sends recovered request `0x185`, decodes
the fixed reply, and returns factors alongside its complete raw record and
extensions. Rejections propagate without retries or default-factor substitution.
This API does not prescribe the original startup's lazy query timing.

Pass the returned `.rates` as `valuation_rates` to
`Catalogue.owned_part_intermediate`. Without this argument the catalogue
preserves cached costs. Explicit `PartValuationRates.from_reply(None)` selects
the recovered absent-data defaults, rather than implying server acceptance.
An encrypted real local TCP test verifies request bytes, factor decoding,
extension retention, and their use in the reconstructed calculation. Its peer
is synthetic, not the fan server.

`python -m tools.owned_valuation_oracle /path/to/original/mcity.exe` compares
30 synthetic cases against original `0x66f944`–`0x66fb04` execution. It covers
zero/nonzero damage, zero wear limit, over-wear, rounding boundaries, body-range
boundaries, different factors, absent-data defaults and large signed inputs.
Every byte of the 1596-byte slot is compared. Only the server-data lookup
boundary is substituted; no network or database service executes.

Read-only integration against the external installed database also passes
4,257 supported branded-part joins with explicit default factors, preserving
damage throughout. The invalid-date row remains excluded. These checks do not
prove complete transactions, every original floating-point mode, or live
authenticated fan-server compatibility.

Source executable SHA-256:
`28c0cdde77ed24bac6aeeea65699c16be0f31e6aa8cb5db38417f0f3d5880164`.
REA evidence: `ev_0c2e29564588cfa56a0fcded684afbad43fe08f6d70e5b6f91549b0856c027c8`
(post-load flow), `ev_000473de8ec8392c71f1f91f0adc33875df941ed2ce7ab5b9b3b306dfc61e6ff`
(repair factor), `ev_01e2f2f4514ec1cd67bf4f7251f811bf80117eafd954aa98c59c522a89cb6eaa`
(scrap factor), and `ev_79b8b4bc38a157029a6a61e89373f46bdd6268fedb51f78b850cfca097a1449a`
(integer conversion).
