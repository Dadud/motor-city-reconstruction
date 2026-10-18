#pragma once
#include "mco/input_keyboard_layout.hpp"
#include "mco/window_keyboard_binding.hpp"
namespace mco {
// Other nonzero identities still require the caller's explicitly mapped view.
// The original selected identity resolves to the shared translation image.
inline std::uint32_t window_keyboard_layout_binding(InputKeyQueue& queue,
    std::span<const std::byte,scan_translation_tables::size> tables,
    std::span<const std::byte,128> other_remap,std::uint32_t handler,
    std::uint32_t owner,std::uint32_t window,std::uint32_t message,
    std::uint32_t wparam,std::uint32_t lparam) {
    const auto remap=queue.load(input_queue_image::remap)==keyboard_scan_remap_identity ?
        input_keyboard_remap(tables):other_remap;
    return window_keyboard_binding(queue,remap,handler,owner,window,message,wparam,lparam);
}
}
