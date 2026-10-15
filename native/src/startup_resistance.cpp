#include "mco/startup_resistance.hpp"
#include <cmath>
#include <stdexcept>

namespace mco {
double startup_surface_factor(std::uint32_t selector, float speed) {
    if (!std::isfinite(speed)) {
        throw std::invalid_argument("finite startup speed required");
    }
    if (speed < 1.f) return 0.;
    const double value = speed;
    if (selector == 2) return value * .000096f + .012f;
    if (selector == 3 || selector == 5) return value * .000072f + .013f;
    return value * .000048f + .01f;
}

std::array<float, 135> startup_resistance_table(float mass, float coefficient,
                                              float area, std::uint32_t selector) {
    if (!std::isfinite(mass) || !std::isfinite(coefficient) || !std::isfinite(area)) {
        throw std::invalid_argument("finite startup resistance inputs required");
    }
    // The original rounds this product once before producing the table.
    const float mass_force = static_cast<float>(static_cast<double>(mass) * 9.81f);
    if (!std::isfinite(mass_force)) {
        throw std::invalid_argument("finite startup mass force required");
    }
    std::array<float, 135> output{};
    for (unsigned index = 0; index < output.size(); ++index) {
        const double rolling = startup_surface_factor(selector, static_cast<float>(index)) * 1.1f * mass_force;
        const double aerodynamic = static_cast<double>(index * index) * coefficient * area * .5905f;
        output[index] = static_cast<float>(aerodynamic + rolling);
        if (!std::isfinite(output[index])) {
            throw std::invalid_argument("finite startup resistance output required");
        }
    }
    return output;
}
}
