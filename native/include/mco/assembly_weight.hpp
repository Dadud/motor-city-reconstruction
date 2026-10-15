#pragma once
#include <array>
namespace mco {
// Ordered mechanical mass observations; slot meanings remain internal research.
struct AssemblyWeightInputs {
    double body_mass;
    double body_fraction;
    double wheelbase;
    double shared_mass;
    std::array<double,23> front_masses;
    std::array<double,13> rear_masses;
};
// Helper return before the original assembly caller's float32 store.
double assembled_front_weight_fraction(const AssemblyWeightInputs& inputs);
}
