#include "mco/collision_response.hpp"
#include <iomanip>
#include <iostream>
#include <limits>
#include <stdexcept>
int main() {
    std::cout << std::setprecision(std::numeric_limits<float>::max_digits10);
    std::size_t count=0;
    while (true) {
        std::array<double,3> v{}, n{}; double threshold, sliding;
        if (!(std::cin >> v[0])) return std::cin.eof() ? 0 : 2;
        if (++count > 100000 || !(std::cin >> v[1] >> v[2] >> n[0] >> n[1] >> n[2] >> threshold >> sliding)) return 2;
        try {
            const auto result=mco::tangential_response(v,n,threshold,sliding);
            std::cout << result.status;
            for (auto value:result.vector) std::cout << ' ' << value;
            std::cout << '\n';
        } catch (const std::invalid_argument&) { return 3; }
    }
}
