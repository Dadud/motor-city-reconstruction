#include "mco/control_update.hpp"
#include <iostream>
#include <iomanip>
int main() {
    std::cout<<std::setprecision(17);
    for(int i=0;i<100000;++i) {
        mco::ControlState s;bool stopped,override,gate;
        if(!(std::cin>>s.target_throttle))return std::cin.eof()?0:2;
        if(!(std::cin>>s.target_brake>>s.target_gear>>s.smooth_throttle>>s.smooth_steering>>s.smooth_brake
            >>s.throttle>>s.brake>>s.output_gear>>s.auxiliary_control>>s.reverse_control>>s.slow_steering>>s.target_steering>>s.steering
            >>s.emergency>>s.steering_output>>s.brake_output>>s.throttle_output>>s.flags>>s.remote_controls>>s.local_player
            >>s.steering_setting>>s.throttle_setting>>s.brake_setting>>s.brake_limit>>s.new_steering_mode>>s.steering_return_rate>>s.steering_attack_rate
            >>s.assisted_gears>>stopped>>override>>gate))return 2;
        auto output=mco::update_controls(s,[&](const mco::ControlCall& c,mco::ControlState& state) {
            switch(c.stage) {
            case mco::ControlStage::remote_controls:state.target_throttle=240;state.target_steering=80;break;
            case mco::ControlStage::manual_gears:case mco::ControlStage::assisted_gears:state.output_gear=3;state.brake=128;break;
            case mco::ControlStage::stopped_query:return stopped;
            case mco::ControlStage::override_query:return override;
            case mco::ControlStage::vehicle_gate:return gate;
            default:break;
            }return false;
        });
        auto& o=output.state;
        std::cout<<o.target_throttle<<' '<<o.target_brake<<' '<<o.target_gear<<' '<<o.smooth_throttle<<' '<<o.smooth_steering<<' '<<o.smooth_brake<<' '
            <<o.throttle<<' '<<o.brake<<' '<<o.output_gear<<' '<<o.auxiliary_control<<' '<<o.reverse_control<<' '<<o.slow_steering<<' '<<o.target_steering<<' '<<o.steering<<' '
            <<o.emergency<<' '<<o.steering_output<<' '<<o.brake_output<<' '<<o.throttle_output<<' '<<o.flags<<' '<<o.remote_controls<<' '<<o.local_player<<' '
            <<o.steering_setting<<' '<<o.throttle_setting<<' '<<o.brake_setting<<' '<<o.brake_limit<<' '<<o.new_steering_mode<<' '
            <<o.steering_return_rate<<' '<<o.steering_attack_rate<<' '<<o.assisted_gears<<' '<<output.calls.size();
        for(const auto& c:output.calls) {std::cout<<' '<<static_cast<int>(c.stage)<<' '<<c.values.size();for(double value:c.values)std::cout<<' '<<value;}
        std::cout<<'\n';
    }return 2;
}
