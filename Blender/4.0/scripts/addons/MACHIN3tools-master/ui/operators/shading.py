import bpy
from bpy.props import IntProperty, StringProperty
from math import degrees, radians
from mathutils import Matrix
from ... utils.registration import get_prefs
from ... utils.light import adjust_lights_for_rendering, get_area_light_poll
from ... utils.view import sync_light_visibility
from ... utils.material import adjust_bevel_shader


render_visibility = []


class SwitchShading(bpy.types.Operator):
    bl_idname = "machin3.switch_shading"
    bl_label = "MACHIN3: Switch Shading"
    bl_options = {'REGISTER', 'UNDO'}

    shading_type: StringProperty(name="Shading Type", default='SOLID')

    # hidden (screen casting)
    toggled_overlays = False

    @classmethod
    def description(cls, context, properties):
        shading = context.space_data.shading
        overlay = context.space_data.overlay
        shading_type = properties.shading_type

        if shading.type == shading_type:
            return f"{'Disable' if overlay.show_overlays else 'Enable'} Overlays for {shading_type.capitalize()} Shading"
        else:
            return f"Switch to {shading_type.capitalize()} shading, and restore previously set Overlay Visibility"

    def execute(self, context):
        scene = context.scene

        shading = context.space_data.shading
        overlay = context.space_data.overlay

        # initiate overlay settings on/from scene level
        self.initiate_overlay_settings(context, shading, overlay)


        # toggle overlays
        if shading.type == self.shading_type:
            self.prefs[self.shading_type] = not self.prefs[self.shading_type]
            self.toggled_overlays = 'Enable' if self.prefs[self.shading_type] else 'Disable'

        # change shading to self.shading_type
        else:
            shading.type = self.shading_type
            self.toggled_overlays = False

            # adjust the lights when necessssary
            if get_prefs().activate_render and get_prefs().activate_shading_pie and get_prefs().render_adjust_lights_on_render and get_area_light_poll() and scene.M3.adjust_lights_on_render:
                self.adjust_lights(scene, shading.type, debug=False)

            if shading.type == 'RENDERED' and scene.render.engine == 'CYCLES':

                # sync light visibility
                if get_prefs().activate_render and get_prefs().render_sync_light_visibility:
                    sync_light_visibility(scene)

                # setup/adjust bevel shader
                if get_prefs().activate_render and get_prefs().activate_shading_pie and get_prefs().render_use_bevel_shader and scene.M3.use_bevel_shader:
                    adjust_bevel_shader(context)

            # enforce hide_render when viewport rendering
            if get_prefs().activate_render and get_prefs().activate_shading_pie and get_prefs().render_enforce_hide_render and scene.M3.enforce_hide_render:
                self.enforce_render_visibility(context, shading.type, debug=True)

        # actually set overlay visibility now
        overlay.show_overlays = self.prefs[self.shading_type]
        return {'FINISHED'}


    # UITLS

    def initiate_overlay_settings(self, context, shading, overlay, debug=False):
        '''
        ensure show_overlay_prefs is stored on the scene level
        create reference to it on the ob via self.prefs
        check if it's out of sync for the current shading type, which can happen if the user toggles overlay using native Blender UI maybe, and correct it
        '''
        
        if not context.scene.M3.get('show_overlay_prefs', False):
            if debug:
                print("initiating overlays prefs on scene object")

            context.scene.M3['show_overlay_prefs'] = {'SOLID': True,
                                                      'MATERIAL': False,
                                                      'RENDERED': False,
                                                      'WIREFRAME': True}

        self.prefs = context.scene.M3['show_overlay_prefs']

        # correct out of sync settings
        if overlay.show_overlays != self.prefs[shading.type]:
            self.prefs[shading.type] = overlay.show_overlays
            print("INFO: Corrected out-of-sync Overlay Visibility setting!")


    def adjust_lights(self, scene, new_shading_type, debug=False):
        m3 = scene.M3

        last = m3.adjust_lights_on_render_last

        # print("last:", last)
        # print("new shading type:", new_shading_type)
        # print("render engine:", scene.render.engine)

        # decrease on start of rendering
        if last in ['NONE', 'INCREASE'] and new_shading_type == 'RENDERED' and scene.render.engine == 'CYCLES':
            m3.adjust_lights_on_render_last = 'DECREASE'

            if debug:
                print("decreasing on switch to cycies rendering")

            adjust_lights_for_rendering(mode='DECREASE')


        elif last == 'DECREASE' and new_shading_type == 'MATERIAL':
            m3.adjust_lights_on_render_last = 'INCREASE'

            if debug:
                print("increasing on switch to material shading")

            adjust_lights_for_rendering(mode='INCREASE')

    def enforce_render_visibility(self, context, new_shading_type, debug=False):
        global render_visibility

        # print()
        # print("new shading type:", new_shading_type)
        # print("render visibility:", [(obj, name) for obj, name in render_visibility])

        # hide objects that shouldn't render
        if new_shading_type == 'RENDERED':
            render_visibility = [(obj, obj.name) for obj in context.visible_objects if obj.hide_render == True and obj.visible_get()]

            for obj, name in render_visibility:
                # print("hiding:", name)
                obj.hide_set(True)
        else:

            for obj, name in render_visibility:
                obj = bpy.data.objects.get(name)

                if obj:
                    # print("unhiding:", name)
                    obj.hide_set(False)
                else:
                    print(f"WARNING: Object {name} could no longer be found")

            render_visibility = []


class ToggleOutline(bpy.types.Operator):
    bl_idname = "machin3.toggle_outline"
    bl_label = "Toggle Outline"
    bl_description = "Toggle Object Outlines"
    bl_options = {'REGISTER'}

    def execute(self, context):
        shading = context.space_data.shading

        shading.show_object_outline = not shading.show_object_outline

        return {'FINISHED'}


class ToggleCavity(bpy.types.Operator):
    bl_idname = "machin3.toggle_cavity"
    bl_label = "Toggle Cavity"
    bl_description = "Toggle Cavity (Screen Space Ambient Occlusion)"
    bl_options = {'REGISTER'}

    def execute(self, context):
        scene = context.scene

        scene.M3.show_cavity = not scene.M3.show_cavity

        return {'FINISHED'}


class ToggleCurvature(bpy.types.Operator):
    bl_idname = "machin3.toggle_curvature"
    bl_label = "Toggle Curvature"
    bl_description = "Toggle Curvature (Edge Highlighting)"
    bl_options = {'REGISTER'}

    def execute(self, context):
        scene = context.scene

        scene.M3.show_curvature = not scene.M3.show_curvature

        return {'FINISHED'}


matcap1_color_type = None


class MatcapSwitch(bpy.types.Operator):
    bl_idname = "machin3.matcap_switch"
    bl_label = "Matcap Switch"
    bl_description = "Quickly Switch between two Matcaps"
    bl_options = {'REGISTER'}

    @classmethod
    def poll(cls, context):
        if context.space_data.type == 'VIEW_3D':
            shading = context.space_data.shading
            return shading.type == "SOLID" and shading.light == "MATCAP"

    def execute(self, context):
        view = context.space_data
        shading = view.shading

        matcap1 = get_prefs().switchmatcap1
        matcap2 = get_prefs().switchmatcap2

        switch_background = get_prefs().matcap_switch_background

        force_single = get_prefs().matcap2_force_single
        global matcap1_color_type

        disable_overlays = get_prefs().matcap2_disable_overlays

        if matcap1 and matcap2 and "NOT FOUND" not in [matcap1, matcap2]:
            if shading.studio_light == matcap1:
                shading.studio_light = matcap2

                if switch_background:
                    shading.background_type = get_prefs().matcap2_switch_background_type

                    if get_prefs().matcap2_switch_background_type == 'VIEWPORT':
                        shading.background_color = get_prefs().matcap2_switch_background_viewport_color

                if force_single and shading.color_type != 'SINGLE':
                    matcap1_color_type = shading.color_type
                    shading.color_type = 'SINGLE'

                if disable_overlays and view.overlay.show_overlays:
                    view.overlay.show_overlays = False

            elif shading.studio_light == matcap2:
                shading.studio_light = matcap1

                if switch_background:
                    shading.background_type = get_prefs().matcap1_switch_background_type

                    if get_prefs().matcap1_switch_background_type == 'VIEWPORT':
                        shading.background_color = get_prefs().matcap1_switch_background_viewport_color

                if force_single and matcap1_color_type:
                    shading.color_type = matcap1_color_type
                    matcap1_color_type = None

                if disable_overlays and not view.overlay.show_overlays:
                    view.overlay.show_overlays = True

            else:
                shading.studio_light = matcap1

        return {'FINISHED'}


class RotateStudioLight(bpy.types.Operator):
    bl_idname = "machin3.rotate_studiolight"
    bl_label = "MACHIN3: Rotate Studiolight"
    bl_options = {'REGISTER', 'UNDO'}

    angle: IntProperty(name="Angle")

    @classmethod
    def description(cls, context, properties):
        return "Rotate Studio Light by %d degrees\nALT: Rotate visible lights too" % (int(properties.angle))

    def invoke(self, context, event):
        current = degrees(context.space_data.shading.studiolight_rotate_z)
        new = (current + self.angle)

        # deal with angles beyond 360
        if new > 360:
            new = new % 360

        # shift angle into blender's -180 to 180 range
        if new > 180:
            new = -180 + (new - 180)

        context.space_data.shading.studiolight_rotate_z = radians(new)

        if event.alt:
            rmx = Matrix.Rotation(radians(self.angle), 4, 'Z')
            lights = [obj for obj in context.visible_objects if obj.type == 'LIGHT']

            for light in lights:
                light.matrix_world = rmx @ light.matrix_world

        return {'FINISHED'}
