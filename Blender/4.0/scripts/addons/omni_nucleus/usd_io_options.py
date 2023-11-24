# SPDX-License-Identifier: MIT
# Copyright (c) 2023, NVIDIA CORPORATION.  All rights reserved.

import sys
from typing import *

import bpy
from bpy.props import (BoolProperty, IntProperty, FloatProperty, StringProperty, EnumProperty)
from bpy.types import (Context)

g_export_frame_range_inited = False

def umm_loaded():
    return "omni.universalmaterialmap" in sys.modules

def create_prop(prop):
    if prop.type == "STRING":
        return StringProperty(default=prop.default, description=prop.description, name=prop.name)
    elif prop.type == "BOOLEAN":
        return BoolProperty(default=prop.default, description=prop.description, name=prop.name)
    elif prop.type == "INT":
        return IntProperty(default=prop.default, description=prop.description, name=prop.name)
    elif prop.type == "FLOAT":
        return FloatProperty(default=prop.default, description=prop.description, name=prop.name)
    elif prop.type == "ENUM":
        prop_items = [(ot.identifier, ot.name, ot.description) for ot in prop.enum_items]
        if len(prop_items) == 0:
            return None
        return EnumProperty(items=prop_items, default=prop.default, description=prop.description, name=prop.name)
    return None

def create_import_props_dict():
    props = {}

    prop_items = bpy.ops.wm.usd_import.get_rna_type().properties.items()
    for item in prop_items:
        if item[1].type == "POINTER":
            continue

        if item[1].identifier in ["sort_method"]:
            continue

        prop = create_prop(item[1])

        if (prop):
            props[item[1].identifier] = prop
        else:
            print (f"Couldn't create import prop {item[0]} of type {item[1].type}")

    return props

def create_export_props_dict():
    props = {}

    prop_items = bpy.ops.wm.usd_export.get_rna_type().properties.items()
    for item in prop_items:
        if item[1].type == "POINTER":
            continue

        if item[1].identifier in ["sort_method"]:
            continue

        prop = create_prop(item[1])

        if (prop):
            props[item[1].identifier] = prop
        else:
            print (f"Couldn't create export prop {item[0]} of type {item[1].type}")

    return props

import_props = create_import_props_dict()

usd_import_props_data = {
    'bl_label': "USD Import Props",
    'bl_idname': "omni.usd_import_props",
    '__annotations__': import_props
}

USDImportProps = type("USDImportProps", (bpy.types.PropertyGroup,), usd_import_props_data)

export_props = create_export_props_dict()

usd_export_props_data = {
    'bl_label': "USD Export Props",
    'bl_idname': "omni.usd_export_props",
    '__annotations__': export_props
}

USDExportProps = type("USDExportProps", (bpy.types.PropertyGroup,), usd_export_props_data)

def draw_props(props_owner, col, items, enabled_props):
    for item in items:
        if item in enabled_props:
            sub_row = col.row()
            sub_row.prop(props_owner, item)
            sub_row.enabled = enabled_props[item]
        else:
            col.prop(props_owner, item)

def draw_expandable_header(prop_owner, identifier, flag, layout, label):
    row = layout.row()
    row.prop(prop_owner, identifier,
        icon="TRIA_DOWN" if flag else "TRIA_RIGHT",
        icon_only=True, emboss=False
    )
    row.label(text=label)

def draw_expandable_props(context, layout, expand_flag_id, header_label,
                          prop_groups, props_owner, box_enabled, enabled_props):
    omni_nucleus = context.scene.omni_nucleus
    if not hasattr(omni_nucleus, expand_flag_id):
        print(f"WARNING: omni_nucleus has no attribute {expand_flag_id}")
        return

    expand_flag = getattr(omni_nucleus, expand_flag_id)

    main_col = layout.column()
    row = main_col.row()
    row.prop(omni_nucleus, expand_flag_id,
        icon="TRIA_DOWN" if expand_flag else "TRIA_RIGHT",
        icon_only=True, emboss=False
    )
    row.label(text=header_label)
    if expand_flag:
        for group in prop_groups:
            col = main_col.column(heading = group[0], align=True)
            draw_props(props_owner, col, group[1], enabled_props)
            col.enabled = box_enabled

class OMNI_USDImportOptions:
    """USD Import Options"""

    def draw(self, layout, context:Context):
        omni_nucleus = context.scene.omni_nucleus
        import_props = context.scene.omni_usd_import_props

        layout.use_property_split = True
        layout.use_property_decorate = False

        layout.label(text="USD Import Options")

        prop_groups = []
        prop_ids = ['prim_path_mask', 'import_visible_only', 'import_defined_only',
                    'create_collection', 'relative_path', 'apply_unit_conversion_scale',
                    'scale', 'attr_import_mode']
        prop_groups.append(("", prop_ids))
        enabled_props = {}

        draw_expandable_props(context, layout, "expand_import_general",
                              "General", prop_groups, import_props,
                              True, enabled_props)

        prop_groups = []
        prop_ids = ['import_meshes', 'import_curves', 'import_volumes', 'import_shapes',
                    'import_cameras', 'import_lights', 'import_materials']
        prop_groups.append(("", prop_ids))
        prop_ids = ['import_render', 'import_proxy', 'import_guide']
        prop_groups.append(("USD Purpose", prop_ids))
        enabled_props = {}

        draw_expandable_props(context, layout, "expand_import_types",
                              "Import Types", prop_groups, import_props,
                              True, enabled_props)

        prop_groups = []
        prop_ids = ['read_mesh_uvs', 'read_mesh_colors', 'validate_meshes', 'import_subdiv']
        prop_groups.append(("", prop_ids))
        enabled_props = {}

        draw_expandable_props(context, layout, "expand_import_geometry",
                              "Geometry", prop_groups, import_props,
                              True, enabled_props)

        prop_groups = []
        prop_ids = ['import_all_materials', 'import_shaders_mode', 'set_material_blend',
                    'mtl_name_collision_mode']
        prop_groups.append(("", prop_ids))
        enabled_props = {
            'set_material_blend' : import_props.import_shaders_mode == 'USD_PREVIEW_SURFACE',
        }

        draw_expandable_props(context, layout, "expand_import_materials",
                              "Materials", prop_groups, import_props,
                              import_props.import_materials, enabled_props)

        prop_groups = []
        prop_ids = ['import_textures_mode', 'import_textures_dir', 'tex_name_collision_mode']
        prop_groups.append(("", prop_ids))
        enabled_props = {
            'import_textures_dir' : import_props.import_textures_mode == 'IMPORT_COPY',
            'tex_name_collision_mode' : import_props.import_textures_mode == 'IMPORT_COPY',
        }

        draw_expandable_props(context, layout, "expand_import_textures",
                              "Textures", prop_groups, import_props,
                              import_props.import_materials, enabled_props)

        prop_groups = []
        prop_ids = ['convert_light_from_nits', 'scale_light_radius',
                    'create_background_shader', 'light_intensity_scale']
        prop_groups.append(("", prop_ids))
        enabled_props = {}

        draw_expandable_props(context, layout, "expand_import_lights",
                              "Lights", prop_groups, import_props,
                              import_props.import_lights, enabled_props)

        prop_groups = []
        prop_ids = ['import_skeletons', 'import_blendshapes']
        prop_groups.append(("", prop_ids))
        enabled_props = {}

        draw_expandable_props(context, layout, "expand_import_rigging",
                              "Rigging", prop_groups, import_props,
                              True, enabled_props)

        prop_groups = []
        prop_ids = ['set_frame_range']
        prop_groups.append(("", prop_ids))
        enabled_props = {}

        draw_expandable_props(context, layout, "expand_import_animation",
                              "Animation", prop_groups, import_props,
                              True, enabled_props)

        prop_groups = []
        prop_ids = ['use_instancing', 'import_instance_proxies']
        prop_groups.append(("", prop_ids))
        enabled_props = {
            'import_instance_proxies' : not import_props.use_instancing
        }

        draw_expandable_props(context, layout, "expand_import_particles_and_instancing",
                              "Particles and Instancing", prop_groups, import_props,
                              True, enabled_props)

    def init(self, context):
        omni_nucleus = context.scene.omni_nucleus
        import_props = context.scene.omni_usd_import_props

        dir = omni_nucleus.import_textures_directory

        if dir and not dir.isspace():
            import_props.import_textures_mode = 'IMPORT_COPY'
            import_props.import_textures_dir = dir.strip()


class OMNI_USDExportOptions:
    """Omniverse USD Export Options"""

    def draw(self, layout, context:Context):
        export_props = context.scene.omni_usd_export_props

        layout.label(text="USD Export Options")

        layout.use_property_split = True
        layout.use_property_decorate = False

        col = layout.column()
        col.prop(export_props, "evaluation_mode")

        prop_groups = []
        prop_ids = ['selected_objects_only', 'visible_objects_only']
        prop_groups.append(("", prop_ids))
        prop_ids = ['convert_orientation', 'export_global_forward_selection',
                    'export_global_up_selection']
        prop_groups.append(("", prop_ids))
        prop_ids = ['usdz_is_arkit', 'convert_to_cm']
        prop_groups.append(("", prop_ids))
        prop_ids = ['relative_paths']
        prop_groups.append(("External Items", prop_ids))
        prop_ids = ['export_as_overs', 'merge_transform_and_shape', 'xform_op_mode']
        prop_groups.append(("", prop_ids))
        enabled_props = {
            'export_global_forward_selection' : export_props.convert_orientation,
            'export_global_up_selection' : export_props.convert_orientation,
        }

        draw_expandable_props(context, layout, "expand_export_general",
                              "General", prop_groups, export_props,
                              True, enabled_props)

        prop_groups = []
        props = ['default_prim_path', 'root_prim_path', 'material_prim_path', 'default_prim_kind',
                 'default_prim_custom_kind']
        prop_groups.append(("", props))
        enabled_props = {
            'default_prim_custom_kind' : export_props.default_prim_kind == "CUSTOM",
        }
        draw_expandable_props(context, layout, "expand_export_stage",
                              "Stage", prop_groups, export_props,
                              True, enabled_props)

        prop_groups = []
        props = ['export_transforms', 'export_meshes', 'export_materials', 'export_lights',
                 'export_cameras', 'export_curves']
        prop_groups.append(("", props))
        enabled_props = {}
        draw_expandable_props(context, layout, "expand_export_types",
                              "Export Types", prop_groups, export_props,
                              True, enabled_props)

        prop_groups = []
        props = ['apply_subdiv', 'export_vertex_colors', 'export_vertex_groups', 'export_normals',
                 'export_uvmaps', 'convert_uv_to_st', 'triangulate_meshes', 'quad_method', 'ngon_method']
        prop_groups.append(("", props))
        enabled_props = {
            'quad_method' : export_props.triangulate_meshes,
            'ngon_method' : export_props.triangulate_meshes,
        }
        draw_expandable_props(context, layout, "expand_export_geometry",
                              "Geometry", prop_groups, export_props,
                              True, enabled_props)

        prop_groups = []
        props = ['generate_preview_surface', 'generate_cycles_shaders', 'generate_mdl', 'export_textures',
                 'overwrite_textures', 'usdz_downscale_size', 'usdz_downscale_custom_size']
        prop_groups.append(("", props))
        enabled_props = {
            'overwrite_textures' : export_props.export_textures,
            'usdz_downscale_size' : export_props.export_textures,
            'usdz_downscale_custom_size' : export_props.export_textures and
                                           export_props.usdz_downscale_size == 'CUSTOM',
            'generate_mdl' : umm_loaded()
        }

        draw_expandable_props(context, layout, "expand_export_materials",
                              "Materials", prop_groups, export_props,
                              export_props.export_materials, enabled_props)

        prop_groups = []
        props = ['light_intensity_scale', 'convert_light_to_nits', 'scale_light_radius',
                 'convert_world_material']
        prop_groups.append(("", props))
        enabled_props = {}
        draw_expandable_props(context, layout, "expand_export_lights",
                              "Lights", prop_groups, export_props,
                              export_props.export_lights, enabled_props)

        prop_groups = []
        props = ['export_armatures', 'fix_skel_root']
        prop_groups.append(("Armatures", props))
        props = ['export_blendshapes']
        prop_groups.append(("Shapes", props))
        enabled_props = {
            'fix_skel_root' : export_props.export_armatures,
        }
        draw_expandable_props(context, layout, "expand_export_rigging",
                              "Rigging", prop_groups, export_props,
                              True, enabled_props)

        prop_groups = []
        props = ['export_animation', 'start', 'end', 'frame_step']
        prop_groups.append(("", props))
        enabled_props = {
            'start' : export_props.export_animation,
            'end' : export_props.export_animation,
            'frame_step' : export_props.export_animation,
        }
        draw_expandable_props(context, layout, "expand_export_animation",
                              "Animation", prop_groups, export_props,
                              True, enabled_props)

        prop_groups = []
        props = ['export_particles', 'export_hair', 'export_child_particles']
        prop_groups.append(("Particles", props))
        props = ['use_instancing']
        prop_groups.append(("Instances", props))
        enabled_props = {
            'export_child_particles' : export_props.export_hair or
                                       export_props.export_particles,
        }
        draw_expandable_props(context, layout, "expand_export_particles_and_instancing",
                              "Particles and Instancing", prop_groups, export_props,
                              True, enabled_props)

    def init(self, context):
        global g_export_frame_range_inited
        if not g_export_frame_range_inited and context.scene:
            context.scene.omni_usd_export_props.start = context.scene.frame_start
            context.scene.omni_usd_export_props.end = context.scene.frame_end
            g_export_frame_range_inited = True
