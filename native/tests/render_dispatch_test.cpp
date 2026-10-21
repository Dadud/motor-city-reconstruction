#include "mco/render_dispatch.hpp"
#ifdef NDEBUG
#undef NDEBUG
#endif
#include <cassert>
#include <stdexcept>

int main() {
    int old_matrix{},old_position{},new_matrix{},new_position{},destination{},points{};
    mco::RenderDispatchState state{&old_matrix,&old_position,7,false,false,true};
    bool called=false;
    mco::dispatch_object_geometry(state,22,&points,&destination,&new_matrix,
        &new_position,12,[&](auto mode,auto count,const auto* input,
          auto* output,const auto* matrix,const auto* position,auto stride) {
            called=true; assert(mode==6); assert(count==22);
            assert(output==&destination && input==&points);
            assert(matrix==&new_matrix && position==&new_position && stride==12);
        });
    assert(called);
    assert(state.matrix_source==&old_matrix && state.position_source==&old_position);
    assert(state.output_stride_bytes==7 && state.matrix_dirty && state.position_dirty);
    assert(state.dispatch_cache_valid);

    try {
        mco::dispatch_object_geometry(state,22,&points,&destination,&new_matrix,
            nullptr,0,[](auto...){throw std::runtime_error("backend");});
        assert(false);
    } catch(const std::runtime_error&) {}
    assert(state.matrix_source==&old_matrix && state.position_source==&old_position);
    assert(state.output_stride_bytes==7 && !state.dispatch_cache_valid);
}
