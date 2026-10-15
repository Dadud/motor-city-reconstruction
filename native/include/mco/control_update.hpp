#pragma once
#include <cstdint>
#include <functional>
#include <vector>
namespace mco {
struct ControlState {
    int target_throttle=0,target_brake=0,target_gear=1;
    bool smooth_throttle=true,smooth_steering=true,smooth_brake=true;
    int throttle=0,brake=0,output_gear=1,auxiliary_control=0,reverse_control=0,slow_steering=0;
    int target_steering=0,steering=0;
    bool emergency=false;
    double steering_output=0,brake_output=0,throttle_output=0;
    std::uint32_t flags=0;
    bool remote_controls=false,local_player=false;
    std::uint32_t steering_setting=128,throttle_setting=128,brake_setting=128;
    int brake_limit=255;
    bool new_steering_mode=true;
    double steering_return_rate=8,steering_attack_rate=8;
    bool assisted_gears=false;
};
enum class ControlStage {remote_controls,assisted_gears,manual_gears,stopped_query,override_query,vehicle_gate,trace_controls};
struct ControlCall {ControlStage stage;std::vector<double> values;};
using ControlExecutor=std::function<bool(const ControlCall&,ControlState&)>;
struct ControlOutput {ControlState state;std::vector<ControlCall> calls;};
ControlOutput update_controls(ControlState state,const ControlExecutor& execute);
}
