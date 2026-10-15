#include "mco/air_density.hpp"
#include <array>
#include <cmath>
#include <stdexcept>
namespace mco {
namespace {
double f(double x) {
    const double result=static_cast<float>(x);
    if (!std::isfinite(result)) throw std::invalid_argument("finite float required");
    return result;
}
}
double calculate_air_density(double altitude,bool cold,bool enabled,std::uint32_t weather) {
    const std::array<double,13> densities={f(1.347),f(1.2849),f(1.225),f(1.1673),f(1.1117),f(1.0581),f(1.0066),
        f(.95695),f(.90925),f(.8634),f(.81935),f(.77704),f(.73643)};
    const double shifted=f(f(altitude)+500),index=std::floor(shifted*f(.002));
    if(index<0 || index>=12) throw std::invalid_argument("altitude outside verified density table interval");
    double temperature=f(cold?278.15:288.15);
    const auto selected=enabled?weather:0;
    if(selected==2) temperature=f(temperature-20);
    else if(selected==1) temperature=f(temperature-10);
    const auto i=static_cast<unsigned>(index);
    const double density=densities[i]+(densities[i+1]-densities[i])*(shifted-index*500)*f(.002);
    return f(density*f(288.15)/temperature);
}
}
