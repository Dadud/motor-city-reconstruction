"""Compare the C++ 0x42e010 terrain-sampling composition with Python."""
import json
import struct
import subprocess

from client.track_surface_lookup import TrackSurfaceMemory, TrackSurfaceWorld
from client.track_surface_sample import sample_track_surface
from client.support_prediction import (PredictionWheel,SupportPredictionState,
    SupportQuery,predict_support)
from client.driving_support import project_track_surface
from tools.track_surface_cases import BASE, BLOCKS, GEOMETRY, PATH, configurations, fixture


def bits(value):
    return struct.unpack('<I',struct.pack('<f',value))[0]


def verify(runner,cases=1200):
    corpus=list(configurations())[:cases]
    lines=[];expected=[]
    vertices=((0,0,0),(16,1,0),(16,3,16),(0,-2,16))
    for mode,cached,previous,neighbors,upward,x,z,seed in corpus:
        arena,root,query=fixture(mode,cached,previous,neighbors,upward,x,z,seed)
        for block in range(3):
            for vertex,coordinates in enumerate(vertices):
                struct.pack_into('<3f',arena,GEOMETRY-BASE+block*0x200+vertex*12,*coordinates)
        world=TrackSurfaceWorld(TrackSurfaceMemory(root+bytes(65536-len(root)),bytes(arena),BASE),
            (0.,0.),(1.,1.),BLOCKS,PATH,2,24)
        point=bytearray(struct.pack('<3f',x,7.,z))
        found=sample_track_surface(world,query,point,0,normal_seed=(0,1,0))
        request=SupportQuery(0,(x,7.,z),0,(1.,2.,3.))
        projection=project_track_surface(world,request,normal_seed=(.3,.8,-.2))
        rec=projection.record
        projection_values=[rec.sector&0xffffffff,rec.group&0xffffffff,rec.status,
            rec.surface_id or 0,*[value or 0 for value in rec.vertex_ids],rec.surface_code or 0,
            *[bits(float(value)) for value in projection.point],
            *[bits(float(value)) for value in projection.reference_position]]
        support_state=SupportPredictionState(tuple(PredictionWheel(
            ((.25 if i&1 else -.25),0.,(.25 if i&2 else -.25)),(float(x),7.,float(z)),.5)
            for i in range(4)),(float(x),7.,float(z)),(.1,0.,-.2),context=0,
            fallback_surface=9,support_count=3)
        support=predict_support(support_state,lambda q:project_track_surface(
            world,q,normal_seed=(.3,.8,-.2)))
        support_values=[support.state.support_count]
        for wheel in support.state.wheels:
            rec=wheel.record
            support_values.extend((int(wheel.contact),bits(wheel.support_delta),wheel.surface_class,
                *[bits(float(v)) for v in wheel.world_point],rec.sector&0xffffffff,
                rec.group&0xffffffff,rec.status,rec.surface_id or 0,
                *[v or 0 for v in rec.vertex_ids],rec.surface_code or 0,
                *wheel.query_tail))
        for q in support.queries:
            support_values.extend((q.context,*[bits(float(v)) for v in q.point],
                                   *[bits(float(v)) for v in q.previous_world]))
        expected.append((int(found),bytes(query),bytes(point),projection_values,support_values))
        lines.append(' '.join(map(str,(mode,cached,previous,neighbors,upward,x&0xffffffff,z&0xffffffff,seed))))
    nodes=bytearray(0x8000);grid=bytearray(65536)
    def word(address,value):struct.pack_into('<I',nodes,address,value&0xffffffff)
    def real(address,value):struct.pack_into('<f',nodes,address,value)
    def half(address,value):struct.pack_into('<h',nodes,address,value)
    struct.pack_into('<4I',grid,0,0xdeadbeef,1,0x200,0)
    for offset,value in ((0,100),(2,0),(4,0),(6,0),(8,0),(10,1)):half(offset,value)
    block,geometry,path=0x1000,0x5000,0x4000
    word(block+0x3c,geometry+0x80);word(block+0x14c,geometry);word(block+0x67c,0);word(block+0x680,8)
    for j in range(8):word(block+0x6a4+j*4,0xffffffff)
    for offset,value in ((0x664,0),(0x66c,0),(0x670,16),(0x678,16)):real(block+offset,value)
    row_vertices=((0,0,0),(16,1,0),(16,3,16),(0,-2,16))
    for i,vertex in enumerate(row_vertices):
        for j,value in enumerate(vertex):real(geometry+i*12+j*4,value)
        half(geometry+0x80+i*2,i)
    for j in range(8):
        real(path+j*0x54,j*2);real(path+j*0x54+4,2);real(path+j*0x54+8,j)
    row_world=TrackSurfaceWorld(TrackSurfaceMemory(bytes(grid),bytes(nodes),0),
        (0.,0.),(1.,1.),block,path,0,8)
    row_seed=17
    row_query=bytearray((row_seed+i*37)&255 for i in range(68))
    row_point=bytearray(struct.pack('<3f',8,7,8))
    row_found=sample_track_surface(row_world,row_query,row_point,0,normal_seed=(.3,.8,-.2))
    row_request=SupportQuery(0,(8.,7.,8.),0,(1.,2.,3.))
    row_projection=project_track_surface(row_world,row_request,normal_seed=(.3,.8,-.2))
    rec=row_projection.record
    projection_values=[rec.sector&0xffffffff,rec.group&0xffffffff,rec.status,
        rec.surface_id or 0,*[value or 0 for value in rec.vertex_ids],rec.surface_code or 0,
        *[bits(float(value)) for value in row_projection.point],
        *[bits(float(value)) for value in row_projection.reference_position]]
    row_state=SupportPredictionState(tuple(PredictionWheel(
        ((.25 if i&1 else -.25),0.,(.25 if i&2 else -.25)),(8.,7.,8.),.5)
        for i in range(4)),(8.,7.,8.),(.1,0.,-.2),context=0,fallback_surface=9,support_count=3)
    row_support=predict_support(row_state,lambda q:project_track_surface(
        row_world,q,normal_seed=(.3,.8,-.2)))
    support_values=[row_support.state.support_count]
    for wheel in row_support.state.wheels:
        rec=wheel.record
        support_values.extend((int(wheel.contact),bits(wheel.support_delta),wheel.surface_class,
            *[bits(float(v)) for v in wheel.world_point],rec.sector&0xffffffff,
            rec.group&0xffffffff,rec.status,rec.surface_id or 0,
            *[v or 0 for v in rec.vertex_ids],rec.surface_code or 0,
            *wheel.query_tail))
    for q in row_support.queries:
        support_values.extend((q.context,*[bits(float(v)) for v in q.point],
                               *[bits(float(v)) for v in q.previous_world]))
    expected.append((int(row_found),bytes(row_query),bytes(row_point),projection_values,support_values))
    lines.append(f'5 0 0 0 0 8 8 {row_seed}')
    result=subprocess.run([str(runner)],input='\n'.join('0 '+line for line in lines)+'\n',
        capture_output=True,text=True,check=True,timeout=60)
    output=result.stdout.splitlines()
    if len(output)!=len(expected):raise AssertionError(('row count',len(output),len(expected)))
    maximum=0.
    for index,(line,(found,query,point,projection_values,support_values)) in enumerate(zip(output,expected)):
        values=list(map(int,line.split()))
        if len(values)!=272:raise AssertionError(('output shape',index,len(values)))
        actual_found=values[0];actual_query=bytes(values[1:69])
        actual_point=struct.pack('<3I',*values[69:72])
        if actual_found!=found or actual_query!=query:
            raise AssertionError(('query/return',index,actual_found,found,
                next((i for i,(a,b) in enumerate(zip(actual_query,query)) if a!=b),None)))
        a=struct.unpack('<3f',actual_point);b=struct.unpack('<3f',point)
        for axis,(left,right) in enumerate(zip(a,b)):
            error=abs(left-right);maximum=max(maximum,error)
            if axis!=1 and left!=right:raise AssertionError(('point component',index,axis,left,right))
            if error>2e-6:raise AssertionError(('height',index,left,right,error))
        if values[72:87]!=projection_values:
            raise AssertionError(('support projection',index,values[72:87],projection_values))
        if values[87:]!=support_values:
            raise AssertionError(('support predictor on track',index,values[87:],support_values))
    return {'cases':len(expected),'row_mode_stack_seed_case':1,'return_and_query':'exact','point':'exact except height <= 2e-6',
        'support_projection':'exact surface record, projected point, and reference point',
        'support_predictor':'exact contact state, deltas, records, and ordered query points',
        'maximum_height_absolute_error':maximum,
        'scope':'native 0x42e010 composition over bounded synthetic track worlds; original 0x42e760 lookup and triangle plane path, row-mode seed explicit'}


if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('runner');parser.add_argument('--cases',type=int,default=1200)
    args=parser.parse_args();print(json.dumps(verify(args.runner,args.cases)))
