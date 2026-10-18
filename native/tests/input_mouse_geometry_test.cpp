#include "input_mouse_geometry_cases.hpp"
int main(){
    using namespace mco;
    for(std::uint32_t first=0;first<2;++first)for(std::uint32_t second=0;second<2;++second){
        mouse_input_cases::Sample sample;
        sample.mouse.enabled=0; // This position path has no mouse-enable guard.
        sample.script.success=0; // Failed ClientToScreen must use original values.
        sample.mouse.store(mouse_input_image::minimum_x,10);
        sample.mouse.store(mouse_input_image::maximum_x,0xfffffff6u); // Reversed bounds.
        sample.mouse.store(mouse_input_image::minimum_y,0);
        sample.mouse.store(mouse_input_image::maximum_y,80);
        std::uint32_t x=77,y=88;
        InputMouseGeometryState state{sample.mouse,x,y};
        input_mouse_geometry_cases::Script context;
        context.fixture.mouse=&sample.mouse;context.first_query=first;context.second_query=second;
        input_mouse_set_position(state,sample.platform,{context.invoke,&context},30,90);
        if(x!=0xfffffff6u || y!=80 || sample.mouse.load(mouse_input_image::x)!=x || sample.mouse.load(mouse_input_image::y)!=y)return 1;
        if(sample.script.logs.size()!=3 || sample.script.logs[0][0]!=3 || sample.script.logs[1][0]!=4 ||
           sample.script.logs[1][1]!=x || sample.script.logs[1][2]!=y || sample.script.logs[2][0]!=5)return 2;
        const auto& logs=context.fixture.logs;
        if(logs.size()!=(first?5u:4u) || logs[0][1]!=0x6be930 || logs[1][1]!=(first?0x7b54a0u:0x8c4938u))return 3;
        if(logs[logs.size()-2][1]!=0x6be930 || logs.back()[1]!=(second?0x7b54d0u:0x8c4938u))return 4;
        if(first && logs[2][1]!=0x6cf1b0)return 5;
    }
    return 0;
}
