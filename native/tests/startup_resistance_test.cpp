#include "mco/startup_resistance.hpp"
#include <limits>
#include <stdexcept>

int main() {
    if (mco::startup_surface_factor(2, .99999994f) != 0 ||
        mco::startup_surface_factor(3, 33) != mco::startup_surface_factor(5, 33)) {
        throw std::runtime_error("surface threshold or selector group regression");
    }
    const auto output = mco::startup_resistance_table(1000, .3f, 2, 2);
    if (output[0] != 0 || !(output.back() > output[1])) {
        throw std::runtime_error("startup resistance regression");
    }
    try {
        mco::startup_resistance_table(std::numeric_limits<float>::infinity(), .3f, 2, 0);
    } catch (const std::invalid_argument&) {
        return 0;
    }
    throw std::runtime_error("nonfinite mass accepted");
}
