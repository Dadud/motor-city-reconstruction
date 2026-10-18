#pragma once
#include "mco/input_callback_dispatch_state.hpp"
#include "mco/input_key_queue.hpp"
#include "mco/input_translation_state.hpp"
#include "mco/input_key_actions.hpp"
namespace mco {
struct InputDefaultKeyState {
    InputCallbackDispatchState& control;
    InputKeyQueue& queue;
    InputTranslationState& translation;
    InputKeyActions& actions;
};
}
