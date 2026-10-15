#include "mco/brake_forces.hpp"
#include <stdexcept>
void check(bool ok) {if(!ok) throw std::runtime_error("brake force behavior mismatch");}
int main() {
    mco::BrakeForceState s{};
    s.thermal.front={100,.25,1,450,8,400,0,0,0};s.thermal.rear=s.thermal.front;
    s.thermal.speed=20;s.thermal.mass_parameter=1300;s.thermal.service_control=1;
    for(auto& w:s.wheels) w={3,0,.3,20,4000,0,0,0,1,.2};
    const auto active=mco::update_brake_forces(s);
    check(active.state.wheels[0].longitudinal_force<0 && active.state.wheels[0].spin_adjustment<0);
    s.front_gate=1;s.wheels[1].control_angle=-.4;
    const auto gated=mco::update_brake_forces(s);
    check(gated.state.wheels[0].spin_adjustment<0 && gated.state.wheels[1].spin_adjustment==0);
    s.front_gate=0;s.thermal.service_control=0;s.thermal.parking_control=true;s.parking_ramp=60;
    const auto parking=mco::update_brake_forces(s);
    check(parking.state.parking_ramp==64 && parking.state.wheels[2].longitudinal_force<0);
    s.thermal.parking_control=false;
    check(mco::update_brake_forces(s).state.wheels[0].spin_adjustment==0);
    s.thermal.service_control=1;s.thermal.front.temperature=900;
    s.thermal.front.material_code=2;
    const auto ordered=mco::update_brake_forces(s);
    check(ordered.events.size()>=4);
    check(ordered.events[0].kind==0 && ordered.events[0].slot==0);
    check(ordered.events[1].kind==1 && ordered.events[1].slot==0);
    check(ordered.events[2].kind==0 && ordered.events[2].slot==1);
    check(ordered.events[3].kind==1 && ordered.events[3].slot==1);
}
