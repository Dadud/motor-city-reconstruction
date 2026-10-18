// Instrument only the pinned private reference-client copy. No credentials read.
// MCO_BLOCKED_ROOT is supplied as a JSON string by the caller before this source.
if (Process.arch !== 'ia32') throw new Error('MCO reference must be x86');
const retained = [];
const guardHooks = [];
const counts = {};
let emitted = 0;
function report(payload) { if (emitted++ < 240) send(payload); }
function block(module, name, result, types) {
    const address = module.getExportByName(name);
    const callback = new NativeCallback(function () {
        counts[name] = (counts[name] || 0) + 1;
        if (counts[name] <= 4) report({kind:'blocked_api', name});
        return result;
    }, 'int', types);
    retained.push(callback); Interceptor.replace(address, callback); guardHooks.push(name);
}
const sockets = Module.load('ws2_32.dll');
block(sockets,'connect',-1,['pointer','pointer','int']);
block(sockets,'WSAConnect',-1,['pointer','pointer','int','pointer','pointer','pointer','pointer']);
block(sockets,'sendto',-1,['pointer','pointer','int','int','pointer','int']);
block(sockets,'WSASendTo',-1,['pointer','pointer','uint','pointer','uint','pointer','int','pointer','pointer']);
block(sockets,'WSAIoctl',-1,['pointer','uint','pointer','uint','pointer','uint','pointer','pointer','pointer']);
const kernel = Process.getModuleByName('kernel32.dll');
block(kernel,'CreateProcessA',0,['pointer','pointer','pointer','pointer','int','uint','pointer','pointer','pointer','pointer']);
block(kernel,'CreateProcessW',0,['pointer','pointer','pointer','pointer','int','uint','pointer','pointer','pointer','pointer']);
// Deny attempts to create/modify files through an absolute original-install path.
const blockedRoot = MCO_BLOCKED_ROOT.toLowerCase().replaceAll('/', '\\');
for (const wide of [false,true]) {
    const name = wide ? 'CreateFileW' : 'CreateFileA';
    const absent = wide ? Memory.allocUtf16String('mco-probe-denied-original-write-absent') : Memory.allocUtf8String('mco-probe-denied-original-write-absent');
    retained.push(absent);
    Interceptor.attach(kernel.getExportByName(name), {onEnter(args) {
        try {
            const path = (wide ? args[0].readUtf16String() : args[0].readCString()).toLowerCase().replaceAll('/', '\\').replace(/^\\\\\?\\/, '');
            this.filePath=path; this.caller=this.returnAddress.toString();
            const access=args[1].toUInt32(), disposition=args[4].toUInt32();
            if ((path===blockedRoot || path.startsWith(blockedRoot+'\\')) && ((access&0x500d0006)!==0 || disposition!==3)) {
                args[0]=absent;args[1]=ptr(0);args[4]=ptr(3);
                report({kind:'blocked_original_write',name});
            }
        } catch (_) { /* Invalid arguments retain the target's native failure. */ }
    },onLeave(result) {
        if(result.toInt32()===-1 && this.filePath) report({kind:'file_open_failed',name,path:this.filePath,caller:this.caller,error:this.lastError});
    }});
    guardHooks.push(name);
}
const registry=Module.load('advapi32.dll');
for (const wide of [false,true]) {
    const name=wide?'RegOpenKeyExW':'RegOpenKeyExA';
    Interceptor.attach(registry.getExportByName(name),{onEnter(args) {
        try {this.key=wide?args[1].readUtf16String():args[1].readCString();this.access=args[3].toUInt32();this.caller=this.returnAddress.toString();}catch(_){}
    },onLeave(result) {
        if(this.key)report({kind:'registry_open',name,key:this.key,access:this.access,result:result.toUInt32(),caller:this.caller});
    }});
}
const user = Module.load('user32.dll');
for (const wide of [false,true]) {
    const name=wide?'MessageBoxW':'MessageBoxA';
    const callback=new NativeCallback(function(window,message,title,flags) {
        let text='unreadable';
        try {text=(wide?message.readUtf16String(256):message.readCString(256)).split('\0')[0];}catch(_){}
        report({kind:'target_dialog',name,text,caller:this.returnAddress.toString(),modules:Process.enumerateModules().slice(0,3).map(m=>({name:m.name,base:m.base.toString(),size:m.size}))});return 2;
    },'int',['pointer','pointer','pointer','uint']);
    retained.push(callback);Interceptor.replace(user.getExportByName(name),callback);
}
const main=Process.mainModule;
for (const [name,address] of Object.entries({entry:0x69dda2,startup:0x6bfa10,diagnostic:0x6bedf0,
    mouse:0x6ef890,keyboard:0x6f0200,layout:0x6f09f0,numlock:0x6bfc80,cleanup:0x6bf410})) {
    const target=main.base.add(address-0x400000);
    Interceptor.attach(target,{onEnter() {
        counts[name]=(counts[name]||0)+1;
        if(counts[name]<=8)report({kind:'routine_enter',name,rva:'0x'+(address-0x400000).toString(16)});
    }});
}
Interceptor.attach(kernel.getExportByName('ExitProcess'),{onEnter(args){report({kind:'target_exit',code:args[0].toUInt32()});}});
Process.setExceptionHandler(details=>{report({kind:'target_exception',type:details.type,address:details.address.toString()});return false;});
report({kind:'guard_ready',hooks:guardHooks,architecture:Process.arch,pointer_size:Process.pointerSize,
    limits:'API-level network/child/write guards; modified dialogs; not OS network isolation or gameplay acceptance'});
