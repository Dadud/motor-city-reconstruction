#include "mco/tire_update.hpp"
#include <stdexcept>
namespace {
void check(bool condition, const char* message) { if (!condition) throw std::runtime_error(message); }
mco::TireUpdateState state() {
    mco::TireUpdateState s{};
    s.mass_parameter = 1450; s.front_lever = 1.2; s.rear_lever = 1.5;
    s.front_track = 1.6; s.wheelbase = 2.7; s.maximum_steering = 0.05;
    s.speed = s.longitudinal_velocity = 20; s.raw_control = 64;
    for (auto& w : s.wheels) w = {0,0,0,20,2000,true,1,111,222,333};
    for (std::size_t i = 0; i < 26; ++i) {
        s.front_curves.primary[i] = s.rear_curves.primary[i] = i*40;
        s.front_curves.secondary[i] = s.rear_curves.secondary[i] = i*20;
    }
    return s;
}
}
int main() {
    auto s = state(); const auto moving = mco::update_tires(s);
    check(moving.wheels[0].steering_angle != moving.wheels[1].steering_angle, "paired front steering missing");
    check(moving.wheels[0].longitudinal_force == 222, "supported longitudinal force not preserved");
    s.wheels[0].contact = false; s.wheels[1].normal_load = 0;
    const auto absent = mco::update_tires(s);
    check(absent.wheels[0].lateral_force == 0 && absent.wheels[0].longitudinal_force == 0 &&
          absent.wheels[0].secondary_response == 0 && absent.wheels[1].longitudinal_force == 0,
          "unsupported force clearing failed");
    s = state(); s.speed = 0; s.lateral_velocity = 0.2; s.yaw_rate = 0.3;
    const auto stopped = mco::update_tires(s);
    check(stopped.lateral_velocity == 0 && stopped.lateral_acceleration < 0 && stopped.yaw_rate < 0.3,
          "stationary damping failed");
    check(stopped.wheels[0].lateral_force < 0, "stationary force response missing");
    s = state(); s.rear_steering = true;
    check(mco::update_tires(s).wheels[2].steering_angle > 0, "high speed rear steering missing");
    s.speed = 2;
    check(mco::update_tires(s).wheels[2].steering_angle < 0, "low speed rear countersteering missing");
    s.front_track = 0; bool rejected = false;
    try { mco::update_tires(s); } catch (const std::invalid_argument&) { rejected = true; }
    check(rejected, "invalid axle dimensions accepted");
}
