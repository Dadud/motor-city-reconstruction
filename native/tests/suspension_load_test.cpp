#include "mco/suspension_load_correction.hpp"
#include <limits>
#include <stdexcept>
namespace {
void check(bool condition, const char* message) { if (!condition) throw std::runtime_error(message); }
}
int main() {
    mco::SuspensionLoadInput s{{1200,1600,900,1100}, {true,true,true,true}, 0, true,
        20, 0.08, -0.06, 1450, 100, 0.45, 0.55, 1.2, 1.5, 2.7, 1.7, -2.3, 500, 0, false};
    const std::array<float,4> initial{1200,1600,900,1100};
    auto t = s; t.enabled = false;
    check(mco::correct_suspension_load(t) == initial, "disabled state changed loads");
    t = s; t.attitude = 0.25001;
    check(mco::correct_suspension_load(t) == initial, "attitude gate changed loads");
    t = s; t.speed = 6; t.support = {false,false,false,false};
    const auto low = mco::correct_suspension_load(t);
    check(low[0] == 1200 && low[1] == 1600 && low[2] > 900 && low[3] < 1100,
          "low-speed torque correction incorrectly gated on support");
    t.disable_torque = true;
    check(mco::correct_suspension_load(t) == initial, "disable torque failed");
    t.disable_torque = false; t.component_mode = 1;
    check(mco::correct_suspension_load(t) == initial, "component-mode torque gate failed");
    t = s; t.disable_torque = true; t.support = {false,false,false,false};
    check(mco::correct_suspension_load(t) == initial, "high-speed correction altered unsupported wheels");
    t = s; t.loads = {1,2,3,4}; t.bank_angle = -0.1; t.pitch_angle = 0.1; t.torque = 2000;
    for (const auto load : mco::correct_suspension_load(t)) check(load >= 0, "negative load escaped clamp");
    t = s; t.rear_track = 0;
    bool rejected = false;
    try { mco::correct_suspension_load(t); } catch (const std::invalid_argument&) { rejected = true; }
    check(rejected, "invalid rear track accepted");
}
