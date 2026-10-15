#include "mco/drivetrain_stages.hpp"
#include <limits>
#include <stdexcept>

namespace {
void check(bool ok,const char* message) {if(!ok) throw std::runtime_error(message);}
template<class F> void invalid(F action) {
    bool rejected=false;
    try {action();} catch(const std::invalid_argument&) {rejected=true;}
    check(rejected,"invalid drivetrain input accepted");
}
}
int main() {
    mco::DriveConfig c{{2.5,0,2.2},{.8,1,.7},{.2,.4,.8},{.002,.003,.004},
        3.5,500,.9,16,7000,false};
    mco::DriveState s;
    auto released=s;released.override_byte=1;
    check(mco::update_clutch(released,c).engagement<s.engagement,"clutch release failed");
    auto airborne=s;airborne.driven_speed=123;
    for(auto& w:airborne.wheels) w.contact=false;
    check(mco::prepare_drive(airborne,c).driven_speed==123,"airborne driven speed reset");
    s.alternate_speed=2.5;
    check(mco::accumulate_drive_request(s,c).request==0,"request threshold failed");
    s.alternate_speed=3;
    check(mco::accumulate_drive_request(s,c).request>0,"request accumulation failed");
    const mco::DriveExecutor no_effect=[](const auto&,auto&)->std::optional<bool>{return true;};
    s.hold_ticks=std::numeric_limits<std::int32_t>::min();
    check(mco::distribute_drive(s,c,no_effect).hold_ticks==std::numeric_limits<std::int32_t>::max(),
        "signed hold wrap failed");
    s.hold_ticks=0;s.effective_torque=1000;s.clutch_gain=1;
    int calls=0;
    const auto effect=[&](const mco::DriveCall& call,mco::DriveState& state)->std::optional<bool>{
        if(calls++==0) {check(call.stage=="damage" && call.code==13,"damage call order");state.damage_one=.75;}
        else check(call.stage=="effect" && call.code==25,"component call order");
        return std::nullopt;
    };
    check(mco::distribute_drive(s,c,effect).output_torque<mco::distribute_drive(s,c,no_effect).output_torque,
        "damage mutation not consumed");
    check(calls==2,"drive effect count");
    s.speed=0;s.raw_throttle=0;
    auto stopped=mco::distribute_drive(s,c,no_effect);
    calls=0;
    stopped=mco::apply_drive_forces(stopped,c,[&](const auto&,auto&)->std::optional<bool>{++calls;return true;});
    check(calls==0 && stopped.wheels[0].spin==0,"stop flag gate failed");
    s.engine_flags=1;s.longitudinal_speed=0;s.wheel_acceleration=0;
    for(auto& w:s.wheels) {w.torque=100;w.longitudinal_force=0;}
    const auto forward=mco::apply_drive_forces(s,c,no_effect);
    s.gear=0;
    const auto reverse=mco::apply_drive_forces(s,c,no_effect);
    check(reverse.wheels[0].longitudinal_force==-forward.wheels[0].longitudinal_force,
        "reverse force sign failed");
    for(auto flag:{2u,0x10u,0x200u}) check(mco::vehicle_control_mode(flag,false,0)==1,"mode flag failed");
    check(mco::vehicle_control_mode(4,true,3)==3 && mco::vehicle_control_mode(4,false,3)==0,
        "local vehicle policy failed");
    invalid([&]{mco::apply_drive_forces(s,c,{});});
    invalid([&]{mco::apply_drive_forces(s,c,[](const auto&,auto&)->std::optional<bool>{return std::nullopt;});});
    auto bad=c;bad.gear_ratios.clear();invalid([&]{mco::update_clutch(s,bad);});
    bad=c;bad.clutch_steps=0;invalid([&]{mco::update_clutch(s,bad);});
    s.engagement=std::numeric_limits<double>::quiet_NaN();invalid([&]{mco::update_clutch(s,c);});
}
