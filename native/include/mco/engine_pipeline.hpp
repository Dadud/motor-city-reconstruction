#pragma once
#include "mco/engine_torque_update.hpp"
#include "mco/engine_update.hpp"
#include "mco/drivetrain_links.hpp"
#include <array>
namespace mco {
struct EnginePipelineState : EngineTorqueState {
 std::uint32_t vehicle_flags=4;
 int selector_index=0;
 std::array<std::int32_t,8>activation_delays{32,16,64,48,12,50,40,24};
 float override_value=0;
 bool control_gate=false;
 float motion_metric=0;
 // +0xac8; EngineTorqueState::engagement is separately stored at +0xb2c.
 float thermal_engagement=.5f;
 int thermal_mode=0;
 float auxiliary_capacity=10,condition=.9f,main_temperature=100,drive_scale=.1f,
 primary_drive=.01f,alternate_drive=.02f,third_temperature=100,gate_one=.1f,
 gate_two=.1f,request=0,rate_two=0,rate_one=0,shielding_one=.2f,shielding_two=.2f;
};
struct EnginePipelineConfig {EngineTorqueConfig torque;DrivetrainLinksConfig links;};
struct PipelineCall {
 std::string domain,stage;
 std::optional<std::int32_t>code;
 std::vector<double>values;
 bool operator==(const PipelineCall&)const=default;
};
using PipelineStageExecutor=std::function<TorqueStageResult(const PipelineCall&,EnginePipelineState&)>;
struct EnginePipelineOutput {EnginePipelineState state;std::vector<PipelineCall>calls;};
// Shared-owner dispatcher with actual recovered torque and condition consumers.
// Every other child remains mandatory explicit supplied behavior.
EnginePipelineOutput update_engine_pipeline(EnginePipelineState,const EnginePipelineConfig&,const PipelineStageExecutor&);
}
