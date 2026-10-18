"""Add evidenced callable boundaries without editing retained enumerations.

Supplements establish entry identity only. They do not imply translation,
verification, classification or a library disposition.
"""
import copy
import hashlib
import json
from pathlib import Path
import re

FILE='function-supplements.json'
ADDRESS=re.compile(r'0x[0-9a-f]+')

def entries(directory,target):
    path=Path(directory)/FILE
    if not path.exists():return [],None
    data=path.read_bytes();document=json.loads(data)
    if document.get('schema')!=1 or not isinstance(document.get('modules'),dict):
        raise ValueError('invalid function supplement schema')
    root=Path(directory).parent.parent
    for digest,rows in document['modules'].items():
        if not re.fullmatch('[0-9a-f]{64}',digest) or not isinstance(rows,list):
            raise ValueError('invalid function supplement target')
        seen=set();ranges=[]
        for row in rows:
            if not isinstance(row,dict) or not all(row.get(k) for k in ('address','end_exclusive','name','evidence','sources')):
                raise ValueError('incomplete function supplement entry')
            if any(not isinstance(row[k],str) or not ADDRESS.fullmatch(row[k]) for k in ('address','end_exclusive')):
                raise ValueError('invalid function supplement address')
            if any(not isinstance(row[k],str) or not row[k].strip() for k in ('name','evidence')):
                raise ValueError('function supplement name/evidence text required')
            start,end=int(row['address'],16),int(row['end_exclusive'],16)
            if not 0<start<end<=0x100000000 or start in seen:
                raise ValueError('duplicate or invalid function supplement range')
            if any(start<other_end and other_start<end for other_start,other_end in ranges):
                raise ValueError('overlapping function supplement ranges')
            seen.add(start);ranges.append((start,end))
            if not isinstance(row.get('direct_callees'),list) or any(not isinstance(v,str) or not ADDRESS.fullmatch(v) for v in row['direct_callees']):
                raise ValueError('invalid function supplement callees')
            if not isinstance(row['sources'],list):raise ValueError('function supplement sources list required')
            for source in row['sources']:
                if not isinstance(source,str):raise ValueError('invalid supplement source')
                relative=Path(source)
                if relative.is_absolute() or '..' in relative.parts or not (root/relative).is_file():
                    raise ValueError('missing or unsafe function supplement source')
    rows=sorted(document['modules'].get(target,[]),key=lambda row:int(row['address'],16))
    return rows,hashlib.sha256(data).hexdigest()

def _rows(document,directory,count):
    if len(document['functions'])!=count:raise ValueError('incomplete base enumeration before supplement')
    existing={row['address'].split(':')[0]+':'+hex(int(row['address'].split(':')[-1],16)) if ':' in row['address'] else hex(int(row['address'],16)) for row in document['functions']}
    if len(existing)!=count:raise ValueError('duplicate base enumeration before supplement')
    rows,digest=entries(directory,document['target_sha256'])
    if any(hex(int(row['address'],16)) in existing for row in rows):
        raise ValueError('function supplement conflicts with base entry')
    return rows,digest

def enumeration(document,directory):
    rows,digest=_rows(document,directory,document['procedure_count'])
    if not rows:return document
    result=copy.deepcopy(document)
    result['base_procedure_count']=document['procedure_count']
    result['supplemental_entries']=len(rows);result['supplement_sha256']=digest
    result['procedure_count']+=len(rows)
    result['functions'].extend(dict(address=hex(int(row['address'],16)),name=row['name'],boundary_origin='supplement',boundary_evidence=row['evidence']) for row in rows)
    return result

def module(document,directory):
    rows,digest=_rows(document,directory,document['summary']['function_entries'])
    if not rows:return document
    result=copy.deepcopy(document)
    result['provenance']['supplement_sha256']=digest
    result['provenance']['base_function_entries']=document['summary']['function_entries']
    result['summary']['supplemental_entries']=len(rows)
    result['summary']['function_entries']+=len(rows)
    if 'internal_entries' in result['summary']:result['summary']['internal_entries']+=len(rows)
    result['summary'].setdefault('decompilation',{})['not-exported-supplement']=len(rows)
    for row in rows:
        result['functions'].append(dict(address=hex(int(row['address'],16)),name=row['name'],external=False,thunk=False,
            body_bytes=int(row['end_exclusive'],16)-int(row['address'],16),direct_callees=[hex(int(value,16)) for value in row['direct_callees']],
            decompilation='not-exported-supplement',translation='unreviewed',boundary_origin='supplement',boundary_evidence=row['evidence']))
    return result
