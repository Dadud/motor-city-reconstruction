#include "mco/owned_descriptions.hpp"
#include <algorithm>
#include <stdexcept>

namespace {
void check(bool ok) { if (!ok) throw std::runtime_error("description mismatch"); }
void put(mco::OwnedPartSlot& s, std::size_t p, std::uint32_t value) {
    for (unsigned i = 0; i < 4; ++i) s[p + i] = static_cast<std::uint8_t>(value >> (8 * i));
}
void text(mco::OwnedPartSlot& s, std::size_t p, const std::string& value) {
    std::copy(value.begin(), value.end(), s.begin() + p); s[p + value.size()] = 0;
}
std::string description(const mco::OwnedPartSlot& s) { return reinterpret_cast<const char*>(s.data() + 0x20); }
template<class F> void reject(F function) {
    bool failed = false; try { function(); } catch (const std::invalid_argument&) { failed = true; }
    check(failed);
}
}
int main() {
    mco::OwnedPartSlot marker{}, root{}, child{}, leaf{};
    put(root, 0, 101); put(root, 0x1e3, 1);
    put(child, 0, 1001); put(child, 0x1e3, 1); put(child, 0x61c, 10);
    text(child, 0x287, "Model"); text(child, 0x180, "Category");
    std::vector<mco::OwnedPartSlot> cache{marker}, slots{root, child};
    const auto original = slots;
    auto result = mco::apply_owned_descriptions(slots, cache, {{10, "Front"}});
    check(description(result[0]) == "Model Front Category" && slots == original);
    reject([&] { mco::apply_owned_descriptions(slots, cache, {}); });
    put(child, 0x61c, 0); text(child, 0x287, std::string(63, 'M')); text(child, 0x180, std::string(53, 'C'));
    slots = {root, child, child, child};
    result = mco::apply_owned_descriptions(slots, cache, {});
    check(description(result[0]).size() == 235); // Third complete line exceeds 351.
    text(child, 0x180, std::string(52, 'C')); slots = {root, child, child, child};
    result = mco::apply_owned_descriptions(slots, cache, {});
    check(description(result[0]).size() == 350);
    put(leaf, 0, 55); put(leaf, 0x1e3, 1); slots = {leaf};
    reject([&] { mco::apply_owned_descriptions(slots, cache, {}); });
    bool called = false;
    result = mco::apply_owned_descriptions(slots, cache, {}, [&](const auto& input) {
        called = true; return input;
    });
    check(called && result == slots);
    put(leaf, 0x1e3, 0); text(leaf, 0x20, "Old"); slots = {leaf};
    result = mco::apply_owned_descriptions(slots, cache, {}); check(result == slots);
    mco::OwnedPartSlot templ{}; put(templ, 0, 55); cache.push_back(templ);
    result = mco::apply_owned_descriptions(slots, cache, {}); check(description(result[0]) == " ");
    reject([&] { mco::apply_owned_descriptions({}, cache, {{0, "invalid"}}); });
}
