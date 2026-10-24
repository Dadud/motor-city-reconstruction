#include "mco/normal_load.hpp"
#include <algorithm>
#include <cmath>
#include <limits>
#include <stdexcept>
namespace mco {
namespace {
float stored(double value) {
    if (!std::isfinite(value) || std::abs(value) > std::numeric_limits<float>::max())
        throw std::invalid_argument("finite float32 normal-load value required");
    return static_cast<float>(value);
}
}
std::array<float, 4> normal_load(const NormalLoadInput& state) {
    std::array<double, 4> scales{};
    for (std::size_t i = 0; i < 4; ++i) scales[i] = stored(state.wheel_scales[i]);
    const double pitch = stored(state.pitch), bank = stored(state.bank), mass = stored(state.mass);
    const double wheelbase = stored(state.wheelbase), ft = stored(state.front_track), rt = stored(state.rear_track);
    double height = stored(state.height_parameter);
    const double front = stored(state.front_lever), rear = stored(state.rear_lever);
    const double speed = stored(state.speed), curvature = stored(state.curvature_scale);
    const double vertical = stored(state.vertical_correction);
    if (mass <= 0 || wheelbase <= 0 || ft <= 0 || rt <= 0 || curvature == 0)
        throw std::invalid_argument("positive mass/dimensions and nonzero signed curvature scale required");
    const auto& support = state.support;
    const auto count = std::count(support.begin(), support.end(), true);
    if (count < 2 || std::abs(pitch) > 0.25) return {};
    height = stored(height * static_cast<double>(stored(0.9090909)));
    const double factor = stored(mass * 0.5 / wheelbase);
    const double front_load = stored(factor * rear), rear_load = stored(factor * front);
    const double turn = stored(6.2831855);
    const double cosine = stored(std::cos(pitch * turn)), sine = std::sin(pitch * turn);
    const double front_pitch = stored(((cosine - 1.0) * rear - sine * height) * factor);
    const double rear_pitch = stored(((cosine - 1.0) * front + sine * height) * factor);
    const double bank_angle = stored(bank * static_cast<double>(stored(3.1415927)));
    const double front_bank = stored((front_load + front_load) * 0.5 * (height / ft) * bank_angle);
    const double rear_bank = stored((rear_load + rear_load) * 0.5 * (height / rt) * bank_angle);
    std::array<float, 4> loads{static_cast<float>(front_load), static_cast<float>(front_load),
                             static_cast<float>(rear_load), static_cast<float>(rear_load)};
    if (count == 2 && !support[0] && !support[1]) {
        loads = {0, 0, stored(rear_bank * 0.5 + front_load + rear_load),
                 stored(-rear_bank * 0.5 + front_load + rear_load)};
    } else if (count == 2 && !support[2] && !support[3]) {
        loads = {stored(front_bank * 0.5 + rear_load + front_load),
                 stored(-front_bank * 0.5 + rear_load + front_load), 0, 0};
    } else {
        for (std::size_t start : {std::size_t{0}, std::size_t{2}}) {
            const double correction = start == 0 ? front_pitch : rear_pitch;
            const double banking = start == 0 ? front_bank : rear_bank;
            if (support[start] && support[start+1]) {
                loads[start] = stored(banking * 0.5 + correction + loads[start]);
                loads[start+1] = stored(-banking * 0.5 + correction + loads[start+1]);
            } else {
                const std::size_t active = support[start] ? start : start+1;
                const std::size_t other = support[start] ? start+1 : start;
                loads[active] = stored(correction + correction + loads[other] + loads[active]);
                loads[other] = 0;
            }
        }
    }
    const double banking = std::min(6.0, std::abs(static_cast<double>(stored(
        std::sin(bank * turn) * speed * speed / curvature))));
    for (std::size_t i = 0; i < 4; ++i)
        loads[i] = std::max(0.0f, stored(((scales[i] - vertical) + banking) * loads[i]));
    return loads;
}
std::array<std::array<float, 3>, 4> normal_force_vectors(const NormalLoadInput& state) {
    const auto loads = normal_load(state);
    std::array<std::array<float, 3>, 4> forces{};
    for (std::size_t i = 0; i < forces.size(); ++i) forces[i][1] = loads[i];
    return forces;
}
}
