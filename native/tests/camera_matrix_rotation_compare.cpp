#include "mco/camera_matrix_rotation.hpp"
#include "cell_io.hpp"
int main() {
    return cell_io::run([](std::istream& input) {
        using namespace cell_io;
        const auto axis=read(input),alias=read(input);
        const auto turns=std::bit_cast<float>(read(input));
        std::array<float,9> source{},destination{};
        for(auto& value:source) value=std::bit_cast<float>(read(input));
        for(auto& value:destination) value=std::bit_cast<float>(read(input));
        auto& output=alias ? source : destination;
        mco::camera_matrix_rotation(source,turns,output,axis);
        for(auto value:source) emit(std::bit_cast<std::uint32_t>(value));
        for(auto value:output) emit(std::bit_cast<std::uint32_t>(value));
    });
}
