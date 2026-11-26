"""Scan and optimize oversized textures (e.g. 64MB .tga files) before committing to Git."""

import argparse
import os
from pathlib import Path
from PIL import Image

SUPPORTED_EXTS = {".tga", ".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff"}


def scan_textures(root: Path, min_mb: float) -> list[tuple[Path, float]]:
    results = []
    for path in root.rglob("*"):
        if path.is_file() and path.suffix.lower() in SUPPORTED_EXTS:
            size_mb = path.stat().st_size / (1024 * 1024)
            if size_mb >= min_mb:
                results.append((path, size_mb))
    return sorted(results, key=lambda item: item[1], reverse=True)


def optimize_image(path: Path, max_dim: int, to_png: bool, dry_run: bool) -> None:
    with Image.open(path) as img:
        w, h = img.size
        needs_resize = max(w, h) > max_dim
        target_path = path.with_suffix(".png") if (to_png and path.suffix.lower() == ".tga") else path

        if not needs_resize and target_path == path:
            print(f"  [SKIP] {path.name} ({w}x{h}) already within limits")
            return

        new_size = (w, h)
        if needs_resize:
            scale = max_dim / max(w, h)
            new_size = (int(w * scale), int(h * scale))

        if dry_run:
            print(f"  [DRY-RUN] {path} ({w}x{h}) -> {target_path.name} ({new_size[0]}x{new_size[1]})")
            return

        out_img = img.resize(new_size, Image.Resampling.LANCZOS) if needs_resize else img
        out_img.save(target_path, optimize=True)
        new_mb = target_path.stat().st_size / (1024 * 1024)
        print(f"  [OK] {target_path.name} -> {new_size[0]}x{new_size[1]} ({new_mb:.2f} MB)")


def main() -> None:
    parser = argparse.ArgumentParser(description="Find and optimize heavy textures for Unity + Git.")
    parser.add_argument("target", type=Path, help="Folder to scan (e.g., Unity Assets folder)")
    parser.add_argument("--min-mb", type=float, default=10.0, help="Flag files >= N MB (default: 10)")
    parser.add_argument("--max-dim", type=int, default=2048, help="Max width/height when optimizing (default: 2048)")
    parser.add_argument("--to-png", action="store_true", help="Convert .tga files to compressed .png")
    parser.add_argument("--apply", action="store_true", help="Apply optimization (default is dry-run)")
    args = parser.parse_args()

    if not args.target.exists():
        raise SystemExit(f"Target path not found: {args.target}")

    heavy = scan_textures(args.target, args.min_mb)
    if not heavy:
        print(f"No textures >= {args.min_mb} MB found in {args.target}")
        return

    print(f"Found {len(heavy)} texture(s) >= {args.min_mb} MB:")
    for path, mb in heavy:
        warn = " [GITHUB >50MB WARNING]" if mb >= 50.0 else ""
        print(f" - {mb:6.2f} MB | {path}{warn}")

    if args.apply or args.to_png:
        print("\nOptimizing...")
        for path, _ in heavy:
            optimize_image(path, args.max_dim, args.to_png, dry_run=not args.apply)


if __name__ == "__main__":
    main()
