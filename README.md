# blender-unity-pipeline

Toolkit praktis untuk menjembatani workflow **Blender → Unity → GitHub**, dibuat berdasarkan kendala nyata saat mengelola aset 3D (rotasi/skala FBX yang meleset dan tekstur `.tga` 64 MB yang memicu *warning* ukuran file di GitHub).

## ✨ Fitur Utama

1. **Blender Add-on (`blender_addon/unity_fbx_exporter.py`)**
   - Export `.fbx` dengan transformasi yang langsung pas di Unity (`-Z` Forward, `Y` Up, `FBX_SCALE_ALL`, *bake space transform*).
   - Mendukung **Single FBX**, **Batch Per Object**, dan **Active Collection**.
2. **Texture Optimizer CLI (`scripts/optimize_textures.py`)**
   - Memindai folder `Assets/` untuk menemukan tekstur berukuran besar (mis. `.tga` > 50 MB).
   - Bisa mengonversi `.tga` → `.png` dan *downscale* resolusi maksimal (mis. `2048px`) agar ukuran repo tetap ramping.
3. **Unity Editor Asset Size Checker (`unity_editor/UnityAssetSizeChecker.cs`)**
   - Menu `Tools > Pipeline > Check Large Assets` di Unity Editor untuk mendeteksi file yang mendekati batas 50 MB / 100 MB GitHub sebelum `git commit`.

## 🚀 Cara Penggunaan

### 1. Pasang Add-on di Blender
1. Buka Blender → `Edit > Preferences > Add-ons > Install...`
2. Pilih `blender_addon/unity_fbx_exporter.py` lalu aktifkan **Unity FBX Pipeline Exporter**.
3. Tekan `N` di *3D Viewport* → buka tab **Unity**.

### 2. Cek & Optimasi Tekstur (Python)
```bash
pip install pillow

# Cek tekstur >= 10 MB (dry-run)
python scripts/optimize_textures.py "D:\Unity\Projects\All_Tugas_K3\Assets" --min-mb 10

# Konversi .tga ke .png dan batasi resolusi maksimal 2048px
python scripts/optimize_textures.py "D:\Unity\Projects\All_Tugas_K3\Assets" --min-mb 20 --max-dim 2048 --to-png --apply
```

### 3. Pakai Checker di Unity
Salin `unity_editor/UnityAssetSizeChecker.cs` ke folder `Assets/Editor/` di proyek Unity kamu, lalu buka **`Tools > Pipeline > Check Large Assets`**.
