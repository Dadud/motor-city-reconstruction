#pragma once
#include <cstdint>
#include <functional>
#include <string>
#include <vector>
namespace mco {
struct DrivetrainLinksState {
 std::uint32_t engine_flags=1,vehicle_flags=0;
 std::int32_t rpm=3000;
 int mode=0;
 bool alternate_enabled=false,bypass=false;
 float speed=20,normalized_rpm=.4f,engagement=.5f,auxiliary_temperature=125,auxiliary_capacity=10,
 condition=.9f,main_temperature=100,loss=0,drive_scale=.1f,primary_drive=.01f,alternate_drive=.02f,
 third_temperature=100,gate_one=.1f,gate_two=.1f,threshold_observation=0,request=0,rate_two=0,
 rate_one=0,shielding_one=.2f,shielding_two=.2f;
};
struct DrivetrainLinksConfig {
 std::int32_t material_index=2,durability_index=1,loss_index=1;
 bool third_enabled=true;
 std::vector<float> mode_coefficients{.8f,1.f,.7f};
 float alternate_threshold=1,thermal_gain=.01f,cooling_capacity=10,main_loss_coefficient=.01f,
 transfer_coefficient=.1f,reference=100,upgrade_enabled=0,upgrade_cooling=0,upgrade_capacity=0;
};
struct LinkCall {std::string stage;int code;std::vector<float> values;bool operator==(const LinkCall &)const=default;};
using LinkEffectExecutor=std::function<void(const LinkCall &,DrivetrainLinksState &)>;
struct DrivetrainLinksOutput {DrivetrainLinksState state;std::vector<LinkCall> calls;};
DrivetrainLinksOutput update_gear_link(DrivetrainLinksState,const DrivetrainLinksConfig &,const LinkEffectExecutor &);
DrivetrainLinksOutput update_drivetrain_loads(DrivetrainLinksState,const DrivetrainLinksConfig &,const LinkEffectExecutor &);
}
