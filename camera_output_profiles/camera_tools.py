"""Camera placement, framing, targeting, duplication, and preset helpers."""

from __future__ import annotations

from dataclasses import dataclass
from math import sin
from typing import Iterable

import bpy
from mathutils import Matrix, Vector


TRACK_CONSTRAINT_NAME = "COP_Track_To_Target"
PROFILE_FIELDS = (
    "initialized",
    "enabled",
    "width",
    "height",
    "file_format",
    "color_mode",
    "quality",
    "transparent_background",
    "output_subfolder",
    "filename_template",
    "use_current_frame",
    "frame",
)

VIEW_PRESETS = {
    "FRONT": ("Front", Vector((0.0, -1.0, 0.0))),
    "BACK": ("Back", Vector((0.0, 1.0, 0.0))),
    "LEFT": ("Left", Vector((-1.0, 0.0, 0.0))),
    "RIGHT": ("Right", Vector((1.0, 0.0, 0.0))),
    "TOP": ("Top", Vector((0.0, 0.0, 1.0))),
    "BOTTOM": ("Bottom", Vector((0.0, 0.0, -1.0))),
    "THREE_QUARTER_FRONT": ("3/4 Front", Vector((1.0, -1.0, 0.45))),
    "THREE_QUARTER_BACK": ("3/4 Back", Vector((-1.0, 1.0, 0.45))),
    "ISOMETRIC": ("Isometric", Vector((1.0, -1.0, 1.0))),
    "LOW_ANGLE": ("Low Angle", Vector((1.0, -1.0, -0.35))),
    "HIGH_ANGLE": ("High Angle", Vector((1.0, -1.0, 1.35))),
}

LENS_PRESETS = {
    "LENS_24": ("24mm Wide", "PERSP", 24.0),
    "LENS_35": ("35mm Natural", "PERSP", 35.0),
    "LENS_50": ("50mm Standard", "PERSP", 50.0),
    "LENS_70": ("70mm Product", "PERSP", 70.0),
    "LENS_85": ("85mm Product/Portrait", "PERSP", 85.0),
    "LENS_100": ("100mm Detail", "PERSP", 100.0),
    "ORTHO_PRODUCT": ("Orthographic Product", "ORTHO", 0.0),
}

CAMERA_SETS = {
    "PRODUCT_BASIC": (
        ("COP_Front", "FRONT", (1920, 1080)),
        ("COP_3Q_Front", "THREE_QUARTER_FRONT", (1920, 1080)),
        ("COP_Side", "RIGHT", (1920, 1080)),
        ("COP_Top", "TOP", (1920, 1080)),
    ),
    "PRODUCT_FULL": (
        ("COP_Front", "FRONT", (1920, 1080)),
        ("COP_Back", "BACK", (1920, 1080)),
        ("COP_Left", "LEFT", (1920, 1080)),
        ("COP_Right", "RIGHT", (1920, 1080)),
        ("COP_Top", "TOP", (1920, 1080)),
        ("COP_3Q_Front", "THREE_QUARTER_FRONT", (1920, 1080)),
    ),
    "SOCIAL_PACK": (
        ("COP_Hero_16x9", "THREE_QUARTER_FRONT", (1920, 1080)),
        ("COP_Square_1x1", "THREE_QUARTER_FRONT", (2048, 2048)),
        ("COP_Vertical_9x16", "FRONT", (1080, 1920)),
    ),
}


@dataclass(slots=True)
class TargetInfo:
    center: Vector
    objects: list
    label: str
    minimum: Vector
    maximum: Vector

    @property
    def dimensions(self) -> Vector:
        return self.maximum - self.minimum

    @property
    def radius(self) -> float:
        return max(self.dimensions.length * 0.5, 0.5)


def _object_visible(obj, context) -> bool:
    try:
        return bool(obj.visible_get(view_layer=context.view_layer)) and not obj.hide_render
    except Exception:
        return not bool(getattr(obj, "hide_render", False))


def world_bounds(objects: Iterable) -> TargetInfo:
    points: list[Vector] = []
    valid_objects = []
    for obj in objects:
        if getattr(obj, "type", None) == "CAMERA":
            continue
        valid_objects.append(obj)
        bound_box = getattr(obj, "bound_box", None)
        if bound_box:
            points.extend(obj.matrix_world @ Vector(corner) for corner in bound_box)
        else:
            points.append(obj.matrix_world.translation.copy())
    if not points:
        raise ValueError("No target objects with usable bounds.")
    minimum = Vector(tuple(min(point[index] for point in points) for index in range(3)))
    maximum = Vector(tuple(max(point[index] for point in points) for index in range(3)))
    center = (minimum + maximum) * 0.5
    label = valid_objects[0].name if len(valid_objects) == 1 else f"{len(valid_objects)} objects"
    return TargetInfo(center, valid_objects, label, minimum, maximum)


def resolve_target(context, camera, mode: str | None = None) -> TargetInfo:
    mode = mode or context.scene.camera_output_target_mode
    selected = [
        obj
        for obj in getattr(context, "selected_objects", ())
        if obj is not camera and getattr(obj, "type", None) != "CAMERA"
    ]
    active = getattr(context, "object", None)

    if mode == "CAMERA_TARGET":
        target = camera.camera_output_profile.tracking_target
        if target is None:
            raise ValueError("Camera Target Empty is missing.")
        return world_bounds([target])
    if mode == "ACTIVE":
        if active is None or active is camera or getattr(active, "type", None) == "CAMERA":
            raise ValueError("No valid active target object.")
        return world_bounds([active])
    if mode == "VISIBLE":
        objects = [
            obj
            for obj in context.scene.objects
            if obj is not camera
            and getattr(obj, "type", None) != "CAMERA"
            and _object_visible(obj, context)
        ]
        return world_bounds(objects)
    if mode == "SCENE_CENTER":
        zero = Vector((0.0, 0.0, 0.0))
        return TargetInfo(zero, [], context.scene.name, zero.copy(), zero.copy())
    if selected:
        return world_bounds(selected)
    if active is not None and active is not camera and getattr(active, "type", None) != "CAMERA":
        return world_bounds([active])
    zero = Vector((0.0, 0.0, 0.0))
    return TargetInfo(zero, [], context.scene.name, zero.copy(), zero.copy())


def safe_look_at(camera, target: Vector) -> None:
    origin = (
        camera.location.copy()
        if getattr(camera, "parent", None) is None
        else camera.matrix_world.translation.copy()
    )
    forward = target - origin
    if forward.length < 1.0e-6:
        raise ValueError("Camera and target are at the same location.")
    forward.normalize()
    up_hint = Vector((0.0, 0.0, 1.0))
    if abs(forward.dot(up_hint)) > 0.999:
        up_hint = Vector((0.0, 1.0, 0.0))
    right = forward.cross(up_hint).normalized()
    up = right.cross(forward).normalized()
    rotation = Matrix((right, up, -forward)).transposed().to_quaternion()
    camera.rotation_mode = "QUATERNION"
    camera.rotation_quaternion = rotation


def apply_view_preset(context, camera, preset: str) -> TargetInfo:
    label, direction = VIEW_PRESETS[preset]
    target = resolve_target(context, camera)
    distance = max(target.radius * context.scene.camera_output_distance_multiplier, 0.5)
    offset = direction.normalized() * distance
    offset.z += context.scene.camera_output_height_offset
    camera.location = target.center + offset
    safe_look_at(camera, target.center)
    camera.select_set(True)
    context.view_layer.objects.active = camera
    return target


def frame_camera(context, camera, objects: Iterable) -> TargetInfo:
    target = world_bounds(objects)
    margin = 1.0 + context.scene.camera_output_margin / 100.0
    data = camera.data
    if data.type == "ORTHO":
        aspect = max(
            context.scene.render.resolution_x / max(context.scene.render.resolution_y, 1),
            1.0e-6,
        )
        data.ortho_scale = max(target.dimensions.y, target.dimensions.x / aspect, 0.1) * margin
        safe_look_at(camera, target.center)
        return target

    half_angle = max(min(data.angle_x, data.angle_y) * 0.5, 0.01)
    distance = target.radius * margin / max(sin(half_angle), 0.01)
    view_direction = -(camera.matrix_world.to_quaternion() @ Vector((0.0, 0.0, -1.0)))
    if view_direction.length < 1.0e-6:
        view_direction = Vector((0.0, -1.0, 0.0))
    camera.location = target.center + view_direction.normalized() * distance
    safe_look_at(camera, target.center)
    return target


def create_target_empty(context, camera, *, target: TargetInfo | None = None):
    target = target or resolve_target(context, camera)
    existing = camera.camera_output_profile.tracking_target
    if existing is not None and existing.name in context.scene.objects:
        existing.location = target.center
        return existing, target

    safe_label = target.objects[0].name if len(target.objects) == 1 else context.scene.name
    empty = bpy.data.objects.new(f"COP_Target_{safe_label}", None)
    empty.empty_display_type = "PLAIN_AXES"
    empty.empty_display_size = max(target.radius * 0.2, 0.1)
    context.scene.collection.objects.link(empty)
    empty.location = target.center
    if len(target.objects) == 1:
        world_matrix = empty.matrix_world.copy()
        empty.parent = target.objects[0]
        empty.matrix_parent_inverse = target.objects[0].matrix_world.inverted()
        empty.matrix_world = world_matrix
    camera.camera_output_profile.tracking_target = empty
    return empty, target


def aim_at_saved_target(camera) -> None:
    target = camera.camera_output_profile.tracking_target
    if target is None:
        raise ValueError("Camera Target Empty is missing.")
    safe_look_at(camera, target.matrix_world.translation)


def add_tracking(camera):
    target = camera.camera_output_profile.tracking_target
    if target is None:
        raise ValueError("Camera Target Empty is missing.")
    constraint = camera.constraints.get(TRACK_CONSTRAINT_NAME)
    if constraint is None:
        constraint = camera.constraints.new(type="TRACK_TO")
        constraint.name = TRACK_CONSTRAINT_NAME
    constraint.target = target
    constraint.track_axis = "TRACK_NEGATIVE_Z"
    constraint.up_axis = "UP_Y"
    return constraint


def remove_tracking(camera) -> bool:
    constraint = camera.constraints.get(TRACK_CONSTRAINT_NAME)
    if constraint is None:
        return False
    camera.constraints.remove(constraint)
    return True


def copy_profile(source, destination) -> None:
    for field_name in PROFILE_FIELDS:
        setattr(destination, field_name, getattr(source, field_name))


def duplicate_camera(context, camera, *, copy_tracking: bool = False):
    duplicate = camera.copy()
    duplicate.data = camera.data.copy()
    duplicate.name = f"{camera.name}_Copy"
    context.scene.collection.objects.link(duplicate)
    copy_profile(camera.camera_output_profile, duplicate.camera_output_profile)
    duplicate.camera_output_profile.tracking_target = (
        camera.camera_output_profile.tracking_target if copy_tracking else None
    )
    if not copy_tracking:
        for constraint in list(duplicate.constraints):
            if constraint.name == TRACK_CONSTRAINT_NAME:
                duplicate.constraints.remove(constraint)
    for obj in context.selected_objects:
        obj.select_set(False)
    duplicate.select_set(True)
    context.view_layer.objects.active = duplicate
    return duplicate


def apply_lens_preset(context, camera, preset: str) -> str:
    label, camera_type, lens = LENS_PRESETS[preset]
    camera.data.type = camera_type
    if camera_type == "PERSP":
        camera.data.lens = lens
    else:
        try:
            target = resolve_target(context, camera)
            camera.data.ortho_scale = max(target.dimensions.x, target.dimensions.y, 1.0) * (
                1.0 + context.scene.camera_output_margin / 100.0
            )
        except ValueError:
            camera.data.ortho_scale = max(camera.data.ortho_scale, 5.0)
    return label


def create_camera_set(context) -> list:
    scene = context.scene
    target = resolve_target(context, None)
    cameras = []
    shared_target = None
    for name, view_preset, resolution in CAMERA_SETS[scene.camera_output_camera_set_type]:
        data = bpy.data.cameras.new(name)
        camera = bpy.data.objects.new(name, data)
        scene.collection.objects.link(camera)
        profile = camera.camera_output_profile
        profile.initialized = True
        profile.enabled = True
        profile.width, profile.height = resolution
        profile.output_subfolder = scene.camera_output_default_subfolder
        profile.filename_template = "{camera}_{width}x{height}_{frame}"
        label, direction = VIEW_PRESETS[view_preset]
        distance = max(target.radius * scene.camera_output_distance_multiplier, 0.5)
        camera.location = target.center + direction.normalized() * distance
        safe_look_at(camera, target.center)
        if scene.camera_output_camera_set_add_tracking:
            if shared_target is None:
                shared_target, _ = create_target_empty(context, camera, target=target)
            camera.camera_output_profile.tracking_target = shared_target
            add_tracking(camera)
        cameras.append(camera)
    if cameras:
        for obj in context.selected_objects:
            obj.select_set(False)
        cameras[0].select_set(True)
        context.view_layer.objects.active = cameras[0]
        scene.camera = cameras[0]
    return cameras
