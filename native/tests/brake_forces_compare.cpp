#include "mco/brake_forces.hpp"
#include <iostream>
#include <iomanip>
int main() {
    std::cout<<std::setprecision(17);
    for(std::size_t count=0;count<100000;++count) {
        mco::BrakeForceState s{};auto& t=s.thermal;int parking,environment,auxiliary;
        if(!(std::cin>>t.service_control)) return std::cin.eof()?0:2;
        if(!(std::cin>>parking>>t.speed>>t.mass_parameter>>t.elevation_parameter>>environment>>t.environment_code)) return 2;
        t.parking_control=parking!=0;t.environment_flag=environment!=0;
        for(auto* a:{&t.front,&t.rear})
            if(!(std::cin>>a->temperature>>a->diameter>>a->cooling_coefficient>>a->heat_capacity_factor
                >>a->thermal_mass>>a->temperature_limit>>a->material_code>>a->construction_code>>a->countdown)) return 2;
        for(auto& w:t.wheels) if(!(std::cin>>w.brake_force>>w.spin_scale>>w.spin_value)) return 2;
        if(!(std::cin>>s.front_quality>>s.rear_quality>>s.front_gate>>s.rear_gate>>s.rear_distribution
            >>s.drive_factor>>s.pitch_angle>>s.vehicle_code>>auxiliary>>s.parking_ramp)) return 2;
        s.auxiliary_flag=auxiliary!=0;
        for(auto& w:s.wheels) if(!(std::cin>>w.spin_value>>w.spin_adjustment>>w.spin_scale>>w.projected_speed
            >>w.normal_load>>w.longitudinal_force>>w.control_angle>>w.component_code>>w.inertia_addend>>w.inertia_multiplier)) return 2;
        const auto r=mco::update_brake_forces(s);const auto& out=r.state;
        std::cout<<out.thermal.front.temperature<<' '<<out.thermal.rear.temperature<<' '
            <<out.thermal.front.countdown<<' '<<out.thermal.rear.countdown<<' '
            <<out.thermal.kinetic_value<<' '<<out.thermal.elevation_value<<' '<<out.parking_ramp;
        for(int i=0;i<4;++i) std::cout<<' '<<out.wheels[i].spin_adjustment<<' '<<out.wheels[i].longitudinal_force
            <<' '<<out.thermal.wheels[i].brake_force;
        std::cout<<' '<<r.wear_events.size();
        for(const auto& [slot,amount]:r.wear_events) std::cout<<' '<<slot<<' '<<amount;
        std::cout<<' '<<r.controller_events.size();
        for(int event:r.controller_events) std::cout<<' '<<event;
        std::cout<<' '<<r.events.size();
        for(const auto& event:r.events) std::cout<<' '<<event.kind<<' '<<event.slot<<' '<<event.value;
        std::cout<<'\n';
    }
    return 2;
}
