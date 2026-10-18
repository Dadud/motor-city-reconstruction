"""Secondary Capstone scan of entry-sized byte windows, not verified function bodies."""
import argparse
import json
from pathlib import Path
from capstone import Cs,CS_ARCH_X86,CS_MODE_32
from capstone.x86 import X86_OP_IMM,X86_OP_MEM
from tools.function_triage import load_modules,load_image,read_range,CLIENT
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('original',type=Path)
parser.add_argument('--output',type=Path,default=Path('build/recovery/action-table-references.json'))
args=parser.parse_args()
root=Path(__file__).resolve().parents[1]/'docs/recovery'
doc=next(d for d in load_modules(root) if d['target_sha256']==CLIENT)
image=load_image(args.original,CLIENT)
cs=Cs(CS_ARCH_X86,CS_MODE_32);cs.detail=True
hits={};coverage={'entries':0,'unmapped':0,'decoded_bytes':0,'window_bytes':0}
for e in doc['functions']:
 if e['external'] or not e['body_bytes']:continue
 start=int(e['address'],16);size=e['body_bytes'];coverage['entries']+=1;coverage['window_bytes']+=size
 try:code=read_range(*image,start,start+size)
 except ValueError:coverage['unmapped']+=1;continue
 for ins in cs.disasm(code,start):
  coverage['decoded_bytes']+=ins.size
  for op in ins.operands:
   value=op.imm&0xffffffff if op.type==X86_OP_IMM else op.mem.disp&0xffffffff if op.type==X86_OP_MEM else None
   if value is not None and 0xb36594<=value<0xb36898:
    hits[ins.address]={'instruction':hex(ins.address),'window_entry':e['address'],'mnemonic':ins.mnemonic,'operands':ins.op_str,'literal':hex(value),'kind':'immediate' if op.type==X86_OP_IMM else 'memory-displacement','access':op.access}
result={'target_sha256':CLIENT,'range':['0xb36594','0xb36898'],'coverage':coverage,'references':list(hits.values()),'limitations':['Secondary Capstone evidence, not REA output. Each window starts at a retained entry and uses its body byte count as length; contiguity and ownership are not established. Gapped bodies can cause omissions and overlaps.', 'Decoded bytes are window samples, not unique owned code coverage. Use REA complete function-body AddressSets and references before drawing function-level absence conclusions.','Only literal immediates and memory displacements; computed addresses and indirect writes are not resolved.','The examined range covers 65 handler words and both 256-byte maps; aliased high handler indices can extend beyond it.']}
args.output.parent.mkdir(parents=True,exist_ok=True)
args.output.write_text(json.dumps(result,indent=2))
print(json.dumps({'target_sha256':CLIENT,'coverage':coverage,'literal_references':len(hits),'output':str(args.output)},indent=2))
