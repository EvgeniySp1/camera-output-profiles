bl_info = {
    "name": "Camera Output Profiles",
    "author": "Open-source contributors",
    "version": (0, 2, 0),
    "blender": (4, 2, 0),
    "location": "View3D > Sidebar > Cam Output",
    "description": "Per-camera render resolution, aspect ratio, file naming and output profiles",
    "category": "Render",
}

from . import operators, properties, render_manager, ui


CLASSES = properties.CLASSES + operators.CLASSES + ui.CLASSES


def register() -> None:
    import bpy

    for cls in CLASSES:
        bpy.utils.register_class(cls)
    properties.register_properties()


def unregister() -> None:
    import bpy

    render_manager.cleanup_render_session(restore=True)
    properties.unregister_properties()
    for cls in reversed(CLASSES):
        bpy.utils.unregister_class(cls)
