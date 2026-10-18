#pragma once
#include "mco/input_device_access.hpp"
#include "mco/input_device_lifetime_state.hpp"
#include "mco/layouts.hpp"
namespace mco {
// Keep images/platform contexts from views, and alias all globals shared by
// lifetime and acquisition. The referenced globals outlive both views.
inline InputDeviceAccess input_device_access_from_lifetime(InputDeviceLifetimeState& lifetime,const InputDeviceAccess& views){
    return {lifetime.interface_handle,lifetime.device,views.keyboard,views.information,
        lifetime.diagnostic_file,lifetime.diagnostic_line,views.resolve,views.get_information,views.invalid_kind,views.user};
}
inline void input_device_bind_callback_table(InputDeviceLifetimeState& lifetime,std::span<std::byte,scan_translation_tables::size> tables){
    lifetime.callback.bind(tables.subspan<scan_translation_tables::callback_word,4>());
}
}
