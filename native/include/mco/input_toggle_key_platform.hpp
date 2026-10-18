#pragma once
#include <cstdint>
namespace mco {
struct InputToggleKeyPlatform {
    std::uint32_t (*query)(std::uint32_t virtual_key, void* user){};
    void (*event)(std::uint32_t virtual_key, std::uint32_t scan,
                  std::uint32_t flags, std::uint32_t extra, void* user){};
    void* user{};
};
}
