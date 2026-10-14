#include "mco/brake_thermal.hpp"
#include <cassert>
#include <stdexcept>

int main() {
    assert(mco::brake_countdown(.25,2,1)==26);
    assert(mco::brake_fade(200,200)==1);
    assert(mco::brake_fade(225,200)==.75);
    assert(mco::brake_fade(250,200)==.5);
    assert(mco::brake_ambient(true,2)==-15);
    mco::BrakeThermalState s{};
    s.front={900,.25,1.1,450,8,400,2,1,2};
    s.rear={900,.2,.9,430,6,350,3,0,0};
    s.wheels={mco::BrakeWorkWheel{100,.25,1},mco::BrakeWorkWheel{100,.25,1},
        mco::BrakeWorkWheel{100,.25,1},mco::BrakeWorkWheel{100,.25,1}};
    s.mass_parameter=1500;s.speed=10;s.service_control=1;
    auto r=mco::update_brake_thermal(s);
    assert(r.front.temperature==800 && r.rear.temperature==700);
    assert(r.front.countdown==1 && r.rear.countdown==0);
    assert(r.wheels[0].brake_force==0);
    s.front.thermal_mass=0;
    try {mco::update_brake_thermal(s);return 1;}catch(const std::invalid_argument&){}
}
