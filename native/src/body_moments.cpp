#include "mco/body_moments.hpp"
#include <cmath>
#include <limits>
#include <stdexcept>
namespace mco {
namespace {
double stored(double v) {
    if (!std::isfinite(v) || std::abs(v)>std::numeric_limits<float>::max())
        throw std::invalid_argument("finite float32 body moment value required");
    return static_cast<float>(v);
}
}
std::array<double,3> accumulate_body_moments(BodyMomentState s) {
    for (double* v : {&s.speed,&s.front_lever,&s.rear_lever,&s.front_track,&s.rear_track,
         &s.height_parameter,&s.mass_parameter,&s.inverse_pitch,&s.inverse_yaw,&s.inverse_roll,
         &s.pitch_multiplier,&s.front_vertical,&s.rear_vertical,&s.yaw_contribution}) *v=stored(*v);
    for (auto& w : s.wheels)
        for (double* v : {&w.lateral_force,&w.longitudinal_force,&w.secondary_response,&w.support_correction}) *v=stored(*v);
    const double k=stored(.15915494), front=s.front_lever, rear=s.rear_lever;
    const double ft=stored(s.front_track*.5),rt=stored(s.rear_track*.5);
    const double height=stored(s.height_parameter*stored(.9090909));
    const auto& w=s.wheels;
    const double lateral=((w[0].lateral_force+w[1].lateral_force)*front
        -(w[3].lateral_force+w[2].lateral_force)*rear)*k;
    const double extra=front*.25*s.yaw_contribution*k;
    const double torque=s.alternate_mode ? 0 : ((w[0].longitudinal_force-w[1].longitudinal_force)*ft
        +(w[3].longitudinal_force-w[2].longitudinal_force)*rt)*k;
    double yaw=stored((torque+extra+lateral)*s.inverse_yaw);
    double secondary=0;
    for (const auto& wheel : w) secondary+=wheel.secondary_response;
    yaw=stored(secondary*s.inverse_yaw*k+yaw);
    if (std::abs(s.speed)<.5) return {0,yaw,0};
    double pitch=0,roll=0;
    for (int i : {0,1,3,2}) {
        const double x=i==0 ? -ft : i==1 ? ft : i==3 ? -rt : rt;
        const double z=i<2 ? front : -rear;
        const double vertical=i<2 ? s.front_vertical : s.rear_vertical;
        pitch=stored(pitch+stored(vertical*z-w[i].longitudinal_force*height));
        roll=stored(roll+stored(w[i].lateral_force*height-vertical*x));
    }
    pitch=stored(pitch*s.inverse_pitch*s.pitch_multiplier*k);
    roll=stored(roll*s.inverse_roll*k);
    const double quarter=stored(s.mass_parameter*.25);
    for (int i=0;i<4;++i) {
        if (w[i].contact && w[i].support_correction!=0) {
            const double contribution=stored(quarter*w[i].support_correction);
            pitch=stored(pitch+contribution*(i<2 ? front : rear)*s.inverse_pitch*k);
            roll=stored(roll+contribution*(i<2 ? ft : rt)*s.inverse_roll*k);
        }
    }
    return {pitch,yaw,roll};
}
}
