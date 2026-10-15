#include "mco/vehicle_preparation.hpp"
#include <algorithm>
#include <cmath>
#include <stdexcept>
namespace mco {
namespace {
double f(double x) {const double result=static_cast<float>(x);if(!std::isfinite(result))throw std::invalid_argument("finite float32 required");return result;}
constexpr double tau=6.2831854820251465,inv_tau=.15915493667125702;
double clamp(double x,double low,double high) {return std::max(low,std::min(high,x));}
std::array<double,9> multiply(const std::array<double,9>& a,const std::array<double,9>& b) {
    constexpr int order[9][3]={{1,2,0},{2,1,0},{2,1,0},{2,1,0},{0,1,2},{2,1,0},{2,1,0},{2,1,0},{2,0,1}};
    std::array<double,9> out{};
    for(int i=0;i<9;++i) {double total=0;for(int k:order[i])total+=a[(i/3)*3+k]*b[k*3+i%3];out[i]=f(total);}
    return out;
}
}
PreparationState prepare_vehicle(PreparationState s) {
    for(double* p:{&s.local_vertical_acceleration,&s.front_observation,&s.rear_observation,&s.front_factor,&s.rear_factor,
        &s.pitch_extent,&s.roll_extent,&s.pitch_limit,&s.roll_limit,&s.orientation_scale,&s.pitch_reference,&s.roll_reference,
        &s.minimum_pitch,&s.maximum_pitch,&s.maximum_roll,&s.pitch_offset,&s.pitch,&s.roll,&s.extent,
        &s.damping,&s.pitch_target,&s.roll_target}) *p=f(*p);
    for(auto& x:s.source_vector)x=f(x);for(auto& x:s.source_matrix)x=f(x);for(auto& x:s.motion_matrix)x=f(x);
    for(auto& x:s.auxiliary)x=f(x);for(auto& x:s.angle_delta)x=f(x);for(auto& x:s.to_world)x=f(x);for(auto& x:s.to_local)x=f(x);
    if(s.support_count<0 || s.support_count>4 || std::min({s.minimum_pitch,s.maximum_pitch,s.maximum_roll,s.pitch_limit,s.roll_limit})<0)
        throw std::invalid_argument("invalid support count or limits");
    if(s.pitch_reference!=s.source_matrix[1] || s.orientation_scale!=s.source_matrix[4] || s.roll_reference!=s.source_matrix[7])
        throw std::invalid_argument("orientation observations disagree with matrix");
    s.damping=1;
    if(s.local_vertical_acceleration>0)s.damping=f(1-(1-s.rear_observation*.5)*s.rear_factor);
    else if(s.local_vertical_acceleration<0)s.damping=f(1-(1-s.front_observation*.5)*s.front_factor);
    s.damping=clamp(s.damping,0,1);
    if(s.support_count<2) {
        const double maximum=std::max(s.pitch_limit,s.roll_limit),scale=clamp(s.orientation_scale,0,1);
        std::array<double,3> transformed{};
        for(int i=0;i<3;++i)transformed[i]=f((s.source_vector[0]*s.motion_matrix[i]+s.source_vector[1]*s.motion_matrix[i+3])+s.source_vector[2]*s.motion_matrix[i+6]);
        const double pr=f(std::atan2(s.pitch_reference,std::abs(s.orientation_scale))*inv_tau*scale);
        const double rr=f(std::atan2(s.roll_reference,std::abs(s.orientation_scale))*inv_tau*scale);
        s.pitch_target=f(rr-std::atan2(transformed[2],transformed[1])*inv_tau+s.pitch_offset);
        s.roll_target=f(pr-std::atan2(transformed[0],transformed[1])*inv_tau);
        const double dp=clamp(rr,-s.minimum_pitch,s.maximum_pitch),dr=clamp(pr,-s.maximum_roll,s.maximum_roll);
        const double pe=std::abs(f(std::sin(s.roll*tau)*s.pitch_extent));
        const double re=std::abs(f(std::sin(s.pitch*tau)*s.roll_extent));
        const double de=std::max(std::max(pe,re),f(scale*maximum*f(.66)));
        s.angle_delta={f((dp-s.pitch)*.015625),f((dr-s.roll)*.015625),f((de-s.extent)*.015625)};
        s.pitch=clamp(f(s.pitch+(dp-s.pitch)*.015625),-s.minimum_pitch,s.maximum_pitch);
        s.roll=clamp(f(s.roll+s.angle_delta[1]),-s.maximum_roll,s.maximum_roll);
        s.extent=clamp(f(s.extent+s.angle_delta[2]),0,maximum);s.auxiliary.fill(0);
    } else s.angle_delta.fill(0);
    const double ps=f(std::sin(s.pitch*tau)),pc=f(std::cos(s.pitch*tau));
    const double rs=f(std::sin(s.roll*tau)),rc=f(std::cos(s.roll*tau));
    s.to_world=multiply(multiply({1,0,0,0,pc,ps,0,-ps,pc},{rc,rs,0,-rs,rc,0,0,0,1}),s.source_matrix);
    for(int i=0;i<3;++i)for(int j=0;j<3;++j)s.to_local[i*3+j]=s.to_world[j*3+i];
    return s;
}
SupportState update_support_disturbance(SupportState s) {
    s.phase=f(s.phase);s.local_longitudinal_speed=f(s.local_longitudinal_speed);
    for(int i=0;i<4;++i) {
        auto& w=s.wheels[i];w.bound_parameter=f(w.bound_parameter);w.amplitude=f(w.amplitude);w.frequency=f(w.frequency);w.displacement=f(w.displacement);
        if(w.bound_parameter<0)throw std::invalid_argument("nonnegative support bound required");
        if(!w.contact) {w.displacement=0;w.correction=0;continue;}
        const double cycle=f(s.phase*w.frequency);
        // Nearest-even FISTP emulation, independent from ambient host rounding mode.
        const double floor=std::floor(cycle),fraction=cycle-floor;
        const double rounded=fraction<.5?floor:fraction>.5?floor+1:std::fmod(floor,2)==0?floor:floor+1;
        if(rounded<-2147483648. || rounded>2147483647.)throw std::invalid_argument("support phase outside signed conversion range");
        const auto index=(static_cast<std::uint32_t>(static_cast<std::int32_t>(rounded))+static_cast<unsigned>(i>1))&255;
        const double noise=f(s.noise[index]*.0078125-1);
        const double speed=f(s.local_longitudinal_speed*w.frequency*f(6.2831855));
        const double disturbance=noise*w.amplitude*std::sin(cycle*tau),velocity=disturbance*speed;
        const double displacement=f(velocity*.03125+w.displacement),bound=std::min(f(w.bound_parameter*.25),std::abs(f(disturbance)));
        w.displacement=clamp(displacement,-bound,bound);w.correction=f(f(velocity)*speed);
    }
    return s;
}
}
