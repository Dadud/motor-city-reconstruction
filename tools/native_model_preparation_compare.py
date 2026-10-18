"""Compare full FCE byte images and native preparation primitive outputs."""
import argparse
import json
import struct
import subprocess
from pathlib import Path
from tools.model_preparation_oracle import cases,expected


def verify(executable):
    records=list(cases());lines=[]
    for op,part,scales,b,ref in records:
        bits=struct.unpack('<3I',struct.pack('<3f',*scales))
        lines.append(' '.join(map(str,(op,part,*bits,b.hex(),ref.hex() or '-'))))
    process=subprocess.run([str(executable)],input='\n'.join(lines)+'\n',text=True,capture_output=True,check=True)
    output=process.stdout.splitlines()
    if len(output)!=len(records):raise AssertionError('comparison output count')
    counts={'h':0,'s':0,'a':0}
    for index,(record,line) in enumerate(zip(records,output)):
        status,data=line.split();observed=(int(status),bytes.fromhex(data) if data!='-' else b'')
        if observed!=expected(*record):raise AssertionError((index,record[:3],'native mismatch'))
        counts[record[0]]+=1
    return {'cases':counts,'maximum_absolute_error':0,'comparison':'exact output and full mutation image bytes'}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('executable',type=Path)
    print(json.dumps(verify(p.parse_args().executable)))
