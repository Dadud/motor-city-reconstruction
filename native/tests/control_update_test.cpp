#include "mco/control_update.hpp"
#include <stdexcept>
void check(bool ok) {if(!ok)throw std::runtime_error("control update mismatch");}
bool supplied(const mco::ControlCall& c,mco::ControlState&) {return c.stage==mco::ControlStage::vehicle_gate;}
int main() {
    mco::ControlState s;s.target_throttle=131;s.throttle=100;
    check(mco::update_controls(s,supplied).state.throttle==104);
    s.target_throttle=132;check(mco::update_controls(s,supplied).state.throttle==108);
    s.target_throttle=68;check(mco::update_controls(s,supplied).state.throttle==84);
    s.new_steering_mode=false;s.target_steering=-127;s.steering=90;
    check(mco::update_controls(s,supplied).state.steering==0);
    s.new_steering_mode=true;s.target_steering=0;s.steering=30;s.slow_steering=1;
    check(mco::update_controls(s,supplied).state.steering==30);
    s.target_steering=-80;check(mco::update_controls(s,supplied).state.steering==28);
    s.slow_steering=0;s.target_steering=100;s.steering=0;s.steering_attack_rate=2.5;
    check(mco::update_controls(s,supplied).state.steering==2);
    s.steering_attack_rate=3.5;check(mco::update_controls(s,supplied).state.steering==4);
    s.emergency=true;s.brake_output=.125;
    auto out=mco::update_controls(s,[](const mco::ControlCall& c,mco::ControlState& state) {
        if(c.stage==mco::ControlStage::trace_controls) {check(state.brake_output==.125);state.brake_output=999;}
        return c.stage==mco::ControlStage::override_query;
    });
    check(out.state.steering==0 && out.state.brake==192 && out.state.throttle==0 && out.state.brake_output!=999);
    bool rejected=false;try {mco::update_controls(s,{});}catch(const std::invalid_argument&) {rejected=true;}check(rejected);
}
