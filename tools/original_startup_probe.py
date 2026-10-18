"""Observe a private copied MCO client through a fresh REA session before resuming."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import signal
import time
from tools.rea_stdio import ReaSession,observation
from tools.recovery_export import ROOT,private_output
from client.dyno import _SOURCE_SHA256

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--stage',type=Path,required=True)
    parser.add_argument('--original-root',type=Path,required=True)
    parser.add_argument('--rea-root',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--seconds',type=int,default=8,choices=range(1,31),metavar='1..30')
    args=parser.parse_args()
    stage=private_output(args.stage);output=private_output(args.output)
    if output.exists():parser.error('output must be absent')
    executable=stage/'mcity.exe'
    digest=hashlib.sha256(executable.read_bytes()).hexdigest()
    if digest!=_SOURCE_SHA256:parser.error('stage must contain the exact verified mcity.exe')
    if stage==args.original_root.resolve():parser.error('original installation cannot be the stage')
    output.mkdir(parents=True)
    script=ROOT/'tools/fixtures/mco_offline_startup.js'
    source='const MCO_BLOCKED_ROOT = '+json.dumps(str(args.original_root.resolve()))+';\n'+script.read_text()
    (output/'probe-source.js').write_text(source,encoding='utf-8')
    session=ReaSession(args.rea_root,output,stage)
    session_id=None;pid=None;resumed=False;ready=False;status={};cleanup=None;target_stop=None
    try:
        started=observation(session.call('start_frida_session',{'mode':'spawn','program':str(executable)}))
        session_id=started['session_id'];pid=started['pid']
        session.call('load_frida_script',{'session_id':session_id,'source_kind':'inline','source':source})
        status=observation(session.call('frida_session_status',{'session_id':session_id}))
        ready=any(m.get('payload',{}).get('kind')=='guard_ready' for m in status.get('messages',[]))
        if not ready:raise RuntimeError('guard readiness unobserved; refusing target resume')
        session.call('resume_frida_session',{'session_id':session_id});resumed=True
        time.sleep(args.seconds)
        status=observation(session.call('frida_session_status',{'session_id':session_id}))
    finally:
        # REA detaches but does not own target lifetime. Stop our owned copy
        # before releasing its hooks, including on a load/readiness failure.
        if pid is not None:
            try:
                os.kill(pid,signal.SIGTERM)
                target_stop={"signal_sent":True}
            except ProcessLookupError:
                target_stop={"already_exited":True}
            except OSError as error:
                target_stop={"error":str(error)}
        if session_id is not None:
            try:cleanup=session.call('close_frida_session',{'session_id':session_id})
            except Exception as error:cleanup={'error':str(error)}
        session.close()
        messages=[m.get('payload',{}) for m in status.get('messages',[]) if m.get('type')=='send']
        summary=dict(target_sha256=digest,rea_version=session.package['version'],
            guard_ready=ready,resumed=resumed,duration_seconds=args.seconds,
            routines=[m['name'] for m in messages if m.get('kind')=='routine_enter'],
            dialogs=[m.get('text') for m in messages if m.get('kind')=='target_dialog'],
            blocked_api_calls=[m.get('name') for m in messages if m.get('kind')=='blocked_api'],
            scope='controlled copied-original reference run; API guards/modified dialogs, not reconstructed-client or network-isolation acceptance',
            script_sha256=hashlib.sha256(source.encode()).hexdigest(),cleanup=cleanup,target_stop=target_stop)
        (output/'summary.json').write_text(json.dumps(summary,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in summary.items() if k not in ('dialogs','cleanup')},indent=2))

if __name__=='__main__':main()
