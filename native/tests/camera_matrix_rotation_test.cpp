#include "mco/camera_matrix_rotation.hpp"
#include <array>
#include <limits>
#include <stdexcept>
int main() {
    std::array<float,9> source{1,2,3,4,5,6,7,8,9},out{};
    for(unsigned axis=0;axis<3;++axis) {
        mco::camera_matrix_rotation(source,0,out,axis);
        if(source!=out) throw std::runtime_error("zero rotation changed matrix");
        auto alias=source;
        mco::camera_matrix_rotation(source,0.125f,out,axis);
        mco::camera_matrix_rotation(alias,0.125f,alias,axis);
        if(alias!=out) throw std::runtime_error("in-place rotation diverged");
        const auto preserved=axis==0 ? 0u : axis==1 ? 3u : 6u;
        for(unsigned i=0;i<3;++i) if(out[preserved+i]!=source[preserved+i])
            throw std::runtime_error("axis invariant row changed");
    }
    unsigned rejected=0;
    for(float angle : {1025.f,std::numeric_limits<float>::infinity(),
                       std::numeric_limits<float>::quiet_NaN()}) {
        try {mco::camera_matrix_rotation(source,angle,out,0);}
        catch(const std::invalid_argument&) {++rejected;}
    }
    try {mco::camera_matrix_rotation(source,0,out,3);}
    catch(const std::invalid_argument&) {++rejected;}
    std::array<float,10> overlap{};
    try {mco::camera_matrix_rotation(std::span<const float,9>(overlap.data(),9),0,
                                   std::span<float,9>(overlap.data()+1,9),0);}
    catch(const std::invalid_argument&) {++rejected;}
    source[0]=std::numeric_limits<float>::infinity();
    try {mco::camera_matrix_rotation(source,0,out,0);}
    catch(const std::invalid_argument&) {++rejected;}
    if(rejected!=6) throw std::runtime_error("unsupported input accepted");
}
