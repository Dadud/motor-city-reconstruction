"""Run every implemented recovery cell's native comparison harness.

The native workflow used to carry two hand-written CI steps per recovered
routine. Cells now carry a manifest instead, so CI asks for the whole set and
the manifests decide what runs. A scaffolded cell is skipped: it has no
comparison corpus yet, and pretending otherwise would turn a missing harness
into a green build.
"""
import argparse
from pathlib import Path
import json
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
CELLS = ROOT / 'docs' / 'recovery' / 'cells'
sys.path.insert(0, str(ROOT))

from tools.function_cell import load_manifest, manifests  # noqa: E402
from tools.cell_corpus import DEFAULT, load_corpus, cases_for, verify as compare  # noqa: E402


def locate(directory, identifier, platform):
    suffix = '.exe' if platform == 'win32' else ''
    for candidate in (directory / f'mco_{identifier}_compare{suffix}',
                      directory / 'Release' / f'mco_{identifier}_compare{suffix}'):
        if candidate.is_file():
            return candidate
    return None


def verify(directory, platform, corpus=None):
    results = []
    document = load_corpus(corpus or DEFAULT)
    for path in manifests():
        manifest = load_manifest(path)
        if manifest.get('status', 'scaffolded') != 'implemented':
            results.append(dict(id=manifest['id'], skipped='scaffolded'))
            continue
        runner = locate(directory, manifest['id'], platform)
        if runner is None:
            raise SystemExit(f"{manifest['id']}: built comparison harness not found")
        output = compare(runner, cases_for(manifest['id'], document), manifest['id'])
        if not output.get('cases') or output.get('exact_output_bits') is not True:
            raise SystemExit(f"{manifest['id']}: comparison returned no verified cases")
        results.append(dict(id=manifest['id'], output=output))
    from tools.native_record_lifecycle_compare import compare as compare_lifecycle
    sequence = locate(directory, 'record_lifecycle', platform)
    if sequence is None:
        raise SystemExit('record_lifecycle: built comparison harness not found')
    from tools.native_record_selection_lifecycle_compare import compare as compare_selection
    selection = locate(directory, 'record_selection_lifecycle', platform)
    if selection is None:
        raise SystemExit('record_selection_lifecycle: built comparison harness not found')
    from tools.native_record_cycle_lifecycle_compare import compare as compare_cycle
    cycle = locate(directory, 'record_cycle_lifecycle', platform)
    if cycle is None:
        raise SystemExit('record_cycle_lifecycle: built comparison harness not found')
    from tools.native_input_key_lifecycle_compare import compare as compare_keys
    keys = locate(directory, 'input_key_lifecycle', platform)
    if keys is None:
        raise SystemExit('input_key_lifecycle: built comparison harness not found')
    from tools.native_input_queue_lifecycle_compare import compare as compare_queue
    queue = locate(directory, 'input_queue_lifecycle', platform)
    if queue is None:
        raise SystemExit('input_queue_lifecycle: built comparison harness not found')
    from tools.native_free_camera_lifecycle_compare import compare as compare_camera
    camera = locate(directory, 'free_camera_lifecycle', platform)
    if camera is None:
        raise SystemExit('free_camera_lifecycle: built comparison harness not found')
    from tools.native_window_camera_lifecycle_compare import compare as compare_window_camera
    window_camera = locate(directory, 'window_camera_lifecycle', platform)
    if window_camera is None:
        raise SystemExit('window_camera_lifecycle: built comparison harness not found')
    from tools.native_window_mouse_lifecycle_compare import compare as compare_window_mouse
    window_mouse = locate(directory, 'window_mouse_lifecycle', platform)
    if window_mouse is None:
        raise SystemExit('window_mouse_lifecycle: built comparison harness not found')
    from tools.native_input_device_information_lifecycle_compare import compare as compare_information
    information = locate(directory, 'input_device_information_lifecycle', platform)
    if information is None:
        raise SystemExit('input_device_information_lifecycle: built comparison harness not found')
    from tools.native_input_device_lifetime_lifecycle_compare import compare as compare_lifetime
    lifetime = locate(directory, 'input_device_lifetime_lifecycle', platform)
    if lifetime is None:
        raise SystemExit('input_device_lifetime_lifecycle: built comparison harness not found')
    from tools.native_input_device_session_compare import compare as compare_session
    session = locate(directory, 'input_device_session', platform)
    if session is None:
        raise SystemExit('input_device_session: built comparison harness not found')
    from tools.native_input_callback_dispatch_lifecycle_compare import compare as compare_dispatch
    dispatch = locate(directory, 'input_callback_dispatch_lifecycle', platform)
    if dispatch is None:
        raise SystemExit('input_callback_dispatch_lifecycle: built comparison harness not found')
    from tools.native_input_default_key_lifecycle_compare import compare as compare_default_key
    default_key = locate(directory, 'input_default_key_lifecycle', platform)
    if default_key is None:
        raise SystemExit('input_default_key_lifecycle: built comparison harness not found')
    from tools.native_input_action_session_compare import compare as compare_action_session
    action_session = locate(directory, 'input_action_session', platform)
    if action_session is None:
        raise SystemExit('input_action_session: built comparison harness not found')
    from tools.native_input_console_lifecycle_compare import compare as compare_console
    console = locate(directory, 'input_console_lifecycle', platform)
    if console is None:
        raise SystemExit('input_console_lifecycle: built comparison harness not found')
    from tools.native_cleanup_registry_lifecycle_compare import compare as compare_cleanup_registry
    cleanup_registry = locate(directory, 'cleanup_registry_lifecycle', platform)
    if cleanup_registry is None:
        raise SystemExit('cleanup_registry_lifecycle: built comparison harness not found')
    from tools.native_input_keyboard_layout_lifecycle_compare import compare as compare_keyboard_layout
    keyboard_layout = locate(directory, 'input_keyboard_layout_lifecycle', platform)
    if keyboard_layout is None:
        raise SystemExit('input_keyboard_layout_lifecycle: built comparison harness not found')
    from tools.native_startup_lifecycle_compare import compare as compare_startup
    startup = locate(directory, 'startup_lifecycle', platform)
    if startup is None:
        raise SystemExit('startup_lifecycle: built comparison harness not found')
    from tools.native_input_mouse_runtime_lifecycle_compare import compare as compare_mouse_runtime
    mouse_runtime=locate(directory,'input_mouse_runtime_lifecycle',platform)
    if mouse_runtime is None:
        raise SystemExit('input_mouse_runtime_lifecycle: built comparison harness not found')
    return dict(cells=len(results),
                compared=sum('output' in r for r in results), results=results,
                startup_lifecycle=compare_startup(startup, corpus or DEFAULT, document),
                input_mouse_runtime_lifecycle=compare_mouse_runtime(mouse_runtime,corpus or DEFAULT,document),
                input_keyboard_layout_lifecycle=compare_keyboard_layout(keyboard_layout, corpus or DEFAULT, document),
                cleanup_registry_lifecycle=compare_cleanup_registry(cleanup_registry, corpus or DEFAULT, document),
                input_console_lifecycle=compare_console(console, corpus or DEFAULT, document),
                input_action_session_lifecycle=compare_action_session(action_session, corpus or DEFAULT, document),
                input_default_key_lifecycle=compare_default_key(default_key, corpus or DEFAULT, document),
                input_callback_dispatch_lifecycle=compare_dispatch(dispatch, corpus or DEFAULT, document),
                input_device_session_lifecycle=compare_session(session, corpus or DEFAULT, document),
                input_device_lifetime_lifecycle=compare_lifetime(lifetime, corpus or DEFAULT, document),
                input_device_information_lifecycle=compare_information(information, corpus or DEFAULT, document),
                lifecycle=compare_lifecycle(sequence, corpus or DEFAULT, document),
                selection_lifecycle=compare_selection(selection, corpus or DEFAULT, document),
                cycle_lifecycle=compare_cycle(cycle, corpus or DEFAULT, document),
                input_lifecycle=compare_keys(keys, corpus or DEFAULT, document),
                input_queue_lifecycle=compare_queue(queue, corpus or DEFAULT, document),
                free_camera_lifecycle=compare_camera(camera, corpus or DEFAULT, document),
                window_camera_lifecycle=compare_window_camera(window_camera, corpus or DEFAULT, document),
                window_mouse_lifecycle=compare_window_mouse(window_mouse, corpus or DEFAULT, document))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory', nargs='?', type=Path, default=Path('build/native'))
    parser.add_argument('--corpus', type=Path,
                        help='fresh original-execution corpus; defaults to committed cases')
    parser.add_argument('--original', type=Path,
                        help='capture and compare against the hash-checked executable now')
    args = parser.parse_args()
    platform = sys.platform
    if args.original and args.corpus:
        parser.error('--original and --corpus are mutually exclusive')
    if args.original:
        from tools.w0_cell_corpus import build
        corpus = build(args.original)
        with tempfile.TemporaryDirectory(prefix='mco-cell-corpus-') as directory:
            path = Path(directory) / 'original.json'
            path.write_text(json.dumps(corpus), encoding='utf-8')
            result = verify(args.directory.resolve(), platform, path)
        result['fresh_original_execution'] = True
    else:
        result = verify(args.directory.resolve(), platform,
                        args.corpus.resolve() if args.corpus else None)
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
