#include "mco/geometry_transform.hpp"
#ifdef NDEBUG
#undef NDEBUG
#endif
#include <cassert>

int main() {
    std::array<float,66> input{};
    for(std::size_t i=0;i<22;++i) {
        input[i*3]=1; input[i*3+1]=2; input[i*3+2]=3;
    }
    const std::array<float,9> matrix{1,2,3,4,5,6,7,8,9};
    const auto output=mco::transform_world_vertices_22(input,matrix,{10,20,30});
    for(std::size_t i=0;i<22;++i) {
        assert(output[i*3]==40);
        assert(output[i*3+1]==56);
        assert(output[i*3+2]==72);
    }
}
