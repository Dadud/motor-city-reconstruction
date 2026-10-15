"""Build the recovered C++ library; no game assets or research tools required."""
import argparse
from pathlib import Path
import shutil
import subprocess
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--build-dir', type=Path, default=Path('build/recovered'))
    parser.add_argument('--config', choices=('Debug', 'Release'), default='Release')
    parser.add_argument('--test', action='store_true', help='build and run native checks')
    parser.add_argument('--cmake', default='cmake', help='CMake executable or full path')
    parser.add_argument('cmake_args', nargs=argparse.REMAINDER,
                        help='extra configure options after -- (compiler, generator, etc.)')
    args = parser.parse_args()
    root = Path(__file__).resolve().parent
    directory = args.build_dir if args.build_dir.is_absolute() else root / args.build_dir
    cmake = shutil.which(args.cmake)
    if cmake is None:
        parser.error('CMake 3.24+ is required; install it or pass --cmake PATH')
    extra = args.cmake_args
    if extra[:1] == ['--']:
        extra = extra[1:]
    configure = [cmake, '-S', str(root), '-B', str(directory),
                 f'-DCMAKE_BUILD_TYPE={args.config}',
                 '-DMCO_BUILD_SCRIPTING=OFF', '-DMCO_BUILD_PLATFORM=OFF',
                 f'-DBUILD_TESTING={"ON" if args.test else "OFF"}', *extra]
    commands = [configure, [cmake, '--build', str(directory), '--config', args.config,
                            '--parallel']]
    if args.test:
        ctest = Path(cmake).with_name('ctest.exe' if sys.platform == 'win32' else 'ctest')
        if not ctest.is_file():
            parser.error('ctest must be installed beside the selected CMake executable')
        commands.append([str(ctest), '--test-dir', str(directory), '-C', args.config,
                         '--output-on-failure'])
    try:
        for command in commands:
            print(subprocess.list2cmdline(command), flush=True)
            subprocess.run(command, cwd=root, check=True)
    except (subprocess.CalledProcessError, OSError) as error:
        print(f'Build failed: {error}', file=sys.stderr)
        return 1
    print(f'Recovered source build complete: {directory}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
