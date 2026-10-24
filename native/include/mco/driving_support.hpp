#pragma once
#include "mco/support_prediction.hpp"
#include "mco/track_surface_sample.hpp"
#include <array>
#include <functional>

namespace mco {
using SupportNormalSeedProvider =
    std::function<std::array<float, 3>(const SupportQuery &)>;

// Bind the recovered 0x42e010 track query to the four-wheel support projector.
SupportProjection project_track_surface(const TrackSurfaceWorld &world,
                                         const SupportQuery &query,
                                         std::array<float, 3> normal_seed);
SupportPredictionOutput predict_support_on_track(
    SupportPredictionState state, const TrackSurfaceWorld &world,
    const SupportNormalSeedProvider &normal_seed_for_query);
}
