#include "mco/suspension_load_correction.hpp"
#include <algorithm>
#include <cmath>
#include <limits>
#include <stdexcept>
namespace mco {
namespace {
float stored(double value) {
    if (!std::isfinite(value) || std::abs(value) > std::numeric_limits<float>::max())
        throw std::invalid_argument("finite float32 suspension-load value required");
    return static_cast<float>(value);
}
}
std::array<float, 4> correct_suspension_load(const SuspensionLoadInput& s) {
    std::array<float, 4> loads{};
    for (std::size_t i = 0; i < 4; ++i) loads[i] = stored(s.loads[i]);
    const double attitude = stored(s.attitude), speed = stored(s.speed);
    const double bank = stored(s.bank_angle), pitch = stored(s.pitch_angle);
    const double mass = stored(s.mass), offset = stored(s.mass_offset);
    const double fw = stored(s.front_weight_parameter), rw = stored(s.rear_weight_parameter);
    const double fl = stored(s.front_lever), rl = stored(s.rear_lever);
    const double wheelbase = stored(s.wheelbase), track = stored(s.rear_track);
    const double gear = stored(s.gear_factor), torque = stored(s.torque);
    if (*std::min_element(loads.begin(), loads.end()) < 0 || wheelbase <= 0 || track <= 0 ||
        mass < offset || mass <= 0 || fw + rw <= 0)
        throw std::invalid_argument("invalid normal load, mass, dimensions or weight parameters");
    if (std::abs(attitude) > 0.25 || !s.enabled) return loads;
    const double total = stored(fw + rw), weight = stored((mass-offset) * static_cast<double>(stored(9.81)));
    const double front_fraction = stored(fw / total), rear_fraction = stored(rw / total);
    const double turn = stored(6.2831855);
    if (std::abs(speed) > 6) {
        const double sine = std::sin(-bank * turn);
        const double front_bank = stored(sine * front_fraction * weight);
        const double rear_bank = sine * rear_fraction * weight;
        const std::array<double, 4> banks{front_bank, -front_bank, rear_bank, -rear_bank};
        for (std::size_t i = 0; i < 4; ++i)
            if (s.support[i]) loads[i] = stored(loads[i] + banks[i]);
        const double pitch_sine = std::sin(-pitch * turn);
        const double front_pitch = stored((front_fraction * weight * fl * 2 / wheelbase) * pitch_sine);
        const double rear_pitch = (rear_fraction * weight * rl * 2 / wheelbase) * pitch_sine;
        const std::array<double, 4> pitches{front_pitch, front_pitch, -rear_pitch, -rear_pitch};
        for (std::size_t i = 0; i < 4; ++i) {
            if (s.support[i]) loads[i] = stored(loads[i] + pitches[i]);
            loads[i] = std::max(0.0f, loads[i]);
        }
    }
    if (s.component_mode == 0 && !s.disable_torque) {
        const double correction = stored(std::abs(gear * torque * rw * 0.5 / (track * total)));
        loads[2] = std::max(0.0f, stored(loads[2] + correction));
        loads[3] = std::max(0.0f, stored(loads[3] - correction));
    }
    return loads;
}
}
