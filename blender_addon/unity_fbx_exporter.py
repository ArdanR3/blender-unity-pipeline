bl_info = {
    "name": "Unity FBX Pipeline Exporter",
    "author": "ArdanR3",
    "version": (1, 0, 0),
    "blender": (3, 6, 0),
    "location": "View3D > Sidebar > Unity",
    "description": "Export meshes to FBX with Unity-compatible transforms, scale, and batch export.",
    "category": "Import-Export",
}

import os
import bpy
from bpy.props import BoolProperty, EnumProperty, StringProperty
from bpy.types import Operator, Panel, PropertyGroup


class UnityExporterSettings(PropertyGroup):
    export_dir: StringProperty(
        name="Export Folder",
        description="Target folder (e.g., Unity Assets/Models directory)",
        default="//exports/",
        subtype="DIR_PATH",
    )
    export_mode: EnumProperty(
        name="Mode",
        items=[
            ("SELECTED_ONE", "Selected -> Single FBX", "Export all selected objects into one FBX"),
            ("SELECTED_EACH", "Selected -> Per Object", "Export each selected object as its own FBX"),
            ("COLLECTION", "Active Collection", "Export the active collection as one FBX"),
        ],
        default="SELECTED_ONE",
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


class UNITY_OT_ExportFBX(Operator):
    bl_idname = "unity_pipeline.export_fbx"
    bl_label = "Export to Unity FBX"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        props = context.scene.unity_exporter
        out_dir = bpy.path.abspath(props.export_dir)
        os.makedirs(out_dir, exist_ok=True)

        selected = list(context.selected_objects)
        if props.export_mode in {"SELECTED_ONE", "SELECTED_EACH"} and not selected:
            self.report({"WARNING"}, "Select at least one object to export.")
            return {"CANCELLED"}

        if props.export_mode == "SELECTED_ONE":
            name = (context.active_object.name if context.active_object else selected[0].name)
            filepath = os.path.join(out_dir, f"{name}.fbx")
            _export_fbx(filepath, props.apply_modifiers, props.include_animations)
            self.report({"INFO"}, f"Exported {filepath}")

        elif props.export_mode == "SELECTED_EACH":
            bpy.ops.object.select_all(action="DESELECT")
            for obj in selected:
                obj.select_set(True)
                context.view_layer.objects.active = obj
                filepath = os.path.join(out_dir, f"{obj.name}.fbx")
                _export_fbx(filepath, props.apply_modifiers, props.include_animations)
                obj.select_set(False)
            for obj in selected:
                obj.select_set(True)
            self.report({"INFO"}, f"Batch exported {len(selected)} FBX files to {out_dir}")

        elif props.export_mode == "COLLECTION":
            col = context.collection
            if not col or not col.objects:
                self.report({"WARNING"}, "Active collection is empty.")
                return {"CANCELLED"}
            bpy.ops.object.select_all(action="DESELECT")
            for obj in col.objects:
                obj.select_set(True)
            filepath = os.path.join(out_dir, f"{col.name}.fbx")
            _export_fbx(filepath, props.apply_modifiers, props.include_animations)
            self.report({"INFO"}, f"Exported collection to {filepath}")

        return {"FINISHED"}


class UNITY_PT_ExporterPanel(Panel):
    bl_label = "Unity FBX Pipeline"
    bl_idname = "UNITY_PT_exporter_panel"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Unity"

    def draw(self, context):
        layout = self.layout
        props = context.scene.unity_exporter

        layout.prop(props, "export_dir")
        layout.prop(props, "export_mode")
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
