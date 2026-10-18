#include "mco/startup_record.hpp"
#include <array>
#include <bit>
#include <cstdint>
#include <stdexcept>

int main() {
    std::array<std::byte,0x1c94> owner{};
    std::array<std::byte,0x820> configuration{};
    std::array<std::byte,0x1400> model{};
    std::array<std::byte,0x4a8> record;
    const auto put32 = [](auto& data, size_t offset, std::uint32_t bits) {
        for (unsigned k = 0; k < 4; ++k)
            data[offset+k] = static_cast<std::byte>((bits>>(k*8))&255);
    };
    bool rejected = false;
    try { mco::startup_record(owner, {}, true, model, 2.05f, record); }
    catch (const std::invalid_argument&) { rejected = true; }
    if (!rejected) throw std::runtime_error("truncated configuration accepted");
    if (mco::startup_record(owner, configuration, true, model, 2.05f, record))
        throw std::runtime_error("model without wheel markers accepted");
    // Both markers present: the run reaches the balance coefficient producers,
    // which reject the degenerate all-zero configuration as they do in the
    // translated constructor.
    put32(model, 0x11c, 1);
    for (unsigned k = 0; k < 10; ++k)
        model[0xe28+k] = static_cast<std::byte>(":PPLFwheel"[k]);
    put32(model, 0x128, std::bit_cast<std::uint32_t>(1.35f));
    if (mco::startup_record(owner, configuration, true, model, 2.05f, record))
        throw std::runtime_error("missing rear marker accepted");
    rejected = false;
    try { mco::startup_record(owner, configuration, false, model, 0.f, record); }
    catch (const std::invalid_argument&) { rejected = true; }
    if (!rejected) throw std::runtime_error("degenerate configuration accepted");
    return 0;
}