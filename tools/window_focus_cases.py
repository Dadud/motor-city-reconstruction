"""Original execution fixtures for the window focus and input-hook handler."""
import struct

BASE, SIZE, ACTIVE, KEYS = 0xaca8f0, 0x530, 0xacae2c, 0x8c8648
DEF, UNHOOK, MODULE, SET_HOOK = 0x7000a000, 0x7000a100, 0x7000a200, 0x7000a300
RESULT = 0x71003000


def fixture_rows():
    """Yield diverse finite global/key images and all activation branches."""
    rows = []
    cases = [
        # Dispatch gate rejection: the default result and all state survive.
        (0, 7, 0x86, 1, 0x1234, 1, 1, 0x1111, 0x2222),
        (1, 8, 0x86, 1, 0x1234, 1, 1, 0x1111, 0x2222),
        # Deactivation, minimized activation, including all hook-presence combinations.
        (1, 7, 0x86, 0, 0x1234, 1, 1, 0x1111, 0x2222),
        (1, 7, 0x86, 0x00010001, 0x1234, 1, 1, 0, 0x2222),
        (1, 7, 0x86, 1, 0x1234, 1, 1, 0x1111, 0),
        (1, 7, 0x86, 0, 0x1234, 1, 0, 0x1111, 0x2222),
        # Activation with hooks disabled, existing hooks, or install failures.
        (1, 7, 0x86, 1, 0x1234, 0, 0, 0, 0),
        (1, 7, 0x86, 1, 0x1234, 1, 0, 0x1111, 0x2222),
        (1, 7, 0x86, 2, 0x1234, 1, 1, 0, 0),
        (1, 7, 0x86, 3, 0x1234, 1, 1, 0, 0x2222),
        (1, 7, 0x86, 1, 0x1234, 1, 1, 0, 0),
        (1, 7, 0x86, 0x00010001, 0x1234, 0, 1, 0, 0),
        # Exercise both low-word activation codes and varied high-word flags.
        *((1, 7, 0x86, code, 0x1234, 1, 1, 0x1111, 0x2222)
          for code in (1, 2, 0x10000, 0x10001, 0xffff, 0xffff0001)),
    ]
    for index, (enabled, window, message, wparam, lparam, hooks, active,
                keyboard, mouse) in enumerate(cases):
        globals_image = bytearray((index * 19 + j * 37 + 11) & 255 for j in range(SIZE))
        struct.pack_into('<I', globals_image, 0x4c0, 7)
        struct.pack_into('<I', globals_image, 0x510, hooks)
        active_image = struct.pack('<I', active)
        keys = bytes((index * 13 + j * 23 + 5) & 255 for j in range(128))
        old_result = (0xaabbccdd ^ index) & 0xffffffff
        module_handle = 0x12340000 + index * 0x100
        default_result = 0xd3f00000 ^ index
        keyboard_result = 0x10100000 + index
        mouse_result = 0x20200000 + index
        inputs = [enabled, window, message, wparam, lparam, old_result,
                  module_handle, default_result, keyboard_result, mouse_result,
                  *globals_image, *active_image, *keys]
        rows.append((inputs, dict(module=module_handle, default=default_result,
                                  keyboard=keyboard_result, mouse=mouse_result)))
    return rows


def capture(oracle):
    """Capture API calls and complete state after running original 0x584070."""
    from unicorn import UC_HOOK_CODE

    cpu, reg = oracle.cpu, oracle.reg
    iats = (0x83b380, 0x83b400, 0x83b264, 0x83b408)
    stubs = (DEF, UNHOOK, MODULE, SET_HOOK)
    saved = {address: bytes(cpu.mem_read(address, 4)) for address in iats}
    cleanups = (0x10, 4, 4, 0x10)
    for iat, stub, cleanup in zip(iats, stubs, cleanups):
        cpu.mem_write(iat, struct.pack('<I', stub))
        cpu.mem_write(stub, b'\xc2' + struct.pack('<H', cleanup))

    events, script = [], {}

    def read(address):
        return struct.unpack('<I', cpu.mem_read(address, 4))[0]

    def hook_callback(cpu_, address, size, user):
        if address not in stubs:
            return
        # Unicorn's code hook runs before the stub's RET instruction and after
        # the caller has pushed its args; ESP points at the return address.
        stack = cpu.reg_read(reg.UC_X86_REG_ESP) + 4
        kind = stubs.index(address)
        if kind == 0:  # DefWindowProcA(HWND, message, wParam, lParam)
            args = struct.unpack('<4I', cpu.mem_read(stack, 16))
            result = script['default']
        elif kind == 1:  # UnhookWindowsHookEx(HHOOK)
            args = (read(stack),)
            result = 1
        elif kind == 2:  # GetModuleHandleA(NULL)
            args = (read(stack),)
            result = script['module']
        else:  # SetWindowsHookExA(id, callback, module, thread)
            args = struct.unpack('<4I', cpu.mem_read(stack, 16))
            result = script['keyboard'] if args[0] == 2 else script['mouse']
        globals_now = bytes(cpu.mem_read(BASE, SIZE))
        active_now = bytes(cpu.mem_read(ACTIVE, 4))
        keys_now = bytes(cpu.mem_read(KEYS, 128))
        if kind == 1:
            # The caller uses a stack local for HHOOK and clears its global
            # only after UnhookWindowsHookEx returns.
            hooks_now = bytes(cpu.mem_read(BASE + 0x508, 8))
        else:
            hooks_now = globals_now[0x508:0x510]
        row = [kind, *args, *([0] * (4-len(args))), result,
               struct.unpack('<I', active_now)[0],
               *struct.unpack('<2I', hooks_now), keys_now[0], keys_now[-1]]
        events.append(row)
        cpu.reg_write(reg.UC_X86_REG_EAX, result)

    hook = cpu.hook_add(UC_HOOK_CODE, hook_callback,
                        begin=min(stubs), end=max(stubs))
    output = []
    try:
        for inputs, callbacks in fixture_rows():
            enabled, window, message, wparam, lparam, old_result = inputs[:6]
            module, default = callbacks['module'], callbacks['default']
            keyboard, mouse = callbacks['keyboard'], callbacks['mouse']
            global_words = inputs[10:10 + SIZE]
            active_words = inputs[10 + SIZE:10 + SIZE + 4]
            key_words = inputs[10 + SIZE + 4:]
            cpu.mem_write(BASE, bytes(global_words))
            cpu.mem_write(ACTIVE, bytes(active_words))
            cpu.mem_write(KEYS, bytes(key_words))
            # When a hook handle exists, its target is accessed as a global
            # at BASE+0x508; the patterned image already supplies it.
            cpu.mem_write(RESULT, struct.pack('<I', old_result))
            script.update(module=module, default=default, keyboard=keyboard, mouse=mouse)
            events.clear()
            oracle.call(0x584070,
                        (enabled, window, message, wparam, lparam, RESULT),
                        cleanup=b'', instruction_limit=100_000)
            final = [cpu.reg_read(reg.UC_X86_REG_EAX), read(RESULT),
                     *cpu.mem_read(BASE, SIZE), *cpu.mem_read(ACTIVE, 4),
                     *cpu.mem_read(KEYS, 128), len(events),
                     *(item for event in events for item in event)]
            output.append(dict(input=inputs, output=final))
    finally:
        cpu.hook_del(hook)
        for address, data in saved.items():
            cpu.mem_write(address, data)
        if hasattr(cpu, 'ctl_flush_tb'):
            cpu.ctl_flush_tb()
    return output
