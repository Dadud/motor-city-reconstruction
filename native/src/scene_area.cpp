#include "mco/scene_area.hpp"
#include <stdexcept>

namespace mco {
// ABI proven from the sole call site and the callee epilogue:
// 0x483450cd is a plain RET, so the routine is cdecl, and the caller at
// 0x53a805 executes ADD ESP,0x14, which is five dword arguments.
// 0x53a7c8 PUSH ECX then 0x53a7c9 PUSH EDI puts arg1 = EDI (the owner)
// and arg2 = [EBP+0xc] (the constructor's second parameter); the other
// three are pushed earlier and still live: EAX from 0x53a7aa and the two
// slots at 0x53a791/0x53a792 reused by the 0x006f1430 calls.
// The return is binary32 in ST0: 0x53a7ff FCOM compares it against 0x0.
// Ghidra's pseudocode reconstructs two arguments; the epilogue and the
// caller's ADD ESP disagree with it, and the assembly is authoritative.
// Arg1 is a pointer, not a number: 0x483487 loads [EBP+8] into EAX and
// 0x48348a dereferences it at +0x490. The FIMUL [EBP+8] on the last block
// belongs to a different path, and that slot is overwritten with ECX at
// 0x4836c4 before the divide, so it reads a reused scratch value.
// Body characterization: the routine allocates a 0x890238-byte scene
// singleton through 0x006ee510, zeroes 0x4b8c dwords of it, then walks
// per-surface geometry indexed by a 16-bit surface id (owner+0x420,
// +0x620, +0x720, triangle data at +0x48 and +0x2038), accumulating
// surface area. The result therefore depends on real scene and terrain
// state that no current harness builds.

float scene_area(std::uint32_t owner, std::uint32_t parameter, std::uint32_t turn_limit, std::uint32_t turn_scale, std::uint32_t context) {
    throw std::logic_error(
        "cell scene_area scaffolded: implement original 0x483450");
}

}  // namespace mco
