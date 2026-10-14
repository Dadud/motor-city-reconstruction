#include "mco/load_transfer.hpp"

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
    check(rejected, "invalid load-transfer input accepted");
}
}
int main() {
    mco::LoadTransferInput state{{2000, 2100, 1500, 1600}, 0, 0, 0, 20,
                               1450, 2.7, 1.6, 1.7, 0.55, 0.12, 0.18};
    const std::array<float, 4> initial{2000, 2100, 1500, 1600};
    check(mco::transfer_load(state) == initial, "inactive correction changed loads");
    auto gated = state; gated.attitude = 0.25001; gated.longitudinal_acceleration = 20;
    check(mco::transfer_load(gated) == initial, "attitude gate changed loads");
    auto threshold = state; threshold.longitudinal_acceleration = static_cast<float>(0.1962);
    threshold.lateral_acceleration = -static_cast<float>(0.1962);
    check(mco::transfer_load(threshold) == initial, "exact acceleration threshold changed loads");
    auto forward = state; forward.longitudinal_acceleration = 5;
    const auto shifted = mco::transfer_load(forward);
    check(shifted[0] < 2000 && shifted[1] < 2100 && shifted[2] > 1500 && shifted[3] > 1600,
          "longitudinal processing order failed");
    auto lateral = state; lateral.lateral_acceleration = 5;
    const auto side = mco::transfer_load(lateral);
    check(side[0] > 2000 && side[1] < 2100 && side[2] > 1500 && side[3] < 1600,
          "lateral processing order failed");
    lateral.speed = 6;
    check(mco::transfer_load(lateral) == initial, "exact lateral speed gate failed");
    auto both = state; both.loads = {1, 100, 1, 100};
    both.longitudinal_acceleration = 20; both.lateral_acceleration = 15;
    const auto clamped = mco::transfer_load(both);
    check(clamped[0] == 0 && clamped[1] == 0 && clamped[2] > clamped[3] && clamped[3] >= 0,
          "longitudinal clamping did not precede lateral axle sums");
    auto bad = state; bad.front_track = 0;
    invalid([&] { mco::transfer_load(bad); });
    bad = state; bad.loads[2] = -1;
    invalid([&] { mco::transfer_load(bad); });
    bad = state; bad.rear_offset = std::numeric_limits<double>::quiet_NaN();
    invalid([&] { mco::transfer_load(bad); });
    bad = state; bad.mass = 1e100;
    invalid([&] { mco::transfer_load(bad); });
}
