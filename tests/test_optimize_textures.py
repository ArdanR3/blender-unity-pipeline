"""Automated pytest suite for scripts/optimize_textures.py and Blender add-on syntax."""

import ast
import sys
from pathlib import Path

import pytest
from PIL import Image

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import optimize_textures as opt  # noqa: E402


def _make_image(path: Path, size: tuple[int, int], color: tuple[int, int, int] = (40, 120, 210)) -> Path:
    img = Image.new("RGB", size, color=color)
    # Add a simple deterministic gradient so compression & resize behavior are realistic
    pixels = img.load()
    w, h = size
    for y in range(0, h, max(1, h // 32)):
        for x in range(0, w, max(1, w // 32)):
            pixels[x, y] = ((x * 7) % 256, (y * 11) % 256, ((x + y) * 5) % 256)
    img.save(path)
    return path


def test_scan_textures_filters_by_size_and_sorts_descending(tmp_path: Path) -> None:
    small_png = _make_image(tmp_path / "small.png", (64, 64))
    large_tga = _make_image(tmp_path / "large.tga", (512, 512))
    medium_tga = _make_image(tmp_path / "medium.tga", (256, 256))
    ignored_txt = tmp_path / "notes.txt"
    ignored_txt.write_bytes(b"x" * (1024 * 1024))  # 1 MB non-image file

    # 256x256 RGB TGA is ~0.19 MB, 512x512 RGB TGA is ~0.75 MB, 64x64 PNG is <0.01 MB
    results = opt.scan_textures(tmp_path, min_mb=0.1)
    found_names = [p.name for p, _ in results]

    assert found_names == ["large.tga", "medium.tga"]
    assert small_png.name not in found_names
    assert ignored_txt.name not in found_names
    assert results[0][1] > results[1][1]


def test_optimize_image_resizes_oversized_png_preserving_aspect_ratio(tmp_path: Path) -> None:
    src = _make_image(tmp_path / "wide_albedo.png", (600, 300))

    opt.optimize_image(src, max_dim=200, to_png=False, dry_run=False)

    with Image.open(src) as updated:
        assert updated.size == (200, 100)


def test_optimize_image_converts_tga_to_compressed_png(tmp_path: Path) -> None:
    tga_path = _make_image(tmp_path / "hero_diffuse.tga", (400, 400))
    tga_size = tga_path.stat().st_size

    opt.optimize_image(tga_path, max_dim=256, to_png=True, dry_run=False)

    png_path = tga_path.with_suffix(".png")
    assert png_path.exists()
    with Image.open(png_path) as converted:
        assert converted.size == (256, 256)
    assert png_path.stat().st_size < tga_size


def test_optimize_image_dry_run_does_not_modify_files(tmp_path: Path) -> None:
    tga_path = _make_image(tmp_path / "dry_test.tga", (500, 500))
    orig_bytes = tga_path.read_bytes()

    opt.optimize_image(tga_path, max_dim=128, to_png=True, dry_run=True)

    assert not tga_path.with_suffix(".png").exists()
    assert tga_path.read_bytes() == orig_bytes


def test_optimize_image_skips_within_limits(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    png_path = _make_image(tmp_path / "ok_icon.png", (128, 128))

    opt.optimize_image(png_path, max_dim=512, to_png=True, dry_run=False)

    captured = capsys.readouterr().out
    assert "[SKIP]" in captured
    with Image.open(png_path) as img:
        assert img.size == (128, 128)


def test_cli_main_exits_for_missing_target(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    missing = tmp_path / "does-not-exist"
    monkeypatch.setattr(sys, "argv", ["optimize_textures.py", str(missing)])

    with pytest.raises(SystemExit) as exc:
        opt.main()
    assert "Target path not found" in str(exc.value)


def test_cli_main_applies_tga_conversion_end_to_end(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    tga_path = _make_image(tmp_path / "cliff_4k.tga", (512, 512))
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "optimize_textures.py",
            str(tmp_path),
            "--min-mb",
            "0.1",
            "--max-dim",
            "256",
            "--to-png",
            "--apply",
        ],
    )

    opt.main()

    out_png = tga_path.with_suffix(".png")
    assert out_png.exists()
    with Image.open(out_png) as img:
        assert img.size == (256, 256)


def test_blender_addon_syntax_and_exports_structure() -> None:
    addon_path = REPO_ROOT / "blender_addon" / "unity_fbx_exporter.py"
    source = addon_path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(addon_path))

    func_names = {node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)}
    class_names = {node.name for node in ast.walk(tree) if isinstance(node, ast.ClassDef)}

    assert {"_export_fbx", "_export_gltf", "_export_with_lods", "register", "unregister"}.issubset(func_names)
    assert {"UnityExporterSettings", "UNITY_OT_ExportFBX", "UNITY_PT_ExporterPanel"}.issubset(class_names)
    assert '"GLB"' in source and '"GLTF_SEPARATE"' in source
    assert '"_LOD0"' in source and '"_LOD1"' in source and '"_LOD2"' in source
