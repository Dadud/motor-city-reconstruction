#include "mco/driving_engine_rpm.hpp"
#include <stdexcept>
namespace { void check(bool condition) { if (!condition) throw std::runtime_error("driving RPM check failed"); } }
int main() {
    mco::DrivingEngineRPM s{600,7000,.5f,.4f,2000,true,.7f,100,300,3000,6800,1,175,30};
    auto out = mco::update_driving_engine_rpm(s, 600);
    s.enabled = false;
    const auto off = mco::update_driving_engine_rpm(s, 600);
    check(off.rpm == 0 && off.angular_speed == 0 && off.target_rpm > 2000);
    s.enabled = true; s.longitudinal_speed = 1000;
    const auto neutral = mco::update_driving_engine_rpm(s, 600);
    check(neutral.target_rpm == out.target_rpm && neutral.rpm == out.rpm);
    s.gear_index = 2; s.longitudinal_speed = 30;
    out = mco::update_driving_engine_rpm(s, 600);
    s.longitudinal_speed = -30;
    check(out.target_rpm == mco::update_driving_engine_rpm(s, 600).target_rpm);
}
