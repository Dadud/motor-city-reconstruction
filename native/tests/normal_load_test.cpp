#include "mco/normal_load.hpp"
#include <limits>
#include <stdexcept>
namespace {
void check(bool condition, const char* message) {
    if (!condition) throw std::runtime_error(message);
}
template<class F> void invalid(F f) {
    bool rejected = false;
    try { f(); } catch (const std::invalid_argument&) { rejected = true; }
    check(rejected, "invalid normal-load state accepted");
}
}
int main() {
    mco::NormalLoadInput s{{true, true, true, true}, 0, 0, 1450, 2.7, 1.6, 1.7,
                          0.55, 1.2, 1.5, 15, 40, 0, {9.8, 10, 9.5, 9.9}};
    const auto all = mco::normal_load(s);
    check(all[0] > 0 && all[1] > 0 && all[2] > 0 && all[3] > 0, "all-wheel resting load failed");
    for (unsigned mask = 0; mask < 16; ++mask) {
        auto t = s; unsigned count = 0;
        for (std::size_t i = 0; i < 4; ++i) { t.support[i] = (mask & (1u << i)) != 0; count += t.support[i]; }
        const auto loads = mco::normal_load(t);
        for (std::size_t i = 0; i < 4; ++i) {
            check(loads[i] >= 0, "negative supported load");
            if (count < 2 || !t.support[i]) check(loads[i] == 0, "unsupported wheel acquired load");
        }
    }
    auto t = s; t.pitch = 0.25001;
    check(mco::normal_load(t) == std::array<float, 4>{}, "pitch gate failed");
    t = s; t.vertical_correction = 12;
    check(mco::normal_load(t) == std::array<float, 4>{}, "negative final-load clamp failed");
    t = s; t.bank = 0.1;
    check(mco::normal_load(t)[0] != all[0], "bank correction missing");
    t = s; t.curvature_scale = 0;
    invalid([&] { mco::normal_load(t); });
    t = s; t.wheel_scales[3] = std::numeric_limits<double>::quiet_NaN();
    invalid([&] { mco::normal_load(t); });
}
