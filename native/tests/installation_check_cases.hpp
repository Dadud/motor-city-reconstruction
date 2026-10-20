#pragma once
#include "mco/installation_check.hpp"
#include "cell_io.hpp"
#include <algorithm>
#include <array>
#include <string>
#include <string_view>
#include <vector>

namespace installation_check_cases {
struct Boundary { std::uint32_t seed; std::vector<std::uint32_t> log; };
inline std::string stock_name(std::uint32_t id);
inline std::uint32_t put_word(std::span<std::byte> out, std::uint32_t value) {
    for (unsigned i = 0; i < 4; ++i) out[i] = std::byte((value >> (8 * i)) & 255);
    return value;
}
inline std::uint32_t invoke(mco::InstallationState& state,
                            const mco::InstallationCall& call, void* user) {
    auto& b = *static_cast<Boundary*>(user);
    const auto id = call.id;
    const auto arg = [&](std::size_t i) { return call.args[i]; };
    const auto owner = 0x71000400u, root = 0x71000100u, candidate = 0x71000200u;
    const auto cdroot = 0x71000300u, level = 0x71000500u;
    std::vector<std::uint32_t> args;
    if (id == 1 || id == 4) args = {owner, arg(1), arg(2), arg(3)};
    else if (id == 2 || id == 12) args = {owner};
    else if (id == 3) args = {owner, arg(1), root, arg(3)};
    else if (id == 5) args = {owner, arg(1), level};
    else if (id == 7) args.assign(call.args.begin(), call.args.end());
    else if (id == 8 || id == 10 || id == 11) args = {arg(0)};
    else if (id == 9) args = {candidate, arg(1)};
    else throw std::invalid_argument("installation helper id");
    b.log.push_back(id); b.log.push_back(static_cast<std::uint32_t>(args.size()));
    b.log.insert(b.log.end(), args.begin(), args.end());

    const auto config = b.seed % 8;
    if (id == 2) return config != 0;
    if (id == 3) {
        const char* roots[] = {"C:\\ROOT\\", "C:\\ROOT\\\\", "ROOT", "C:\\"};
        const auto* text = roots[b.seed % 4];
        for (std::size_t i = 0; text[i] && i < call.destination.size(); ++i)
            call.destination[i] = std::byte(text[i]);
        return b.seed % 2;
    }
    if (id == 4) return config != 1;
    if (id == 5) {
        constexpr std::uint32_t levels[] = {0, 1, 2, 0xffffffff, 3, 0x80000000,
                                            0x7fffffff, 0xfffffffe};
        call.locals.level = levels[(b.seed / 8) % 8];
        return config != 2;
    }
    if (id == 1) return 0;
    if (id == 7) {
        auto output = call.destination;
        std::vector<std::byte> value;
        if (arg(1) == 0x8885b8) {
            const char* text = "C:\\mcity.exe";
            for (std::size_t i = 0; text[i]; ++i) value.push_back(std::byte(text[i]));
        } else if (arg(1) == 0x896148) {
            for (char c : std::string_view("c:\\")) value.push_back(std::byte(c));
        } else {
            const auto& src = arg(1) == 0x896140 ? call.locals.root : call.locals.cdroot;
            const auto end = std::find(src.begin(), src.end(), std::byte{});
            value.assign(src.begin(), end);
            if (arg(1) == 0x896140) value.push_back(std::byte{'\\'});
            const auto name = arg(3);
            if (name >= 0x71008000 && name < 0x710081f0) {
                const auto index = static_cast<unsigned>((name - 0x71008000) / 16);
                const auto text = std::string("ITEM") + (index < 10 ? "0" : "") + std::to_string(index);
                for (char c : text) value.push_back(std::byte(c));
            } else {
                const auto text = stock_name(name);
                for (char c : text) value.push_back(std::byte(c));
            }
        }
        const auto n = std::min(value.size(), output.size());
        std::copy_n(value.begin(), n, output.begin());
        if (n < output.size()) output[n] = std::byte{};
        if (b.seed & 64) state.flags[1] ^= 0x80000000;
        return 0;
    }
    if (id == 8) {
        if (b.seed & 256) state.flags[3] += 17;
        const auto drive_mask = (b.seed / 8) % 4 == 0 ? 0u :
            (b.seed / 8) % 4 == 1 ? (1u << 2) :
            (b.seed / 8) % 4 == 2 ? ((1u << 2) | (1u << 5) | (1u << 25)) : 0x3ffffffu;
        return (drive_mask & (1u << arg(0))) != 0;
    }
    if (id == 9) {
        const auto drive = std::to_integer<unsigned char>(call.locals.candidate[0]) - 97;
        const auto mode = (b.seed / 32) % 4;
        const auto mask = mode == 0 ? 0u : mode == 1 ? (1u << 2) :
                          mode == 2 ? ((1u << 5) | (1u << 25)) : 0x3ffffffu;
        return (mask & (1u << drive)) ? 0x71009000u + drive * 16 : 0;
    }
    if (id == 10) { if (b.seed & 128) call.locals.candidate[0] = std::byte{'M'}; return 0; }
    if (id == 11) return 0x12340000u + b.seed;
    if (id == 12) { if (b.seed & 32) state.flags[1] ^= 0x80000000; return 0; }
    return 0;
}
inline std::string stock_name(std::uint32_t id) {
    switch (id) {
    case 0x8e3ac4: return ""; case 0x896110: return "SaveData\\";
    case 0x896100: return "Data\\Tracks\\"; case 0x8960f0: return "Data\\GameArt\\";
    case 0x8960e4: return "Data\\Parts\\"; case 0x8960d0: return "Data\\Audio\\Music\\";
    case 0x8960c0: return "Data\\Audio\\SFX\\"; case 0x8960ac: return "Data\\Audio\\Speech\\";
    case 0x896094: return "Data\\Audio\\Speechdata\\"; case 0x896088: return "Data\\Menus\\";
    case 0x89607c: return "Data\\Text\\"; case 0x896070: return "Data\\Fonts\\";
    case 0x896064: return "Data\\FeArt\\"; case 0x896058: return "Data\\DB\\";
    case 0x896048: return "Data\\Movies\\"; case 0x896038: return "Data\\Models\\";
    case 0x89602c: return "Data\\Skins\\"; case 0x896020: return "Data\\GUI\\";
    case 0x896014: return "Data\\Html\\"; default: throw std::invalid_argument("unknown stock path identity");
    }
}
inline void compare(std::istream& in) {
    using namespace cell_io;
    const auto seed = read(in), count = read(in);
    std::vector<mco::InstallationRow> rows;
    for (std::uint32_t i = 0; i < count; ++i) rows.push_back({read(in), read(in)});
    std::array<std::uint32_t, 4> flags{}; for (auto& x : flags) x = read(in);
    std::array<std::byte, 8320> paths{};
    for (std::size_t i = 0; i < paths.size(); ++i) paths[i] = std::byte((seed + i * 13) & 255);
    mco::InstallationState state{paths, flags}; Boundary boundary{seed, {}};
    const auto result = mco::installation_check(state, rows, {invoke, &boundary});
    emit(result); for (auto x : state.flags) emit(x); for (auto x : paths) emit(std::to_integer<std::uint8_t>(x));
    emit(static_cast<std::uint32_t>(boundary.log.size())); for (auto x : boundary.log) emit(x);
}
}
