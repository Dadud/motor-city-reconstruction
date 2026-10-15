#pragma once
#include "mco/driving_engine_rpm.hpp"
#include <cstdint>
#include <functional>
#include <optional>
#include <string>
#include <vector>
namespace mco {
struct EngineTorqueState {
 DrivingEngineRPM rpm_state{};
 std::uint32_t engine_flags=1;
 bool bypass=false;
 std::int32_t counter=1000;
 bool alternate_enabled=false;
 std::int32_t boost_flag=0;
 float curve_torque=100,effective_torque=100,power=0,engagement=.5f,brake_control=0,
 condition_accumulator=0,condition_gate=0,damage_d3c=0,damage_d40=0,damage_d44=0,
 damage_d48=0,damage_d4c=0,loss=0,auxiliary_temperature=100,boost_observation=0,
 effect_motion=0,drag_factor=0,drag_speed=0,drag=0,coupling_resistance=0,environment_field=0;
 bool environment_override=false,environment_selector_enabled=false;
 std::int32_t environment_selector=0;
};
struct EngineTorqueConfig {
 std::vector<float> torque_curve;
 bool third_enabled=false;
 std::int32_t loss_index=1,material_index=1;
 float upgrade_enabled=0;
 std::int32_t upgrade_index=0,gain_mode=0;
 float boost_threshold=1,boost_available=1,exhaust_tag=0,compression=9;
 std::int32_t durability_index=3,limit_a=1,limit_b=2,overspeed_base=10000,overspeed_extra=0,overload_index=100;
 float overload_coefficient=10,torque_capacity=1000;
};
struct TorqueCall {
 std::string stage;
 std::optional<std::int32_t> code;
 std::vector<double> values;
 bool operator==(const TorqueCall&)const=default;
};
// value is the child result; boost additionally writes a binary32 increment.
struct TorqueStageResult {double value=0;float boost_increment=0;};
using TorqueStageExecutor=std::function<TorqueStageResult(const TorqueCall&,EngineTorqueState&)>;
struct EngineTorqueOutput {EngineTorqueState state;std::vector<TorqueCall>calls;};
// Power, environment, inline curve and RPM are recovered. Other children must be supplied.
EngineTorqueOutput update_engine_torque(EngineTorqueState,const EngineTorqueConfig&,const TorqueStageExecutor&);
}
