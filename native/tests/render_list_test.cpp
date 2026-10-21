#include "mco/render_list.hpp"
#ifdef NDEBUG
#undef NDEBUG
#endif
#include <cassert>
#include <string>

int main() {
    using mco::RenderRecord;
    const auto make=[](std::uint32_t id,std::uint32_t key) {
        RenderRecord record{}; record.words[0]=id; record.words[5]=key; return record;
    };
    auto result=mco::build_render_list({make(0,0x11),make(1,0x10),
                                        make(2,0x10),make(3,0x12)});
    assert(result.records.size()==4);
    assert(result.records[0].words[0]==3 && result.records[1].words[0]==0);
    assert(result.records[2].words[0]==1 && result.records[3].words[0]==2);
    assert((result.next_indices==std::vector<std::size_t>{1,2,3,mco::RenderList::npos}));
    assert(mco::build_render_list({}).next_indices.empty());

    mco::FceModel first{0,{{":Hdoor",{}, {},{},{}}},{}};
    mco::FceModel second{0,{{":Mdoor",{}, {},{},{}}},{}};
    const std::array models{first,second};
    auto selection=mco::collect_render_group(models,"door",3,0x80,0x13);
    assert(selection && selection->words[1]==1 && selection->words[3]==0);
    assert(selection->words[4]==0x88 && selection->words[5]==0x13);
    assert(!mco::collect_render_group(models,"missing",2));

    mco::FceModel body{0,{}, {}};
    for(const auto* name:{":Hbody",":Hheadlight",":Hinterior",":Hdashlight",
                          ":Hsteer",":Hhood",":Htop",":Hshield",":Hswin",
                          ":Hbumper",":Hwheelwell",":Hfenderlight"})
        body.parts.push_back({name,{}, {},{}, {}});
    const auto body_records=mco::collect_body_render_records(
        body,0x40000|0x20|0x800,0,true);
    assert(body_records.size()==11);
    assert(body_records[0].words[5]==1 && body_records[1].words[5]==2);
    assert(body_records[2].words[5]==0x14 && body_records[3].words[5]==0x13);
    assert(body_records[4].words[5]==0x12);
    assert(body_records[5].words[3]==6 && body_records[6].words[3]==7);
    mco::FcePart marker{":PPrearsusp",{2.5f,-3.0f,4.25f},{},{},{}};
    mco::FceModel suspension{0,{{":PHrearsusp",{9,8,7},{},{},{}},
                                  {":PTrearsusp",{6,5,4},{},{},{}}},{}};
    auto attached=mco::attach_rear_suspension(marker,suspension,3,0x1234);
    assert(attached && attached->first.origin==marker.origin);
    assert(attached->second.words[1]==0x1234 && attached->second.words[3]==1);
    assert(attached->second.words[4]==0x88 && attached->second.words[5]==0xf);
    mco::FcePart fog_marker{":PPRfog",{20,30,40},{},{},{}};
    mco::FceModel fog{0,{{":PHfog",{2,3,4},{{8,10,12}},{},{}},
                           {":PPRchild",{4,5,6},{},{},{}}},{}};
    auto generic=mco::attach_component_marker(fog_marker,fog,0,0x5678);
    assert(generic && generic->part_index==0);
    assert((generic->model.parts[0].vertices[0]==mco::Vec3{14,37,48}));
    assert((generic->model.parts[1].origin==mco::Vec3{18,32,42}));
    assert(generic->record.words[1]==0x5678 && generic->record.words[4]==0x41);

    mco::FceModel rear_left{0,{{":PHtire",{}, {},{}, {}}},{}};
    mco::FceModel rear_alias{0,{{":PTtire",{}, {},{}, {}}},{}};
    const std::array owner_nodes{
        mco::ComponentModelNode{6,&rear_left,0x1000},
        mco::ComponentModelNode{11,&rear_alias,0x2000}};
    auto found=mco::select_component_node(owner_nodes,"R","tire",3);
    assert(found && found->node_index==1 && found->part_index==0);
    assert(found->record.words[1]==0x2000 && found->record.words[4]==0x48);
    auto found_lod0=mco::select_component_node(owner_nodes,"R","tire",0);
    assert(found_lod0 && found_lod0->node_index==0);
}
