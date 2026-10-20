#include "mco/installation_check.hpp"
#include <algorithm>
#include <bit>
#include <initializer_list>
#include <stdexcept>

namespace mco {
std::uint32_t installation_check(InstallationState& state,
                                 std::span<const InstallationRow> rows,
                                 const InstallationPlatform& platform) {
    if (rows.size() > 31) throw std::out_of_range("installation row terminator domain");
    if (!platform.invoke) throw std::invalid_argument("installation platform required");
    std::fill(state.paths.begin(), state.paths.end(), std::byte{});
    InstallationLocals locals{};
    constexpr std::uint32_t owner = 0x71000400, root = 0x71000100;
    constexpr std::uint32_t candidate = 0x71000200, cdroot = 0x71000300;
    constexpr std::uint32_t level = 0x71000500;
    auto call = [&](std::uint32_t id, std::initializer_list<std::uint32_t> args,
                    std::span<std::byte> destination = {}) {
        return platform.invoke(state, {id, {args.begin(), args.size()}, destination, locals},
                               platform.user);
    };
    auto close = [&](std::uint32_t result) { call(12, {owner}); return result; };

    call(1, {owner, 0x80000002, 0x896184, 0xf003f});
    if (!call(2, {owner})) return close(1);
    call(3, {owner, 0x89617c, root, 0x103}, locals.root);
    std::size_t length = 0;
    while (length < locals.root.size() && locals.root[length] != std::byte{}) ++length;
    if (!length || length == locals.root.size())
        throw std::invalid_argument("installation root must be nonempty and terminated");
    if (locals.root[length - 1] == std::byte{'\\'}) locals.root[length - 1] = std::byte{};
    if (!call(4, {owner, 0x80000002, 0x896154, 0xf003f})) return close(1);
    if (!call(5, {owner, 0x89614c, level})) return close(1);

    state.flags[0] = locals.level;
    state.flags[1] = locals.level == 2 ? 1u : 0u;
    state.flags[2] = locals.level == 0 ? 1u : 0u;
    if (!state.flags[1]) {
        call(7, {candidate, 0x8885b8, 0x895050}, locals.candidate);
        call(7, {cdroot, 0x896148}, locals.cdroot);
        bool found = false;
        state.flags[3] = 0;
        const auto old_mode = call(11, {0x8001});
        for (std::uint32_t drive = 0; drive < 26; ++drive) {
            locals.candidate[0] = std::byte('a' + drive);
            if (call(8, {drive})) {
                ++state.flags[3];
                const auto file = call(9, {candidate, 0x88b104});
                if (file) {
                    call(10, {file});
                    locals.cdroot[0] = locals.candidate[0];
                    found = true;
                }
            }
        }
        call(11, {old_mode});
        if (!found) return close(2);
    }

    for (std::size_t i = 0; i < rows.size(); ++i) {
        const auto identity = 0xa52d48u + static_cast<std::uint32_t>(i * 260);
        auto destination = state.paths.subspan(i * 260, 260);
        call(7, {identity, 0x896140, root, rows[i].identity}, destination);
        const auto type = rows[i].type;
        const bool use_cd = (type == 1 && std::bit_cast<std::int32_t>(locals.level) < 1) ||
                            (type == 2 && locals.level != 2) || type == 3;
        if (use_cd) {
            // The stock table has no type-3 row when level==2. That combination
            // reads uninitialized original stack bytes and is outside this model.
            if (locals.level == 2)
                throw std::invalid_argument("CD-root path unavailable for level2/type3");
            call(7, {identity, 0x886b1c, cdroot, rows[i].identity}, destination);
        }
    }
    return close(0);
}
}
