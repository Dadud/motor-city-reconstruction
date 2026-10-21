#pragma once
#include <array>
#include <cstdint>
#include <functional>
#include <span>

namespace mco {
struct ContactResponse {
    std::array<float,3> linear{};
    std::array<float,3> angular{};
};
using ContactResponseFn = std::function<ContactResponse(
    std::span<const std::uint8_t>, const std::array<float,3>&,
    const std::array<float,3>&, const std::array<float,3>&)>;

ContactResponse contact_response(
    std::span<const std::uint8_t> record,
    const std::array<float,3>& force,
    const std::array<float,3>& contact_point,
    const std::array<float,3>& normal);
void contact_forces_step(std::span<std::uint8_t> record,
                         const ContactResponseFn& response = contact_response);
}
