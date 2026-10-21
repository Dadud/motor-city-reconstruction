#pragma once
#include <array>
#include <cstddef>
#include <cstdint>
#include <optional>
#include <span>
#include <string_view>
#include <utility>
#include <vector>
#include "mco/fce.hpp"

namespace mco {
struct RenderRecord {
    std::array<std::uint32_t,9> words{};
};
struct RenderList {
    std::vector<RenderRecord> records;
    // The native pointer chain is represented by indices; null is npos.
    std::vector<std::size_t> next_indices;
    static constexpr std::size_t npos=static_cast<std::size_t>(-1);
};
struct ComponentAttachment {
    FceModel model;
    std::uint16_t part_index{};
    RenderRecord record;
};
struct ComponentModelNode {
    std::uint32_t class_index{};
    const FceModel* model{};
    std::uint32_t model_handle{};
};
struct ComponentNodeSelection {
    std::size_t node_index{};
    std::uint16_t part_index{};
    RenderRecord record;
};
struct ResolvedComponentAttachment {
    std::size_t node_index{};
    ComponentAttachment attachment;
};
std::optional<RenderRecord> collect_render_group(
    std::span<const FceModel> models, std::string_view group, int lod,
    std::uint32_t extra_flags=0, std::uint32_t mesh_type=0);
std::vector<RenderRecord> collect_body_render_records(
    const FceModel& model, std::uint32_t flags, int lod,
    bool include_interior=true);
std::optional<std::pair<FcePart,RenderRecord>> attach_rear_suspension(
    const FcePart& marker, const FceModel& component, int lod,
    std::uint32_t model_handle=0);
std::optional<ComponentAttachment> attach_component_marker(
    const FcePart& marker, const FceModel& component, int lod,
    std::uint32_t model_handle=0);
std::optional<ComponentNodeSelection> select_component_node(
    std::span<const ComponentModelNode> nodes, std::string_view class_prefix,
    std::string_view suffix, int lod);
std::optional<ResolvedComponentAttachment> attach_component_from_nodes(
    const FcePart& marker, std::span<const ComponentModelNode> nodes, int lod);
RenderList build_render_list(std::vector<RenderRecord> records);
}
