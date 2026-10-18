// Run only against the separately built, owned frida_canary test executable.
const symbol = Process.mainModule.enumerateExports().find(
    entry => /_?mco_trace_canary$/.test(entry.name));
if (!symbol) throw new Error('canary export missing');
let sent = 0;
Interceptor.attach(symbol.address, {
    onEnter(args) { this.input = args[0].toUInt32(); },
    onLeave(result) {
        if (sent++ < 4) send({kind: 'mco-hook-canary', arch: Process.arch,
            pointer_size: Process.pointerSize, input: this.input, output: result.toUInt32()});
    }
});
