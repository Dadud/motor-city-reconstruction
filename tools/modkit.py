"""Run with python -m tools.modkit; standard-library data-alpha-1 SDK."""
import argparse
import html
import json
from pathlib import Path
import sys

from client.mod_registry import ModError, build_registry, load_package, package_archive
from client.mod_script import load_script_package, summarize_script_package, run_script_package


def preview_svg(resource):
    """Top-down (+X right, +Z up) authored geometry; no simulation implied."""
    data = resource.data
    title = html.escape(data["label"])
    mesh = data.get("mesh")
    shapes = []
    if mesh:
        vertices = mesh["vertices"]
        xs, zs = [v[0] for v in vertices], [v[2] for v in vertices]
        span = max(max(xs) - min(xs), max(zs) - min(zs), 1e-6)
        def point(index):
            x, _, z = vertices[index]
            return f"{40 + (x - min(xs)) / span * 520:.3f},{580 - (z - min(zs)) / span * 520:.3f}"
        for triangle in mesh["triangles"]:
            shapes.append(f'<polygon points="{" ".join(point(i) for i in triangle)}" fill="{data.get("color", "#60a5fa")}" stroke="#111827" stroke-width="1"/>')
    else:
        shapes.append('<text x="30" y="100">Metadata resource: no geometry preview</text>')
    return ('<svg xmlns="http://www.w3.org/2000/svg" width="640" height="640" viewBox="0 0 640 640">'
            '<rect width="640" height="640" fill="#f8fafc"/>'
            f'<text x="20" y="25">{title} — data alpha preview</text>' + "".join(shapes) +
            '<text x="20" y="625">Top view: +X right, +Z up; author units, no physics</text></svg>')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    script = sub.add_parser('script', help='Validate or execute an offline script-alpha-1 package')
    script.add_argument('package', help='script package directory or ZIP')
    script.add_argument('--runner', type=Path, help='built mco_mod_script executable; omit to validate only')
    script.add_argument('--event', choices=('inspect', 'preview'), default='inspect')
    script.add_argument('--output', type=Path, help='write a reproducible script package ZIP')
    for command in ("validate", "inspect", "preview", "package"):
        child = sub.add_parser(command)
        child.add_argument("packages", nargs="+", help="package directories or ZIP archives; include dependencies")
        if command == "preview":
            child.add_argument("--resource", required=True, help="namespaced registry ID (including replacement aliases)")
            child.add_argument("--output", required=True, type=Path, help="SVG output")
        if command == "package":
            child.add_argument("--output", required=True, type=Path, help="new ZIP output; first supplied package is packaged")
    args = parser.parse_args(argv)
    try:
        if args.command == 'script':
            package = load_script_package(args.package)
            result = (run_script_package(package, args.runner, event=args.event)
                      if args.runner else summarize_script_package(package))
            if args.output:
                package_archive(package, args.output)
            print(json.dumps(result, indent=2))
            return 0
        packages = [load_package(path) for path in args.packages]
        ordered, registry = build_registry(packages)
        if args.command == "preview":
            if args.resource not in registry:
                raise ModError(f"unknown resource {args.resource}; run inspect for available IDs")
            args.output.write_text(preview_svg(registry[args.resource]), encoding="utf-8")
            print(f"Preview saved: {args.output}")
        elif args.command == "package":
            package_archive(packages[0], args.output)
            print(f"Packaged {packages[0].id}: {args.output}")
        elif args.command == "inspect":
            print(json.dumps({"api_version": "data-alpha-1", "package_order": [p.id for p in ordered],
                              "packages": [{"id": p.id, "version": p.manifest["version"], "license": p.manifest["license"], "digest": p.digest} for p in ordered],
                              "resources": [{"id": rid, "provider": item.provider, "kind": item.kind, "data": item.data} for rid, item in registry.items()]}, indent=2))
        else:
            print(f"Valid: {len(ordered)} packages, {len(registry)} registry IDs; order: {', '.join(p.id for p in ordered)}")
    except (ModError, OSError, RecursionError) as exc:
        print(f"modkit: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
