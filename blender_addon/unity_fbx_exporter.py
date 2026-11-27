bl_info = {
    "name": "Unity FBX & glTF Pipeline Exporter",
    "author": "ArdanR3",
    "version": (1, 1, 0),
    "blender": (3, 6, 0),
    "location": "View3D > Sidebar > Unity",
    "description": "Export meshes to Unity-ready FBX or GLB/glTF with optional non-destructive LOD presets and batch export.",
    "category": "Import-Export",
}

import os
import bpy
from bpy.props import BoolProperty, EnumProperty, StringProperty
from bpy.types import Operator, Panel, PropertyGroup

LOD_MODIFIER_NAME = "__unity_pipeline_lod_decimate__"

LOD_PRESETS = {
    "NONE": [("", 1.0)],
    "UNITY_2": [("_LOD0", 1.0), ("_LOD1", 0.5)],
    "UNITY_3": [("_LOD0", 1.0), ("_LOD1", 0.5), ("_LOD2", 0.25)],
}

FORMAT_EXTENSIONS = {
    "FBX": ".fbx",
    "GLB": ".glb",
    "GLTF_SEPARATE": ".gltf",
}


class UnityExporterSettings(PropertyGroup):
    export_dir: StringProperty(
        name="Export Folder",
        description="Target folder (e.g., Unity Assets/Models directory)",
        default="//exports/",
        subtype="DIR_PATH",
    )
    export_format: EnumProperty(
        name="Format",
        items=[
            ("FBX", "Unity FBX (.fbx)", "Export Unity-compatible FBX (-Z Forward, Y Up)"),
            ("GLB", "glTF Binary (.glb)", "Export single-file binary glTF 2.0 (Unity / Three.js / Web 3D)"),
            ("GLTF_SEPARATE", "glTF Separate (.gltf)", "Export glTF JSON with separate .bin and textures"),
        ],
        default="FBX",
    )
    export_mode: EnumProperty(
        name="Mode",
        items=[
            ("SELECTED_ONE", "Selected -> Single File", "Export all selected objects into one file"),
            ("SELECTED_EACH", "Selected -> Per Object", "Export each selected object as its own file"),
            ("COLLECTION", "Active Collection", "Export the active collection as one file"),
        ],
        default="SELECTED_ONE",
    )
    lod_preset: EnumProperty(
        name="LOD Preset",
        items=[
            ("NONE", "None (Single Mesh)", "Export without LOD suffix"),
            ("UNITY_2", "2-Tier (_LOD0, _LOD1)", "Export _LOD0 (100%) and _LOD1 (50%)"),
            ("UNITY_3", "3-Tier (_LOD0, _LOD1, _LOD2)", "Export _LOD0 (100%), _LOD1 (50%), and _LOD2 (25%)"),
        ],
        default="NONE",
    )
    lod_use_decimate: BoolProperty(
        name="Non-Destructive Decimate",
        description="Temporarily apply a Decimate modifier per LOD tier without altering the source mesh",
        default=True,
    )
    apply_modifiers: BoolProperty(
        name="Apply Modifiers",
        default=True,
    )
    include_animations: BoolProperty(
        name="Include Animations",
        default=False,
    )


def _export_fbx(filepath: str, apply_modifiers: bool, include_animations: bool) -> None:
    bpy.ops.export_scene.fbx(
        filepath=filepath,
        use_selection=True,
        global_scale=1.0,
        apply_unit_scale=True,
        apply_scale_options="FBX_SCALE_ALL",
        axis_forward="-Z",
        axis_up="Y",
        use_space_transform=True,
        bake_space_transform=True,
        object_types={"ARMATURE", "MESH", "EMPTY"},
        use_mesh_modifiers=apply_modifiers,
        mesh_smooth_type="FACE",
        add_leaf_bones=False,
        bake_anim=include_animations,
        path_mode="COPY",
        embed_textures=False,
    )


def _export_gltf(filepath: str, export_format: str, apply_modifiers: bool, include_animations: bool) -> None:
    bpy.ops.export_scene.gltf(
        filepath=filepath,
        export_format=export_format,
        use_selection=True,
        export_yup=True,
        export_apply=apply_modifiers,
        export_animations=include_animations,
    )


def _export_single_file(
    filepath: str,
    export_format: str,
    apply_modifiers: bool,
    include_animations: bool,
) -> None:
    if export_format == "FBX":
        _export_fbx(filepath, apply_modifiers, include_animations)
    else:
        _export_gltf(filepath, export_format, apply_modifiers, include_animations)


def _export_with_lods(
    out_dir: str,
    base_name: str,
    target_objects: list,
    props: UnityExporterSettings,
) -> list[str]:
    ext = FORMAT_EXTENSIONS.get(props.export_format, ".fbx")
    tiers = LOD_PRESETS.get(props.lod_preset, [("", 1.0)])
    exported_paths: list[str] = []

    for suffix, ratio in tiers:
        added_modifiers: list[tuple] = []
        filepath = os.path.join(out_dir, f"{base_name}{suffix}{ext}")

        try:
            if ratio < 1.0 and props.lod_use_decimate:
                for obj in target_objects:
                    if obj.type == "MESH":
                        mod = obj.modifiers.new(name=LOD_MODIFIER_NAME, type="DECIMATE")
                        mod.ratio = ratio
                        added_modifiers.append((obj, mod))

            use_mods = props.apply_modifiers or bool(added_modifiers)
            _export_single_file(filepath, props.export_format, use_mods, props.include_animations)
            exported_paths.append(filepath)
        finally:
            for obj, mod in added_modifiers:
                if mod.name in obj.modifiers:
                    obj.modifiers.remove(mod)

    return exported_paths


class UNITY_OT_ExportFBX(Operator):
    bl_idname = "unity_pipeline.export_fbx"
    bl_label = "Export 3D Asset"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        props = context.scene.unity_exporter
        out_dir = bpy.path.abspath(props.export_dir)
        os.makedirs(out_dir, exist_ok=True)

        selected = list(context.selected_objects)
        if props.export_mode in {"SELECTED_ONE", "SELECTED_EACH"} and not selected:
            self.report({"WARNING"}, "Select at least one object to export.")
            return {"CANCELLED"}

        exported_count = 0

        if props.export_mode == "SELECTED_ONE":
            name = context.active_object.name if context.active_object else selected[0].name
            paths = _export_with_lods(out_dir, name, selected, props)
            exported_count += len(paths)
            self.report({"INFO"}, f"Exported {len(paths)} file(s) for '{name}' to {out_dir}")

        elif props.export_mode == "SELECTED_EACH":
            bpy.ops.object.select_all(action="DESELECT")
            for obj in selected:
                obj.select_set(True)
                context.view_layer.objects.active = obj
                paths = _export_with_lods(out_dir, obj.name, [obj], props)
                exported_count += len(paths)
                obj.select_set(False)
            for obj in selected:
                obj.select_set(True)
            self.report({"INFO"}, f"Batch exported {exported_count} {props.export_format} file(s) to {out_dir}")

        elif props.export_mode == "COLLECTION":
            col = context.collection
            if not col or not col.objects:
                self.report({"WARNING"}, "Active collection is empty.")
                return {"CANCELLED"}
            bpy.ops.object.select_all(action="DESELECT")
            col_objects = list(col.objects)
            for obj in col_objects:
                obj.select_set(True)
            paths = _export_with_lods(out_dir, col.name, col_objects, props)
            exported_count += len(paths)
            self.report({"INFO"}, f"Exported collection '{col.name}' ({len(paths)} file(s)) to {out_dir}")

        return {"FINISHED"}


class UNITY_PT_ExporterPanel(Panel):
    bl_label = "Unity & glTF Pipeline"
    bl_idname = "UNITY_PT_exporter_panel"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Unity"

    def draw(self, context):
        layout = self.layout
        props = context.scene.unity_exporter

        layout.prop(props, "export_dir")
        layout.prop(props, "export_format")
        layout.prop(props, "export_mode")
        layout.separator()
        layout.prop(props, "lod_preset")
        if props.lod_preset != "NONE":
            layout.prop(props, "lod_use_decimate")
        layout.separator()
        layout.prop(props, "apply_modifiers")
        layout.prop(props, "include_animations")
        layout.separator()
        layout.operator("unity_pipeline.export_fbx", icon="EXPORT")


CLASSES = (UnityExporterSettings, UNITY_OT_ExportFBX, UNITY_PT_ExporterPanel)


def register():
    for cls in CLASSES:
        bpy.utils.register_class(cls)
    bpy.types.Scene.unity_exporter = bpy.props.PointerProperty(type=UnityExporterSettings)


def unregister():
    del bpy.types.Scene.unity_exporter
    for cls in reversed(CLASSES):
        bpy.utils.unregister_class(cls)


if __name__ == "__main__":
    register()
