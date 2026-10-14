#include "mco/wheel_spin.hpp"
#include <algorithm>
#include <cmath>
#include <limits>
#include <stdexcept>
namespace mco {
namespace {
double stored(double v) {
    if(!std::isfinite(v) || std::abs(v)>std::numeric_limits<float>::max()) throw std::invalid_argument("finite float32 spin value required");
    return static_cast<float>(v);
}
}
WheelSpinOutput integrate_wheel_spin(WheelSpinState s) {
    const double multiplier=stored(s.gear_multiplier),front=stored(s.front_scale),rear=stored(s.rear_scale);
    const double fc=stored(s.front_compliance),rc=stored(s.rear_compliance);
    const double fa=stored(s.front_secondary_angle),ra=stored(s.rear_secondary_angle);
    const double fq=stored(s.front_quality),rq=stored(s.rear_quality),body=stored(s.body_secondary_angle);
    const double fl=stored(s.front_lever),rl=stored(s.rear_lever),yaw=stored(s.yaw_rate),lateral=stored(s.lateral_velocity);
    if(front<=0 || rear<=0 || fc<0 || rc<0) throw std::invalid_argument("positive scales and nonnegative compliance required");
    WheelSpinOutput out{};
    for(int i=0;i<4;++i) {
        auto& w=s.wheels[i];
        for(double* v:{&w.spin_value,&w.spin_adjustment,&w.spin_scale,&w.projected_speed,&w.normal_load,
            &w.kinetic_parameter,&w.ratio_denominator,&w.phase}) *v=stored(*v);
        if(w.spin_scale<=0 || w.ratio_denominator==0 || w.normal_load<0) throw std::invalid_argument("positive scale/nonzero ratio/nonnegative load required");
        double spin=stored(w.spin_value+w.spin_adjustment*.03125);
        if(w.correction_enabled && !s.override_control && s.direction_mode!=1) {
            const double limit=stored(std::max(std::abs(w.projected_speed/w.spin_scale),std::abs(stored(s.rpm)*multiplier/w.spin_scale)));
            spin=std::clamp(spin,-limit,limit);
        }
        const double deformation=std::clamp(stored(w.normal_load*stored(.001)*stored(.005)),0.0,stored(.05));
        const double squared=stored(spin*spin);
        w.kinetic_value=stored(squared*w.kinetic_parameter*.5);
        const double base=i<2 ? front : rear,compliance=i<2 ? fc : rc;
        const double delta=std::clamp(stored(deformation-squared*base*stored(.101936795)*compliance*stored(.001)),stored(-.01),compliance);
        const double scale=stored(base-delta);
        w.phase=stored(spin*stored(.004973592)+w.phase);
        const double forward=stored(scale*spin),ratio=stored(scale*spin/w.ratio_denominator);
        w.local_lateral=i<2 ? stored(fl*yaw+lateral) : stored(lateral-rl*yaw);
        w.local_vertical=0;w.local_longitudinal=forward;
        if(ratio>1) out.wear_events.emplace_back(i,stored(ratio*stored(5.2083337e-6)));
        w.slip_ratio=w.projected_speed==0 ? 0 : stored((scale*spin-w.projected_speed)/w.projected_speed);
        w.slip_ratio=std::clamp(w.slip_ratio,-1.0,100000.0);
        double secondary=stored((i<2 ? fa : ra)*stored(.0055555557));
        if(w.contact) secondary=stored(std::abs(body*stored(i<2 ? 1.05 : 1.02))+secondary);
        const double quality=i<2 ? fq : rq;
        if(quality>.75) secondary=stored((.75-quality)*stored(.07)+secondary);
        w.secondary_angle=std::clamp(secondary,stored(-.083333336),stored(.083333336));
        w.spin_value=spin;w.spin_scale=scale;
    }
    out.state=s;return out;
}
}
