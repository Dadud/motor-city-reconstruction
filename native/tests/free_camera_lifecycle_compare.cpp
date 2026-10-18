#include "input_queue_cases.hpp"
#include "mco/free_camera_update.hpp"
#include "mco/input_key_down.hpp"
#include "mco/input_key_release.hpp"
#include "mco/input_queue_resize.hpp"
int main() {
    return cell_io::run([](std::istream& input) {
        auto image=cell_io::image<512>(input),latches=cell_io::image<512>(input);
        auto subject=cell_io::image<68>(input);
        auto f=queue_cases::Fixture::read(input);
        auto queue=f.state();
        std::array<std::byte,0x6000> arena{};
        std::array<std::byte,65536> grid{};
        mco::detail::write_word(arena,0x3000+0x680,8);
        const mco::SpatialQueryMemory memory{grid,arena,0x71000000};
        const mco::TrackSurfaceWorld world{memory,{0,0},{1,1},0x71003000,0x71001000,0,8};
        mco::FreeCameraState camera{image,std::span<const std::byte,128>(f.keys.data(),128),latches,
            [](std::uint32_t identity,void* user) -> std::span<const std::byte,68> {
                if(identity!=0x7100b000) throw std::invalid_argument("unmapped camera subject");
                return *static_cast<std::array<std::byte,68>*>(user);
            },&subject};
        const auto count=cell_io::read(input);
        if(count==0 || count>4096) throw std::invalid_argument("camera lifecycle count");
        for(unsigned i=0;i<count;++i) {
            const auto op=cell_io::read(input),a=cell_io::read(input),b=cell_io::read(input);
            const auto bits=((a&127u)<<16)|((a>>7)<<24)|(b&65535u);
            std::uint32_t result=0;
            if(op==0) result=mco::input_key_down(queue,f.remap,1,7,0x100,0x70,bits);
            else if(op==1) result=mco::input_key_release(f.keys,f.remap,queue.load(input_queue_image::remap),1,7,7,bits);
            else if(op==2) mco::free_camera_update(camera,world,a,b);
            else if(op==3) mco::input_queue_resize(queue,a);
            else throw std::invalid_argument("camera lifecycle operation");
            cell_io::emit(result);cell_io::emit(image);cell_io::emit(latches);
            f.emit();cell_io::emit(subject);f.logs.clear();
        }
    });
}
