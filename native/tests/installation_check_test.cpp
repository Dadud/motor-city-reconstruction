#include "mco/installation_check.hpp"
#include <array>
#include <stdexcept>
static std::uint32_t fail(mco::InstallationState&, const mco::InstallationCall&, void*) { return 0; }
int main() {
    std::array<std::byte, 8320> paths{};
    mco::InstallationState state{paths, {}};
    bool missing = false, too_many = false;
    try { mco::installation_check(state, {}, {}); }
    catch (const std::invalid_argument&) { missing = true; }
    std::array<mco::InstallationRow, 32> rows{};
    try { mco::installation_check(state, rows, {fail, nullptr}); }
    catch (const std::out_of_range&) { too_many = true; }
    return missing && too_many ? 0 : 1;
}
