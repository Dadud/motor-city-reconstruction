#include "mco/tire_update.hpp"
#include "mco/steering_response.hpp"
#include <algorithm>
#include <cmath>
#include <limits>
#include <stdexcept>
namespace mco {
namespace {
float stored(double value) {
    if (!std::isfinite(value) || std::abs(value) > std::numeric_limits<float>::max())
        throw std::invalid_argument("finite float32 tire update value required");
    return static_cast<float>(value);
}
void normalize(TireCurves& c) {
    for (auto& v : c.primary) v = stored(v);
    for (auto& v : c.secondary) v = stored(v);
    c.angle_coefficient = stored(c.angle_coefficient);
}
}
TireUpdateState update_tires(TireUpdateState s) {
    normalize(s.front_curves); normalize(s.rear_curves);
    for (double* v : {&s.speed, &s.mass_parameter, &s.front_lever, &s.rear_lever,
                     &s.front_track, &s.wheelbase, &s.maximum_steering, &s.longitudinal_velocity,
                     &s.lateral_velocity, &s.lateral_acceleration, &s.yaw_rate, &s.body_slip}) *v = stored(*v);
    if (s.front_track <= 0 || s.wheelbase <= 0 || s.mass_parameter <= 0)
        throw std::invalid_argument("positive dimensions and mass parameter required");
    for (auto& w : s.wheels) {
        for (double* v : {&w.steering_angle, &w.slip_angle, &w.secondary_angle, &w.projected_speed,
                         &w.normal_load, &w.surface_multiplier, &w.lateral_force,
                         &w.longitudinal_force, &w.secondary_response}) *v = stored(*v);
        if (w.normal_load < 0) throw std::invalid_argument("nonnegative normal load required");
    }
    const double steering = stored(s.maximum_steering * steering_response(s.raw_control, s.longitudinal_velocity));
    const double turn = stored(6.2831855), inverse_turn = 0.15915493667125702;
    std::array<double,4> angles{steering,steering,0,0};
    if (std::abs(steering) >= static_cast<double>(stored(0.001))) {
        const double radians = std::abs(steering) * turn;
        const double tangent = static_cast<double>(stored(std::sin(radians))) / stored(std::cos(radians));
        const double denominator = stored(s.wheelbase / tangent - s.front_track);
        const double paired = stored(std::atan2(s.wheelbase, denominator) * inverse_turn);
        if (steering <= 0) angles[0] = -paired; else angles[1] = paired;
    }
    if (s.rear_steering) {
        const double rear = std::abs(s.speed) <= static_cast<double>(stored(8.9406))
            ? std::clamp(static_cast<double>(stored(steering * static_cast<double>(stored(-0.2)))),
                         static_cast<double>(stored(-0.055555556)), static_cast<double>(stored(0.055555556)))
            : std::clamp(static_cast<double>(stored(steering * 0.5)),
                         static_cast<double>(stored(-0.027777778)), static_cast<double>(stored(0.027777778)));
        angles[2] = angles[3] = rear;
    }
    for (auto& angle : angles) angle = std::clamp(angle,-1.0,1.0);
    if (std::abs(s.speed) <= 0.25) {
        s.yaw_rate = stored(s.yaw_rate * static_cast<double>(stored(0.95)));
        s.lateral_acceleration = stored(s.lateral_velocity * -32.0);
        s.lateral_velocity = 0;
    }
    for (std::size_t i = 0; i < 4; ++i) {
        auto& w = s.wheels[i];
        double slip = 0;
        if (s.mode_observations[i]) {
            const double lever = i < 2 ? s.front_lever : s.rear_lever;
            const double numerator = stored(lever * s.yaw_rate * turn);
            const double angle = std::atan2(numerator, std::abs(s.longitudinal_velocity)) * inverse_turn;
            slip = stored(i < 2 ? angle + s.body_slip : s.body_slip - angle);
        }
        slip = stored(w.projected_speed >= 0 ? slip - angles[i] : slip + angles[i]);
        double force = 0, secondary = 0;
        if (w.normal_load <= 0 || !w.contact) w.longitudinal_force = 0;
        else if (std::abs(s.speed) >= 0.25) {
            if (std::abs(s.speed) < 6) {
                const double blend = stored((std::abs(s.speed) - 0.25) * static_cast<double>(stored(0.17391305)));
                slip = stored(blend * slip + (1.0-blend) * std::sin(slip*turn) * static_cast<double>(stored(0.008333334)));
                slip = std::clamp(slip,-1.0,1.0);
            }
            const auto& c = i < 2 ? s.front_curves : s.rear_curves;
            const WheelCurveInput observation{slip,w.secondary_angle,w.normal_load,w.surface_multiplier};
            force = wheel_response(c.primary,c.angle_coefficient,observation,false,s.alternate_load);
            secondary = wheel_response(c.secondary,c.angle_coefficient,observation,true);
            if (std::abs(s.lateral_velocity) < 0.25)
                force = stored(force - s.lateral_velocity * static_cast<double>(stored(1.4)) * std::sqrt(w.normal_load*5700.0));
        } else force = stored(s.mass_parameter * 0.25 * s.lateral_acceleration);
        if (std::abs(force) <= 10 && std::abs(s.speed) > 6) force = 0;
        w.steering_angle = angles[i]; w.slip_angle = slip;
        w.lateral_force = force; w.secondary_response = secondary;
    }
    return s;
}
}
