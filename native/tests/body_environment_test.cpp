#include "mco/body_environment.hpp"
#include "mco/air_density.hpp"
#undef NDEBUG
#include <cassert>

int main() {
    mco::BodyResistanceState body{};
    body.speed=30.;body.longitudinal_speed=30.;body.drag_parameter=.4;body.area_parameter=2.2;
    body.front_lever=1.2;body.rear_lever=1.5;body.height_parameter=.7;body.length_parameter=2.;
    body.wheel_loads={10000.,10000.,10000.,10000.};body.contacts={true,true,true,true};
    body.density=-100.;body.wind_lateral=100.;body.wind_longitudinal=100.;body.drafting_factor=-100.;
    mco::DraftVehicle own{1,{0.,0.,0.},{1.,0.,0.,0.,1.,0.,0.,0.,1.},{1.,.8,2.}};
    auto peer=own;peer.identifier=2;peer.position[2]=4.;
    mco::BodyEnvironment env{0.,false,true,1,
        {0,0,{0.,0.,1.},{1.,0.,0.,0.,1.,0.,0.,0.,1.},true},1,{own,peer}};
    const auto first=mco::calculate_body_environment(body,env);
    assert(first.density==mco::calculate_air_density(0.,false,true,1));
    assert(!first.wind.present && first.drafting.selected_vehicle==2 && first.drafting.inside_wake);
    assert(first.body.longitudinal_drag<0. && first.body.wheel_loads[0]<body.wheel_loads[0]);
    assert(first.drafting.vehicles[1].wake_origin!=peer.wake_origin);
    // Advance both mutable outputs, then compare the next step with explicit producer handoffs.
    body.wheel_loads=first.body.wheel_loads;env.vehicles=first.drafting.vehicles;
    const auto second=mco::calculate_body_environment(body,env);
    body.density=second.density;body.wind_lateral=second.wind.body_velocity[0];
    body.wind_longitudinal=second.wind.body_velocity[2];body.drafting_factor=second.drafting.factor;
    const auto direct=mco::calculate_body_resistance(body);
    assert(second.body.wheel_loads==direct.wheel_loads);
    assert(second.body.longitudinal_drag==direct.longitudinal_drag);
    assert(second.body.wheel_loads[0]<first.body.wheel_loads[0]);
    assert(second.body.wheel_loads[2]>first.body.wheel_loads[2]);
    assert(second.drafting.vehicles[1].wake_origin==first.drafting.vehicles[1].wake_origin);
}
