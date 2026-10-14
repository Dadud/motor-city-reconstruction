#include "mco/body_moments.hpp"
#include "mco/wheel_force_orientation.hpp"
#include <stdexcept>
#include <cmath>
void check(bool ok) {if (!ok) throw std::runtime_error("body moment behavior mismatch");}
int main() {
    mco::BodyMomentState s{};
    s.speed=20;s.front_lever=1.2;s.rear_lever=1.5;s.front_track=1.6;s.rear_track=1.7;
    s.inverse_pitch=.003;s.inverse_yaw=.002;s.inverse_roll=.004;s.pitch_multiplier=.8;s.mass_parameter=1300;
    check(mco::accumulate_body_moments(s)==std::array<double,3>{0,0,0});
    s.wheels[0].lateral_force=100;
    check(mco::accumulate_body_moments(s)[1]>0);
    s.wheels[0].lateral_force=0;s.wheels[0].longitudinal_force=100;
    check(mco::accumulate_body_moments(s)[1]>0);
    s.alternate_mode=true;check(mco::accumulate_body_moments(s)[1]==0);
    s.wheels[0].longitudinal_force=0;s.wheels[0].support_correction=.2;s.wheels[0].contact=true;
    check(mco::accumulate_body_moments(s)[0]>0);
    s.speed=.49999;check(mco::accumulate_body_moments(s)[0]==0);
    std::array<mco::ForceOrientationWheel,4> wheels{};
    for(auto& w:wheels) w={.25,0,100,200};
    const auto out=mco::orient_wheel_forces(wheels,0,0);
    check(std::abs(out[0].lateral_force+100)<.0001 && std::abs(out[0].longitudinal_force+100)<.0001);
}
