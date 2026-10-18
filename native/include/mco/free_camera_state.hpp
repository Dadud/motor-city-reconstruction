#pragma once
#include "mco/layouts.hpp"
#include "mco/track_surface_world.hpp"
namespace mco {
using CameraSubjectResolver=std::span<const std::byte,68> (*)(std::uint32_t identity,void* user);
struct FreeCameraState {
    std::span<std::byte,free_camera_image::size> image;
    std::span<const std::byte,128> keys;
    std::span<std::byte,512> latches;
    // Resolve after reset, which may change the opaque subject identity.
    CameraSubjectResolver resolve_subject{};
    void* user{};
};
}
