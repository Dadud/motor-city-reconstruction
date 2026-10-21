#include "mco/render_list.hpp"
#include <algorithm>
#include <stdexcept>
#include <string>
#include <utility>

namespace mco {
std::optional<RenderRecord> collect_render_group(
    std::span<const FceModel> models, std::string_view group, int lod,
    std::uint32_t extra_flags, std::uint32_t mesh_type) {
    if(lod<0) throw std::invalid_argument("LOD must be nonnegative");
    if(group.empty() || group.find('\0')!=std::string_view::npos)
        throw std::invalid_argument("group must be nonempty and NUL-free");
    const auto requested=std::min(lod,3);
    constexpr std::array<std::string_view,4> prefixes{":H",":M",":S",":T"};
    for(int level=requested;level>=0;--level) {
        const std::string name=std::string(prefixes[static_cast<std::size_t>(level)])+
                               std::string(group);
        for(std::size_t model_index=0;model_index<models.size();++model_index) {
            const auto& parts=models[model_index].parts;
            const auto found=std::find_if(parts.begin(),parts.end(),
                [&](const auto& part){return part.name==name;});
            if(found==parts.end()) continue;
            RenderRecord record{};
            record.words[1]=static_cast<std::uint32_t>(model_index);
            record.words[3]=static_cast<std::uint16_t>(found-parts.begin());
            // The native code stores the requested LOD bit even after fallback.
            record.words[4]=(std::uint32_t{1}<<static_cast<unsigned>(requested))|
                            extra_flags;
            record.words[5]=mesh_type;
            return record;
        }
    }
    return std::nullopt;
}

std::vector<RenderRecord> collect_body_render_records(
    const FceModel& model, std::uint32_t flags, int lod, bool include_interior) {
    const std::array models{model};
    std::vector<RenderRecord> records;
    const auto add=[&](std::string_view group,std::uint32_t extra,
                       std::uint32_t type) {
        if(auto record=collect_render_group(models,group,lod,extra,type))
            records.push_back(*record);
        return !records.empty();
    };
    add("body",0,1);
    add("headlight",0,2);
    if(include_interior) {
        const auto before=records.size();
        add("interior",0x80,0x14);
        if(records.size()!=before) {
            add("dashlight",0x80,0x13);
            add("steer",0x180,0x12);
        }
    }
    if((flags&0x40000u)==0) return records;

    for(const auto& [bit,group]:std::array<std::pair<std::uint32_t,std::string_view>,5>{
            {{1,"hood"},{2,"hoodhole"},{4,"scooplarge"},
             {8,"scoopsmall"},{0x10,"scoopfact"}}})
        if(flags&bit) add(group,0,0);
    const bool top=(flags&0x20u)!=0;
    const bool convertible=(flags&0x80u)!=0;
    const bool chopped=(flags&0x40u)!=0;
    if(top) { add("top",0x100,0); add("shield",0x100,0); add("swin",0x100,0); }
    if(convertible) {
        add("convertible",0x100,3); add("shield",0x100,0); add("swin",0x100,3);
    }
    if(chopped) {
        add("topchop",0x100,0); add("shieldchop",0x100,0); add("swinchop",0x100,0);
    }
    if(flags&0x20000u) add(chopped?"cagechop":"cage",0x100,0);
    for(const auto& [bit,group]:std::array<std::pair<std::uint32_t,std::string_view>,3>{
            {{0x800,"bumper"},{0x100,"rmirror"},{0x200,"lmirror"}}})
        if(flags&bit) add(group,0,0);
    if(flags&0x400u) add("skirt",0,0);
    add("wheelwell",0,0);
    add((flags&0x1000u)?"ffender":"fenderlight",0,0);
    for(const auto& [bit,group]:std::array<std::pair<std::uint32_t,std::string_view>,4>{
            {{0x2000,"rfender"},{0x4000,"boards"},
             {0x8000,"chin"},{0x10000,"firewall"}}})
        if(flags&bit) add(group,0,0);
    if(!top&&!convertible&&!chopped) add("shield",0x100,0);
    return records;
}

std::optional<std::pair<FcePart,RenderRecord>> attach_rear_suspension(
    const FcePart& marker, const FceModel& component, int lod,
    std::uint32_t model_handle) {
    if(marker.name!=":PPrearsusp")
        throw std::invalid_argument("rear suspension attachment requires :PPrearsusp");
    if(lod<0) throw std::invalid_argument("LOD must be nonnegative");
    constexpr std::array<std::string_view,4> prefixes{":PH",":PM",":PS",":PT"};
    const auto requested=std::min(lod,3);
    for(int level=requested;level>=0;--level) {
        const std::string name=std::string(prefixes[static_cast<std::size_t>(level)])+
                               "rearsusp";
        for(std::size_t index=0;index<component.parts.size();++index) {
            if(component.parts[index].name!=name) continue;
            auto part=component.parts[index];
            part.origin=marker.origin;
            RenderRecord record{};
            record.words[1]=model_handle;
            record.words[3]=static_cast<std::uint16_t>(index);
            record.words[4]=(std::uint32_t{1}<<static_cast<unsigned>(requested))|0x80u;
            record.words[5]=0x0f;
            return std::pair{std::move(part),record};
        }
    }
    return std::nullopt;
}

std::optional<ComponentAttachment> attach_component_marker(
    const FcePart& marker, const FceModel& component, int lod,
    std::uint32_t model_handle) {
    if(marker.name.size()<4 || marker.name.compare(0,3,":PP")!=0)
        throw std::invalid_argument("generic attachment requires a :PP marker");
    if(lod<0) throw std::invalid_argument("LOD must be nonnegative");
    const auto text=std::string_view(marker.name).substr(3);
    constexpr std::array<std::string_view,10> classes{
        "LF","RF","LR","RR","L","R","A","B","C","F"};
    std::string_view class_prefix;
    for(const auto prefix:classes) {
        if(text.starts_with(prefix)) { class_prefix=prefix; break; }
    }
    const auto suffix=text.substr(class_prefix.size());
    if(suffix.empty()) throw std::invalid_argument("component marker suffix is empty");
    const bool mirrored=class_prefix.starts_with('R');
    const auto requested=std::min(lod,3);
    constexpr std::array<std::string_view,4> prefixes{":PH",":PM",":PS",":PT"};
    std::size_t selected=component.parts.size();
    for(int level=requested;level>=0 && selected==component.parts.size();--level) {
        const std::string name=std::string(prefixes[static_cast<std::size_t>(level)])+
                               std::string(suffix);
        for(std::size_t index=0;index<component.parts.size();++index) {
            if(component.parts[index].name==name) { selected=index; break; }
        }
    }
    if(selected==component.parts.size()) return std::nullopt;
    const auto anchor=component.parts[selected].origin;
    const auto target=marker.origin;
    const auto rebase=[&](const Vec3& point) {
        Vec3 output{};
        for(std::size_t axis=0;axis<3;++axis) {
            volatile float delta=point[axis]-anchor[axis];
            if(mirrored && axis==0) delta=-delta;
            volatile float value=delta+target[axis];
            output[axis]=value;
        }
        return output;
    };
    ComponentAttachment result{};
    result.model=component;
    result.part_index=static_cast<std::uint16_t>(selected);
    for(std::size_t index=0;index<result.model.parts.size();++index) {
        auto& part=result.model.parts[index];
        if(lod==0) {
            if(part.name.starts_with(":PP")) part.origin=rebase(part.origin);
            for(auto& vertex:part.vertices) vertex=rebase(vertex);
        }
        if(index==selected) part.origin=target;
    }
    result.record.words[1]=model_handle;
    result.record.words[3]=result.part_index;
    result.record.words[4]=(std::uint32_t{1}<<static_cast<unsigned>(requested))|
                           (mirrored?0x40u:0u);
    result.record.words[5]=0;
    return result;
}

std::optional<ComponentNodeSelection> select_component_node(
    std::span<const ComponentModelNode> nodes, std::string_view class_prefix,
    std::string_view suffix, int lod) {
    if(suffix.empty() || suffix.find('\0')!=std::string_view::npos ||
       class_prefix.find('\0')!=std::string_view::npos)
        throw std::invalid_argument("component class and suffix must be NUL-free");
    if(lod<0) throw std::invalid_argument("LOD must be nonnegative");
    constexpr std::array<std::string_view,12> classes{
        "","LF","RF","LR","RR","L","R","A","B","C","F","R"};
    constexpr std::array<std::string_view,4> lod_prefixes{":PH",":PM",":PS",":PT"};
    const auto requested=std::min(lod,3);
    for(const auto& node:nodes) {
        if(node.class_index>=classes.size())
            throw std::invalid_argument("component class index outside native table");
        if(!node.model && classes[node.class_index]==class_prefix)
            throw std::invalid_argument("matching component node has no model");
    }
    for(int level=requested;level>=0;--level) {
        const std::string name=std::string(lod_prefixes[static_cast<std::size_t>(level)])+
                               std::string(suffix);
        for(std::size_t node_index=0;node_index<nodes.size();++node_index) {
            const auto& node=nodes[node_index];
            if(classes[node.class_index]!=class_prefix) continue;
            const auto& parts=node.model->parts;
            const auto found=std::find_if(parts.begin(),parts.end(),
                [&](const auto& part){return part.name==name;});
            if(found==parts.end()) continue;
            const auto part_index=static_cast<std::size_t>(found-parts.begin());
            ComponentNodeSelection result{};
            result.node_index=node_index;
            result.part_index=static_cast<std::uint16_t>(part_index);
            result.record.words[1]=node.model_handle;
            result.record.words[3]=result.part_index;
            result.record.words[4]=(std::uint32_t{1}<<static_cast<unsigned>(requested))|
                (class_prefix.starts_with('R')?0x40u:0u);
            return result;
        }
    }
    return std::nullopt;
}

std::optional<ResolvedComponentAttachment> attach_component_from_nodes(
    const FcePart& marker, std::span<const ComponentModelNode> nodes, int lod) {
    if(marker.name.size()<4 || marker.name.compare(0,3,":PP")!=0)
        throw std::invalid_argument("generic attachment requires a :PP marker");
    const auto text=std::string_view(marker.name).substr(3);
    constexpr std::array<std::string_view,10> prefixes{
        "LF","RF","LR","RR","L","R","A","B","C","F"};
    std::string_view class_prefix;
    for(const auto prefix:prefixes) {
        if(text.starts_with(prefix)) { class_prefix=prefix; break; }
    }
    const auto suffix=text.substr(class_prefix.size());
    const auto selection=select_component_node(nodes,class_prefix,suffix,lod);
    if(!selection) return std::nullopt;
    const auto& node=nodes[selection->node_index];
    const auto attachment=attach_component_marker(marker,*node.model,lod,
                                                    node.model_handle);
    if(!attachment) return std::nullopt;
    return ResolvedComponentAttachment{selection->node_index,*attachment};
}

RenderList build_render_list(std::vector<RenderRecord> records) {
    // 0x52dd70 swaps when the left word 5 is smaller, producing descending
    // order while preserving collector order for equal keys.
    for(std::size_t end=records.size();end>1;--end) {
        bool changed=false;
        for(std::size_t i=0;i+1<end;++i) {
            if(records[i].words[5]<records[i+1].words[5]) {
                std::swap(records[i],records[i+1]);
                changed=true;
            }
        }
        if(!changed) break;
    }
    RenderList result;
    result.records=std::move(records);
    result.next_indices.reserve(result.records.size());
    for(std::size_t i=0;i<result.records.size();++i)
        result.next_indices.push_back(i+1<result.records.size()?i+1:RenderList::npos);
    return result;
}
}
