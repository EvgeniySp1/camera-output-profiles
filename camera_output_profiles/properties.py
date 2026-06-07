"""Blender property definitions for Camera Output Profiles."""

import bpy
from bpy.props import (
    BoolProperty,
    CollectionProperty,
    EnumProperty,
    IntProperty,
    PointerProperty,
    StringProperty,
)
from bpy.types import PropertyGroup


FILE_FORMAT_ITEMS = (
    ("PNG", "PNG", "Portable Network Graphics"),
    ("JPEG", "JPEG", "JPEG image"),
    ("WEBP", "WEBP", "WebP image, when supported by this Blender build"),
)

COLOR_MODE_ITEMS = (
    ("RGB", "RGB", "Render without alpha channel"),
    ("RGBA", "RGBA", "Render with alpha channel when the format supports it"),
)

VALIDATION_SEVERITY_ITEMS = (
    ("CRITICAL", "Critical", "Blocks batch rendering"),
    ("WARNING", "Warning", "Does not block rendering"),
    ("INFO", "Info", "Informational message"),
)


def _default_frame_for_profile(profile: PropertyGroup) -> int:
    obj = getattr(profile, "id_data", None)
    if obj is not None:
        for scene in bpy.data.scenes:
            if scene.objects.get(obj.name) is obj:
                return int(scene.frame_current)
    return 1


def _get_frame(profile: PropertyGroup) -> int:
    try:
        return int(profile.get("_frame", _default_frame_for_profile(profile)))
    except (TypeError, ValueError):
        return _default_frame_for_profile(profile)


def _set_frame(profile: PropertyGroup, value: int) -> None:
    profile["_frame"] = int(value)


class CameraOutputProfile(PropertyGroup):
    """Per-camera render output profile."""

    initialized: BoolProperty(
        name="Initialized",
        default=False,
        options={"HIDDEN"},
    )

    enabled: BoolProperty(
        name="Enabled",
        description="Include this camera in batch rendering",
        default=True,
    )

    width: IntProperty(
        name="Width",
        description="Render resolution width in pixels",
        default=1920,
        min=1,
        soft_max=8192,
    )

    height: IntProperty(
        name="Height",
        description="Render resolution height in pixels",
        default=1080,
        min=1,
        soft_max=8192,
    )

    file_format: EnumProperty(
        name="Format",
        description="Image file format for this camera profile",
        items=FILE_FORMAT_ITEMS,
        default="PNG",
    )

    color_mode: EnumProperty(
        name="Color",
        description="Output color mode",
        items=COLOR_MODE_ITEMS,
        default="RGBA",
    )

    quality: IntProperty(
        name="Quality",
        description="JPEG/WebP quality",
        default=90,
        min=1,
        max=100,
        subtype="PERCENTAGE",
    )

    transparent_background: BoolProperty(
        name="Transparent",
        description="Use transparent film background when supported",
        default=False,
    )

    output_subfolder: StringProperty(
        name="Output Subfolder",
        description=(
            "Optional folder inside the Base Output Folder. "
            "Leave empty to save directly into the base folder"
        ),
        default="camera_profiles",
    )

    filename_template: StringProperty(
        name="Filename Template",
        description="Filename template using tokens like {camera}, {width}, {height}, {frame}",
        default="{camera}_{width}x{height}_{frame}",
    )

    use_current_frame: BoolProperty(
        name="Current Frame",
        description="Render the scene's current frame",
        default=True,
    )

    frame: IntProperty(
        name="Frame",
        description="Frame to render when Current Frame is disabled",
        get=_get_frame,
        set=_set_frame,
    )


class CameraOutputValidationItem(PropertyGroup):
    severity: EnumProperty(
        name="Severity",
        items=VALIDATION_SEVERITY_ITEMS,
        default="INFO",
    )

    message: StringProperty(
        name="Message",
        default="",
    )

    camera_name: StringProperty(
        name="Camera",
        default="",
    )


CLASSES = (
    CameraOutputProfile,
    CameraOutputValidationItem,
)


def register_properties() -> None:
    bpy.types.Object.camera_output_profile = PointerProperty(type=CameraOutputProfile)
    bpy.types.Scene.camera_output_validation_results = CollectionProperty(
        type=CameraOutputValidationItem
    )
    bpy.types.Scene.camera_output_validation_summary = StringProperty(
        name="Validation",
        default="Not validated",
    )
    bpy.types.Scene.camera_output_validation_critical_count = IntProperty(default=0)
    bpy.types.Scene.camera_output_validation_warning_count = IntProperty(default=0)
    bpy.types.Scene.camera_output_validation_info_count = IntProperty(default=0)
    bpy.types.Scene.camera_output_validation_timestamp = StringProperty(default="")
    bpy.types.Scene.camera_output_show_render_window = BoolProperty(
        name="Show Render Window",
        description="Show Blender's Render Result after rendering when possible",
        default=True,
    )
    bpy.types.Scene.camera_output_open_folder_after_render = BoolProperty(
        name="Open Output Folder After Render",
        description="Open the output folder after a successful render",
        default=False,
    )
    bpy.types.Scene.camera_output_restore_scene_output = BoolProperty(
        name="Restore Scene Output After Render",
        description=(
            "When enabled, the add-on restores Blender's global Output settings "
            "after rendering. Disable if you want the last rendered profile to "
            "remain applied to Scene Output"
        ),
        default=True,
    )


def unregister_properties() -> None:
    for owner, attribute in (
        (bpy.types.Scene, "camera_output_restore_scene_output"),
        (bpy.types.Scene, "camera_output_open_folder_after_render"),
        (bpy.types.Scene, "camera_output_show_render_window"),
        (bpy.types.Scene, "camera_output_validation_timestamp"),
        (bpy.types.Scene, "camera_output_validation_info_count"),
        (bpy.types.Scene, "camera_output_validation_warning_count"),
        (bpy.types.Scene, "camera_output_validation_critical_count"),
        (bpy.types.Scene, "camera_output_validation_summary"),
        (bpy.types.Scene, "camera_output_validation_results"),
        (bpy.types.Object, "camera_output_profile"),
    ):
        if hasattr(owner, attribute):
            delattr(owner, attribute)
