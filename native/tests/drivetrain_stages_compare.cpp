#include "mco/drivetrain_stages.hpp"
#include <iomanip>
#include <iostream>
#include <sstream>
#include <stdexcept>
#include <type_traits>

namespace {
template<class Visitor> void visit(mco::DriveState& s,Visitor use) {
    for(auto& w:s.wheels) use(w.spin,w.adjustment,w.radius,w.inertia,w.conversion,
        w.distribution,w.torque,w.normal_load,w.longitudinal_force,w.driven,w.contact);
    use(s.engine_flags,s.vehicle_flags,s.rpm,s.gear,s.hold_ticks,s.override_byte,
        s.raw_throttle,s.auxiliary_byte,s.component_mode,s.mode_setting,s.local_player,
        s.bypass,s.throttle,s.engagement,s.clutch_gain,s.angular_speed,s.coupling_resistance,
        s.effective_torque,s.transmitted_torque,s.reference_rotation,s.output_torque,
        s.driven_speed,s.previous_rotation,s.drag_speed,s.prior_output_rotation,
        s.final_drive_acceleration,s.gearbox_drag,s.output_rotation,s.wheel_acceleration,
        s.accumulated_drag,s.inertia_sum,s.longitudinal_speed,s.acceleration,s.speed,
        s.alternate_speed,s.damage_one,s.damage_two,s.request);
}
template<class T> void read(std::istream& in,T& value) {
    if constexpr(std::is_same_v<T,std::uint8_t>) {
        unsigned temporary;
        if(!(in>>temporary) || temporary>255) throw std::runtime_error("invalid drive byte");
        value=static_cast<std::uint8_t>(temporary);
    } else if(!(in>>value)) throw std::runtime_error("invalid drive fixture");
}
}
int main() {
    std::cout<<std::setprecision(17);
    std::string line;
    while(std::getline(std::cin,line)) {
        std::istringstream in(line);
        std::string stage;bool gate=false,mutation=false;
        read(in,stage);read(in,gate);read(in,mutation);
        mco::DriveState s;
        visit(s,[&](auto&... items){(read(in,items),...);});
        mco::DriveConfig c;
        for(auto* table:{&c.gear_ratios,&c.gear_losses,&c.inertia_factors,&c.speed_factors}) {
            std::size_t count;read(in,count);
            if(count==0 || count>8) throw std::runtime_error("invalid gear table length");
            table->resize(count);for(auto& value:*table) read(in,value);
        }
        read(in,c.final_drive);read(in,c.torque_capacity);read(in,c.efficiency);
        read(in,c.clutch_steps);read(in,c.maximum_rpm);read(in,c.third_enabled);
        read(in,c.option_one);read(in,c.option_two);read(in,c.option_kind);
        read(in,c.increment_gain);read(in,c.secondary_gain);read(in,c.secondary_kind);
        in>>std::ws;if(!in.eof()) throw std::runtime_error("trailing drive fixture fields");
        std::vector<mco::DriveCall> calls;
        const auto execute=[&](const mco::DriveCall& call,mco::DriveState& current)->std::optional<bool>{
            calls.push_back(call);
            if(mutation && call.stage=="damage") current.damage_one=.75;
            return call.stage=="vehicle_gate" ? std::optional<bool>(gate) : std::nullopt;
        };
        if(stage=="clutch") s=mco::update_clutch(s,c);
        else if(stage=="prepare") s=mco::prepare_drive(s,c);
        else if(stage=="request") s=mco::accumulate_drive_request(s,c);
        else if(stage=="distribute") s=mco::distribute_drive(s,c,execute);
        else if(stage=="apply") s=mco::apply_drive_forces(s,c,execute);
        else throw std::runtime_error("unknown drivetrain stage");
        visit(s,[](const auto&... items){((std::cout<<+items<<' '),...);});
        std::cout<<calls.size();
        for(const auto& call:calls) {
            std::cout<<' '<<call.stage<<' '<<call.code.value_or(-1)<<' '<<call.values.size();
            for(double value:call.values) std::cout<<' '<<value;
        }
        std::cout<<'\n';
    }
}
