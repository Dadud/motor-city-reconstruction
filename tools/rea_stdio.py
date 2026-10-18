"""Small synchronous client for an isolated, version-pinned REA stdio session."""
import json
from pathlib import Path
import queue
import subprocess
import threading
import time

class ReaSession:
    def __init__(self,package_root,output,cwd):
        self.output=Path(output);self.counter=0;self.messages=queue.Queue()
        package_root=Path(package_root)
        self.package=json.loads((package_root/'package.json').read_text())
        self.stderr=(self.output/'rea-server.log').open('w',encoding='utf-8')
        self.process=subprocess.Popen(['node',str(package_root/'scripts/rea.mjs'),'--mcp'],
            cwd=cwd,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=self.stderr,
            text=True,encoding='utf-8',bufsize=1)
        def read():
            try:
                for line in self.process.stdout:
                    try:self.messages.put(json.loads(line))
                    except json.JSONDecodeError:continue
            finally:self.messages.put(None)
        threading.Thread(target=read,daemon=True).start()
        try:
            self.request('initialize',{'protocolVersion':'2024-11-05','capabilities':{},
                'clientInfo':{'name':'mco-recovery-runtime','version':'1'}})
            self.send({'jsonrpc':'2.0','method':'notifications/initialized'})
        except BaseException:
            self.close()
            raise
    def send(self,document):
        self.process.stdin.write(json.dumps(document)+'\n');self.process.stdin.flush()
    def request(self,method,params,timeout=45):
        self.counter+=1;identifier=self.counter
        self.send({'jsonrpc':'2.0','id':identifier,'method':method,'params':params})
        deadline=time.monotonic()+timeout
        while True:
            response=self.messages.get(timeout=max(0,deadline-time.monotonic()))
            if response is None:raise RuntimeError('REA stdio session closed')
            if response.get('id')!=identifier:continue
            (self.output/f'{identifier:03d}-{method.replace("/","-")}.json').write_text(json.dumps(response,indent=2)+'\n')
            if response.get('error'):raise RuntimeError(response['error'].get('message','REA RPC failed'))
            return response['result']
    def call(self,name,arguments):
        result=self.request('tools/call',{'name':name,'arguments':arguments})
        value=result.get('structuredContent')
        if value is None:
            value=next((json.loads(c['text']) for c in result.get('content',[]) if c['type']=='text'),{})
        if result.get('isError') or value.get('error'):
            error=value.get('error',{})
            raise RuntimeError(f'{name}: {error.get("code","tool_error")}: {error.get("message","operation failed")}')
        return value
    def close(self):
        if self.process.poll() is None:
            self.process.stdin.close()
            try:self.process.wait(timeout=10)
            except subprocess.TimeoutExpired:self.process.terminate();self.process.wait(timeout=5)
        self.stderr.close()

def observation(document):
    if 'evidence' in document:document=document['evidence']
    if 'normalized_result' in document:return document['normalized_result']
    if 'result' in document:return document['result']
    return document
