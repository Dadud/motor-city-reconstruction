#include "mco/rolling_resistance.hpp"

#include <cmath>
#include <limits>
#include <stdexcept>

namespace {
void check(bool condition, const char* message) {
    if (!condition) throw std::runtime_error(message);
}
template<class F> void invalid(F function) {
    bool rejected = false;
    try { function(); } catch (const std::invalid_argument&) { rejected = true; }
    check(rejected, "invalid resistance input accepted");
}
}
int main() {
    std::array<mco::ResistanceWheel, 4> wheels{};
    for (auto& wheel : wheels) wheel = {0, 0, 2000, 2, 2, true, 100};
    auto run = [&](const auto& input, double speed = 20, bool disabled = false,
                   bool mode = false, bool alternate = false) {
        return mco::rolling_resistance(input, speed, 1.2, 0.8, 0.3, -0.1, 0,
                                      disabled, mode, alternate);
    };
    const auto forward = run(wheels);
    check(forward.wheels[0].longitudinal_force < 100 && forward.last_contribution < 0,
          "forward resistance direction failed");
    for (const auto result : {run(wheels, 1.9999), run(wheels, 20, true), run(wheels, 20, false, true)}) {
        check(result.last_contribution == 0, "gated return failed");
        for (const auto& wheel : result.wheels)
            check(wheel.longitudinal_force == 100, "gated force changed");
    }
    check(run(wheels, 2).last_contribution < 0, "exact speed gate rejected");
    auto reverse = wheels;
    for (auto& wheel : reverse) wheel.rolling_speed = -2;
    check(run(reverse).last_contribution == -forward.last_contribution, "rolling direction sign failed");
    auto boundary = wheels;
    boundary[0].rolling_speed = 0.5;
    boundary[1].contact = false;
    boundary[2].normal_load = 0;
    boundary[3].normal_load = 0;
    const auto preserved = run(boundary);
    for (const auto& wheel : preserved.wheels)
        check(wheel.longitudinal_force == 100, "application gate changed force");
    check(preserved.last_contribution == 0, "return summed earlier wheels");
    auto absent = wheels;
    absent[3].contact = false;
    check(run(absent).last_contribution == forward.last_contribution &&
          run(absent).wheels[3].longitudinal_force == 100, "last unapplied contribution lost");
    auto slipped = wheels;
    for (auto& wheel : slipped) wheel.slip_angle = 0.1;
    check(run(slipped, 20, false, false, true).last_contribution < run(slipped).last_contribution,
          "alternate amplification failed");
    auto bad = wheels; bad[0].speed_scale = 0;
    invalid([&] { run(bad, 0); }); // Validation precedes the speed gate.
    bad = wheels; bad[0].normal_load = -1;
    invalid([&] { run(bad); });
    bad = wheels; bad[2].slip_angle = std::numeric_limits<double>::infinity();
    invalid([&] { run(bad); });
    invalid([&] { run(wheels, 1e100); });
}
