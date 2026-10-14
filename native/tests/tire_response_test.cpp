#include "mco/tire_response.hpp"

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
    check(rejected, "invalid wheel input accepted");
}
}
int main() {
    mco::WheelResponseTable table{};
    for (std::size_t i = 0; i < table.size(); ++i) table[i] = i * 100.0;
    const mco::WheelCurveInput wheel{4.5 / 180.0, 0.0, 4000, 1.0};
    const float primary = mco::wheel_response(table, 0, wheel);
    check(std::abs(primary + 450.0f) < 0.001f, "fractional knot interpolation failed");
    auto reversed = wheel; reversed.slip_angle = -wheel.slip_angle;
    check(mco::wheel_response(table, 0, reversed) == -primary, "primary slip sign failed");
    check(mco::wheel_response(table, 0, wheel, true) == -primary, "secondary sign failed");
    auto saturated = wheel; saturated.slip_angle = 0.3;
    check(mco::wheel_response(table, 0, saturated) == -2500.0f, "table saturation failed");
    auto unloaded = wheel; unloaded.normal_load = 0;
    check(mco::wheel_response(table, 1, unloaded) == 0, "unloaded response failed");
    auto heavy = wheel; heavy.normal_load = 30000;
    check(mco::wheel_response(table, 0, heavy, true) == 2250.0f, "secondary load cap failed");
    check(mco::wheel_response(table, 0, heavy, true, true) ==
          mco::wheel_response(table, 0, heavy, true), "alternate switch affected secondary path");
    auto angle = wheel; angle.slip_angle = 0; angle.secondary_angle = 0.003;
    check(mco::wheel_response(table, 0.021, angle) >
          mco::wheel_response(table, 0.021, angle, true), "secondary angle coefficient failed");
    auto bad = wheel; bad.normal_load = -1;
    invalid([&] { mco::wheel_response(table, 0, bad); });
    bad = wheel; bad.surface_multiplier = std::numeric_limits<double>::infinity();
    invalid([&] { mco::wheel_response(table, 0, bad); });
    bad = wheel; bad.slip_angle = std::numeric_limits<float>::max();
    invalid([&] { mco::wheel_response(table, 0, bad); });
    invalid([&] { mco::wheel_response(table, 1e100, wheel); });
    table[25] = std::numeric_limits<double>::quiet_NaN();
    invalid([&] { mco::wheel_response(table, 0, unloaded); });
}
