#include "mco/drivetrain_stages.hpp"
#include <algorithm>
#include <cmath>
#include <limits>
#include <stdexcept>

namespace mco {
namespace {
double stored(double v) {
    if (!std::isfinite(v) || std::abs(v)>std::numeric_limits<float>::max())
        throw std::invalid_argument("finite float32 drive observation required");
    return static_cast<float>(v);
}
void normalize(DriveState& s) {
    for (double* v : {&s.throttle,&s.engagement,&s.clutch_gain,&s.angular_speed,
        &s.coupling_resistance,&s.effective_torque,&s.transmitted_torque,
        &s.reference_rotation,&s.output_torque,&s.driven_speed,&s.previous_rotation,
        &s.drag_speed,&s.prior_output_rotation,&s.final_drive_acceleration,
        &s.gearbox_drag,&s.output_rotation,&s.wheel_acceleration,&s.accumulated_drag,
        &s.inertia_sum,&s.longitudinal_speed,&s.acceleration,&s.speed,&s.alternate_speed,
        &s.damage_one,&s.damage_two,&s.request}) *v=stored(*v);
    for (auto& w:s.wheels)
        for (double* v : {&w.spin,&w.adjustment,&w.radius,&w.inertia,&w.conversion,
            &w.distribution,&w.torque,&w.normal_load,&w.longitudinal_force}) *v=stored(*v);
}
void begin(DriveState& s,DriveConfig& c) {
    normalize(s);
    for (auto* table : {&c.gear_ratios,&c.gear_losses,&c.inertia_factors,&c.speed_factors}) {
        if (table->empty() || table->size()>8 || s.gear<0 ||
            static_cast<std::size_t>(s.gear)>=table->size())
            throw std::invalid_argument("explicit table entry required for RPM gear index");
        for (auto& v:*table) v=stored(v);
    }
    for (double* v : {&c.final_drive,&c.torque_capacity,&c.efficiency,&c.option_one,
        &c.option_two,&c.increment_gain,&c.secondary_gain}) *v=stored(*v);
    if (c.final_drive==0 || c.torque_capacity==0 || c.clutch_steps<=0)
        throw std::invalid_argument("nonzero drive denominators and positive clutch steps required");
}
}
std::uint32_t vehicle_control_mode(std::uint32_t flags,bool local,std::uint32_t setting) {
    return (flags&0x212) ? 1 : local ? setting : 0;
}
DriveState update_clutch(DriveState s,DriveConfig c) {
    begin(s,c);
    const bool release=c.third_enabled ? s.throttle<stored(.01) && s.driven_speed<25 : s.override_byte==1;
    double step=stored(1./c.clutch_steps);
    if (release) s.engagement=stored(s.engagement-step);
    else if (s.engagement<1) {
        if (s.bypass || s.damage_one<.5) {
            if (!c.third_enabled && s.coupling_resistance>200) step*=stored(.3);
        } else step=stored(step*stored(1.8));
        s.engagement=stored(s.engagement+step);
    }
    s.engagement=std::clamp(s.engagement,0.,1.);
    if (s.engagement==0 || s.engagement==1) s.clutch_gain=s.engagement;
    else {
        const double remaining=stored(1.-s.engagement);
        s.clutch_gain=stored(1.-std::pow(remaining,4));
        if (c.third_enabled && s.angular_speed>0) {
            const double fraction=std::min(1.,stored(s.reference_rotation/s.angular_speed));
            const double scale=std::clamp(stored((1.-fraction)*1.5+1.),1.,2.5);
            s.clutch_gain=stored(scale*s.clutch_gain);
        }
    }
    return s;
}
DriveState prepare_drive(DriveState s,DriveConfig c) {
    begin(s,c);
    const double denominator=(s.wheels[3].radius+s.wheels[2].radius)*.5;
    if (denominator==0) throw std::invalid_argument("nonzero mean rear radius required");
    const double acceleration=std::clamp(stored(s.acceleration/denominator),-100.,100.);
    const double ratio=c.gear_ratios[s.gear],final=c.final_drive;
    if (s.gear!=1 && ratio==0) throw std::invalid_argument("nonzero active gear ratio required");
    s.wheel_acceleration=acceleration;
    s.output_rotation=stored(s.prior_output_rotation/final);
    s.final_drive_acceleration=stored(acceleration*final);
    s.prior_output_rotation=s.gear==1 ? s.driven_speed : stored(s.previous_rotation/ratio);
    s.drag_speed=s.engagement<=0 ? stored((s.rpm*stored(.10471976)-s.previous_rotation)*32.) :
                                  stored(acceleration*final*ratio);
    s.previous_rotation=stored(s.rpm*stored(.10471976));
    double maximum=0;
    for (const auto& w:s.wheels) if (w.driven && w.contact) {
        maximum=std::max(maximum,std::abs(stored(w.spin*final)));
        s.driven_speed=maximum;
    }
    s.reference_rotation=s.gear==1 ?
        stored((s.angular_speed-s.reference_rotation)*s.engagement+s.reference_rotation) :
        stored(ratio*s.driven_speed);
    // FST retains this unrounded sum for the continuing x87 product.
    const double summed=c.inertia_factors[s.gear]+s.inertia_sum;
    s.coupling_resistance=stored((s.angular_speed-s.reference_rotation)*summed*s.engagement*s.engagement*32.);
    return s;
}
DriveState accumulate_drive_request(DriveState s,DriveConfig c) {
    begin(s,c);
    if (s.alternate_speed<=2.5) return s;
    const auto mode=s.component_mode;
    double value=stored(mode==5 ? 1.0416667e-5 : (mode==2 || mode==3 || mode==4 || mode==7) ? 5.2083333e-6 : 2.6041666e-6);
    if (c.option_one>0 && c.option_two>0) {
        const double factor=c.option_kind==1 ? .05 : c.option_kind==2 ? .025 : c.option_kind==3 ? .0125 : .1;
        value=stored(value*stored(factor));
    }
    if (c.increment_gain>0) value=stored((c.increment_gain*stored(.02)+1.)*value);
    if (c.secondary_gain!=0) {
        value=stored((c.secondary_gain+1.)*value);
        const double factor=c.secondary_kind==1 ? .5 : c.secondary_kind==2 ? .25 : c.secondary_kind==3 ? .125 : .75;
        value=stored(value*stored(factor));
    }
    s.request=std::clamp(stored(s.request+value),0.,1.);
    return s;
}
DriveState distribute_drive(DriveState s,DriveConfig c,const DriveExecutor& execute) {
    if (!execute) throw std::invalid_argument("drive effects required");
    begin(s,c);
    s.transmitted_torque=(s.effective_torque>0 || s.engagement>=1) ?
        stored(s.clutch_gain*s.effective_torque) : s.driven_speed>=25 ? 0 : 10;
    if (s.gear==1) s.output_torque=0;
    else if (s.hold_ticks!=0) {
        s.output_torque=0;
        s.hold_ticks=s.hold_ticks==std::numeric_limits<std::int32_t>::min() ?
            std::numeric_limits<std::int32_t>::max() : s.hold_ticks-1;
    } else {
        s.gearbox_drag=stored(std::abs(s.drag_speed)*c.inertia_factors[s.gear]);
        s.output_torque=stored((s.transmitted_torque-s.gearbox_drag)*c.gear_losses[s.gear]*c.gear_ratios[s.gear]);
    }
    const double ratio=stored(s.output_torque/c.torque_capacity);
    if (ratio>1 && !s.bypass) {
        execute({"damage",13,{stored(std::pow(s.output_torque-c.torque_capacity,2)/c.torque_capacity)}},s);
        execute({"effect",25,{stored(std::abs(s.speed)*std::min(4.,ratio)*.03125)}},s);
    }
    if (!s.bypass) for (const auto* damage : {&s.damage_one,&s.damage_two}) {
        if (*damage>=.25) {
            const double delta=stored(*damage-.25);
            s.output_torque=stored((1.-delta*delta)*s.output_torque);
        }
    }
    double efficiency=c.efficiency;
    if (!c.third_enabled && vehicle_control_mode(s.vehicle_flags,s.local_player,s.mode_setting)) {
        const double reduced=stored(efficiency-stored(.025));
        if (reduced>=efficiency) throw std::invalid_argument("original drive-efficiency diagnostic boundary unsupported");
        efficiency=reduced;
    }
    for (auto& w:s.wheels) {
        s.accumulated_drag=stored(std::abs(s.final_drive_acceleration)*s.inertia_sum);
        w.torque=stored((s.output_torque-s.accumulated_drag)*w.distribution*c.final_drive*efficiency);
    }
    // The final original stop test overwrites the earlier auxiliary-byte test.
    s.engine_flags=std::abs(s.speed)<1 && s.raw_throttle==0 ? s.engine_flags|0x20 : s.engine_flags&0xffffffdf;
    normalize(s);
    return s;
}
DriveState apply_drive_forces(DriveState s,DriveConfig c,const DriveExecutor& execute) {
    if (!execute) throw std::invalid_argument("vehicle gate observation required");
    begin(s,c);
    for (auto& w:s.wheels) {
        if (!w.driven) {
            if (s.acceleration>0 && w.contact && w.normal_load!=0)
                w.longitudinal_force=stored(w.longitudinal_force-std::abs(s.wheel_acceleration)*w.inertia);
            continue;
        }
        bool enabled=false;
        if (!(s.engine_flags&0x20)) {
            const auto answer=execute({"vehicle_gate",std::nullopt,{}},s);
            if (!answer) throw std::invalid_argument("boolean vehicle gate required");
            enabled=*answer;
        }
        double force=0;
        if (enabled) {
            s.accumulated_drag=stored(w.inertia*s.wheel_acceleration+s.accumulated_drag);
            if (w.radius==0) throw std::invalid_argument("nonzero driven wheel radius required");
            force=stored((w.torque-std::abs(s.wheel_acceleration)*w.inertia)/w.radius);
            if (s.gear==0) force=-force;
        } else {w.adjustment=0;w.spin=0;}
        // A supplied service can mutate shared state. Reject invalid indices
        // before reading a table even when the entry-state index was valid.
        if (s.gear<0 || static_cast<std::size_t>(s.gear)>=c.gear_ratios.size() ||
            static_cast<std::size_t>(s.gear)>=c.speed_factors.size())
            throw std::invalid_argument("service changed gear outside observed tables");
        if (w.contact && w.normal_load!=0) {
            const double factor=c.speed_factors[s.gear];
            if (s.gear==0 && s.rpm*factor*stored(1.05)<std::abs(s.longitudinal_speed)) force=0;
            else if (s.gear>1 && s.rpm*factor*stored(1.05)<s.longitudinal_speed) force=0;
            if (c.maximum_rpm*factor<std::abs(s.longitudinal_speed)) force=0;
            w.longitudinal_force=stored(w.longitudinal_force+force);
        }
        double denominator=c.gear_ratios[s.gear]*c.final_drive;
        if (denominator==0) denominator=1;
        w.adjustment=stored(w.conversion*w.longitudinal_force*w.radius/denominator);
    }
    normalize(s);
    return s;
}
}
