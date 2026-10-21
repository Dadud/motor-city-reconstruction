#include "mco/matrix_math.hpp"
#include <bit>
#include <iostream>

int main() {
    int mode{};
    while (std::cin>>std::dec>>mode) {
        if (mode==1) {
            std::array<float,3> left{},right{};
            for (auto& value:left) if (!(std::cin>>value)) return 2;
            for (auto& value:right) if (!(std::cin>>value)) return 2;
            std::cout<<mco::dot_3_f32(left,right)<<'\n';
            continue;
        }
        if (mode==2 || mode==3) {
            std::array<float,9> matrix{};
            for(auto& value:matrix) if(!(std::cin>>std::dec>>value)) return 2;
            std::array<float,9> result{};
            if(mode==2) {
                std::array<float,3> delta{};
                for(auto& value:delta) if(!(std::cin>>value)) return 2;
                result=mco::integrate_rotation_matrix(matrix,delta);
            } else {
                int iterations{};
                if(!(std::cin>>iterations)) return 2;
                result=mco::repair_rotation_matrix(matrix,iterations);
            }
            for(const auto value:result)
                std::cout<<std::hex<<std::bit_cast<std::uint32_t>(value)<<' ';
            std::cout<<'\n';
            continue;
        }
        std::array<std::uint32_t,9> values{};
        if (!(std::cin>>std::hex>>values[0])) return 2;
        for (std::size_t i=1;i<values.size();++i) if (!(std::cin>>values[i])) return 2;
        for (const auto value:mco::transpose_3x3_words(values)) std::cout<<std::hex<<value<<' ';
        std::cout<<'\n';
    }
}
