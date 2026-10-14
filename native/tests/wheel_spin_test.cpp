#include "mco/wheel_spin.hpp"
#include <stdexcept>
void check(bool ok){if(!ok) throw std::runtime_error("wheel spin mismatch");}
int main() {
    mco::WheelSpinState s{};s.direction_mode=1;s.front_scale=.3;s.rear_scale=.35;
    s.front_compliance=.02;s.rear_compliance=.03;s.front_lever=1.2;s.rear_lever=1.5;s.yaw_rate=.03;s.lateral_velocity=.2;
    for(auto& w:s.wheels) w={1,32,.3,0,0,1,1,0,true,false};
    const auto out=mco::integrate_wheel_spin(s);
    check(out.state.wheels[0].spin_value==2 && out.state.wheels[0].slip_ratio==0);
    check(out.state.wheels[0].local_lateral>out.state.wheels[2].local_lateral);
    s.direction_mode=0;check(mco::integrate_wheel_spin(s).state.wheels[0].spin_value==0);
    s.override_control=true;check(mco::integrate_wheel_spin(s).state.wheels[0].spin_value==2);
}
