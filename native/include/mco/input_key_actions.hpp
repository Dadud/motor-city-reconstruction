#pragma once
#include "mco/layouts.hpp"
#include "mco/detail/byte_words.hpp"
namespace mco {
struct InputKeyActions;
using InputKeyActionInvoke=void (*)(InputKeyActions&,std::uint32_t identity,void* user);
struct InputKeyActions {
    const std::span<std::byte,input_action_image::size> image;
    InputKeyActionInvoke invoke{};
    void* user{};
};
// Original 0x6f0e80; mapped signed low indices are intentional.
std::uint32_t input_key_action(InputKeyActions&,std::uint32_t code);
}
