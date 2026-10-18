#include "mco/input_scan_translate.hpp"
#include <stdexcept>

namespace mco {

// Decompiled pseudocode of 0x6f05b0, kept as the implementation draft.
// The oracle against the original, not this text, decides correctness.


std::uint32_t input_scan_translate(InputTranslationState &state, std::uint32_t scan, std::uint32_t extended) {
    (void)extended; // Passed by queue callers, never read by this original body.
    if(!state.get_state) throw std::invalid_argument("input device state bridge required");
    const auto device=state.get_state(state,6,state.user);
    if(scan==0x3a) {state.caps=state.caps==0 ? 1u:0u;return 0;}
    if(scan>255 || device.size()<=direct_key_image::alt_right)
        throw std::invalid_argument("scan/modifier view outside supplied input domain");
    auto pressed=[&](std::size_t offset) {return device[offset]!=std::byte{};};
    std::size_t plane=0;
    if(pressed(direct_key_image::alt_left) || pressed(direct_key_image::alt_right)) plane=4;
    else if(pressed(direct_key_image::control_left) || pressed(direct_key_image::control_right)) {
        if(state.escape_exits!=0 && scan==1) {
            if(!state.exit_request) throw std::invalid_argument("input exit-request bridge required");
            state.exit_request(state,0,state.user);
            throw std::logic_error("nonreturning input exit-request bridge returned");
        }
        plane=3;
    } else if(pressed(direct_key_image::shift_left) || pressed(direct_key_image::shift_right)) plane=1;
    else if(state.caps!=0) plane=2;
    constexpr std::array<std::size_t,5> starts{scan_translation_tables::normal,
        scan_translation_tables::shift,scan_translation_tables::caps,
        scan_translation_tables::control,scan_translation_tables::alt};
    auto value=std::to_integer<std::uint32_t>(state.tables[starts[plane]+scan]);
    if(value>=128) {
        if(value>=144) value&=127;
        return value<<8;
    }
    return value;
}

}  // namespace mco
