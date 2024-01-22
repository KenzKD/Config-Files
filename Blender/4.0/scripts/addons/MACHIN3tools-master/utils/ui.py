import bpy
import rna_keymap_ui
from mathutils import Vector
from bpy_extras.view3d_utils import region_2d_to_location_3d, location_3d_to_region_2d
from bl_ui.space_statusbar import STATUSBAR_HT_header as statusbar
from . registration import get_prefs
from time import time


icons = None


def get_icon(name):
    global icons

    if not icons:
        from .. import icons

    return icons[name].icon_id


# MOUSE

def get_mouse_pos(self, context, event, hud=True, hud_offset=(20, 20)):
    '''
    get and set the current mouse position (region space)
    optionally
        create an offset vector too, based on the wm.HC_mouse_pos_region prop, this would be used in an operator's invoke() only
        set HUD_x and HUD_y props for HUD drawing
    '''

    self.mouse_pos = Vector((event.mouse_region_x, event.mouse_region_y))

    if hud:
        scale = context.preferences.system.ui_scale * get_prefs().modal_hud_scale

        self.HUD_x = self.mouse_pos.x + hud_offset[0] * scale
        self.HUD_y = self.mouse_pos.y + hud_offset[1] * scale


def wrap_mouse(self, context, x=False, y=False):
    '''
    wrap mouse to other side of the region
    works on self.mouse_pos which are expected to exist, and which are in region space of course
    '''

    width = context.region.width
    height = context.region.height

    # copy the curretn mouse location
    mouse = self.mouse_pos.copy()

    # check for x wrapping
    if x:
        if mouse.x <= 0:
            mouse.x = width - 10

        elif mouse.x >= width - 1:  # the -1 is required for full screen, where the max region width is never passed
            mouse.x = 10

    # check for y wrapping, as long as x wasn't wrapped already
    if y and mouse == self.mouse_pos:
        if mouse.y <= 0:
            mouse.y = height - 10

        elif mouse.y >= height - 1:
            mouse.y = 10

    # actually warp the mouse ot the other side now, IF mouse differs from self.mouse_pos now
    if mouse != self.mouse_pos:
        # print()
        # print("warping --- woooosh")
        warp_mouse(self, context, mouse)


def warp_mouse(self, context, co2d=Vector(), region=True, hud_offset=(20, 20)):
    '''
    warp mouse to passed in co2d
       which by default is expected to be in region space
       and so will be converted to window space accordingly, which is what context.window.cursior_warp() expects
    '''

    coords = get_window_space_co2d(context, co2d) if region else co2d

    # engage!
    context.window.cursor_warp(int(coords.x), int(coords.y))

    # set mouse_pos prop on operator
    self.mouse_pos = co2d if region else get_region_space_co2d(context, co2d)

    # self.last_mouse too, if present
    if getattr(self, 'last_mouse', None):
        self.last_mouse = self.mouse_pos

    # HUD coords too, if present
    if getattr(self, 'HUD_x', None):
        scale = context.preferences.system.ui_scale * get_prefs().modal_hud_scale

        self.HUD_x = self.mouse_pos.x + hud_offset[0] * scale
        self.HUD_y = self.mouse_pos.y + hud_offset[1] * scale


def get_window_space_co2d(context, co2d=Vector()):
    '''
    using the region x and y, convert the passed in (mouse) coords from region into absolute (blender-window) space
    '''

    return co2d + Vector((context.region.x, context.region.y))


def get_region_space_co2d(context, co2d=Vector()):
    '''
    using the region x and y, convert the passed in (mouse) coords from absolute (blender-window) to region space
    '''

    return Vector((context.region.x, context.region.y)) - co2d






# CURSOR - TODO: remove

def init_cursor(self, event, offsetx=0, offsety=20):
    self.last_mouse_x = event.mouse_x
    self.last_mouse_y = event.mouse_y

    # region offsets
    self.region_offset_x = event.mouse_x - event.mouse_region_x
    self.region_offset_y = event.mouse_y - event.mouse_region_y

    # init HUD location (at mouse)
    self.HUD_x = event.mouse_x - self.region_offset_x + offsetx
    self.HUD_y = event.mouse_y - self.region_offset_y + offsety


def wrap_cursor(self, context, event, x=False, y=False):
    if x:

        if event.mouse_region_x <= 0:
            context.window.cursor_warp(context.region.width + self.region_offset_x - 10, event.mouse_y)

        if event.mouse_region_x >= context.region.width - 1:  # the -1 is required for full screen, where the max region width is never passed
            context.window.cursor_warp(self.region_offset_x + 10, event.mouse_y)


        """
        if event.mouse_region_x > context.region.width - 2:
            context.window.cursor_warp(event.mouse_x - context.region.width + 2, event.mouse_y)
            self.last_mouse_x -= context.region.width

        elif event.mouse_region_x < 1:
            context.window.cursor_warp(event.mouse_x + context.region.width - 2, event.mouse_y)
            self.last_mouse_x += context.region.width
        """

    if y:
        if event.mouse_region_y <= 0:
            context.window.cursor_warp(event.mouse_x, context.region.height + self.region_offset_y - 10)

        if event.mouse_region_y >= context.region.height - 1:
            context.window.cursor_warp(event.mouse_x, self.region_offset_y + 100)

        """
        if event.mouse_region_y > context.region.height - 2:
            context.window.cursor_warp(event.mouse_x, event.mouse_y - context.region.height + 2)
            self.last_mouse_y -= context.region.height

        elif event.mouse_region_y < 1:
            context.window.cursor_warp(event.mouse_x, event.mouse_y + context.region.height - 2)
            self.last_mouse_y += context.region.height
        """


# POPUP

def popup_message(message, title="Info", icon="INFO", terminal=True):
    def draw_message(self, context):
        if isinstance(message, list):
            for m in message:
                self.layout.label(text=m)
        else:
            self.layout.label(text=message)

    bpy.context.window_manager.popup_menu(draw_message, title=title, icon=icon)

    if terminal:
        if icon == "FILE_TICK":
            icon = "ENABLE"
        elif icon == "CANCEL":
            icon = "DISABLE"
        print(icon, title)

        if isinstance(message, list):
            print(" »", ", ".join(message))
        else:
            print(" »", message)


# ZOOM FACTOR

def get_zoom_factor(context, depth_location, scale=10, ignore_obj_scale=False):
    '''
    get factor to scale 3dview items to behave as if in screen space
    '''

    center = Vector((context.region.width / 2, context.region.height / 2))
    offset = center + Vector((scale, 0))

    # NOTE: this can through an exception in some rare cases
    #   File "/opt/blender-3.6.2-linux-x64/3.6/scripts/modules/bpy_extras/view3d_utils.py", line 127, in region_2d_to_location_3d
    # coord_vec = region_2d_to_vector_3d(region, rv3d, coord)
    # File "/opt/blender-3.6.2-linux-x64/3.6/scripts/modules/bpy_extras/view3d_utils.py", line 30, in region_2d_to_vector_3d
    # persinv = rv3d.perspective_matrix.inverted()
    try:
        center_3d = region_2d_to_location_3d(context.region, context.region_data, center, depth_location)
        offset_3d = region_2d_to_location_3d(context.region, context.region_data, offset, depth_location)
    except:
        print("exception!")
        return 1

    # draw_point(center_3d, color=(1, 1, 0), modal=False)
    # draw_point(offset_3d, color=(1, 0, 0), modal=False)

    # take object scaling into account
    if not ignore_obj_scale and context.active_object:
        mx = context.active_object.matrix_world.to_3x3()
        zoom_vector = mx.inverted_safe() @ Vector(((center_3d - offset_3d).length, 0, 0))
        return zoom_vector.length
    return (center_3d - offset_3d).length


# HUD

def get_flick_direction(context, mouse_loc_3d, flick_vector, axes):
    # origin_2d = location_3d_to_region_2d(context.region, context.region_data, self.origin)
    origin_2d = location_3d_to_region_2d(context.region, context.region_data, mouse_loc_3d, default=Vector((context.region.width / 2, context.region.height / 2)))

    axes_2d = {}

    for direction, axis in axes.items():
        # print(direction, axis)

        # axis_2d = location_3d_to_region_2d(context.region, context.region_data, self.origin + axis)
        axis_2d = location_3d_to_region_2d(context.region, context.region_data, mouse_loc_3d + axis, default=origin_2d)

        # avoid zero length vectors from ortho views
        if (axis_2d - origin_2d).length:
            axes_2d[direction] = (axis_2d - origin_2d).normalized()

    return min([(d, abs(flick_vector.xy.angle_signed(a))) for d, a in axes_2d.items()], key=lambda x: x[1])[0]


# HEADER

def require_header_offset(context, top=True):
    '''
    determine if anything written at the top of the screen requires an additional offset due to the presense of tool options

    depending on the Blender version, this varies
    get the header(2.03) or tool_header(3.0), but only if it's y location is under (bottom) / above (top) the halve the height of the area
    '''

    area = context.area
    headers = [r for r in area.regions if r.type == ('HEADER' if bpy.app.version < (3, 0, 0) else 'TOOL_HEADER') and ((r.y > area.height / 2) if top else (r.y < area.height / 2))]

    if headers:

        # in 2.93 we need to check if the tool header is hidden, to determine if an offset should be used
        if bpy.app.version < (3, 0, 0):
            return not context.space_data.show_region_tool_header

        # in 3.0,0 we need to check if the tool header is shown
        else:
            return context.space_data.show_region_tool_header


# KEYMAPS

def kmi_to_string(kmi, docs_mode=False):
    '''
    return keymap item as printable string
    '''

    kmi_str = f"{kmi.idname}, name: {kmi.name}, active: {kmi.active}, map type: {kmi.map_type}, type: {kmi.type}, value: {kmi.value}, alt: {kmi.alt}, ctrl: {kmi.ctrl}, shift: {kmi.shift}, properties: {str(dict(kmi.properties))}"

    if docs_mode:
        return f"`{kmi_str}`"
    else:
        return kmi_str


def draw_keymap_items(kc, name, keylist, layout):
    drawn = []

    # index keeping track of SUCCESSFULL kmi iterations
    idx = 0

    for item in keylist:
        keymap = item.get("keymap")
        isdrawn = False

        if keymap:
            km = kc.keymaps.get(keymap)

            kmi = None
            if km:
                idname = item.get("idname")

                for kmitem in km.keymap_items:
                    if kmitem.idname == idname:
                        properties = item.get("properties")

                        if properties:
                            if all([getattr(kmitem.properties, name, None) == value for name, value in properties]):
                                kmi = kmitem
                                break

                        else:
                            kmi = kmitem
                            break

            # draw keymap item

            if kmi:
                # multi kmi tools, will share a single box, created for the first kmi
                if idx == 0:
                    box = layout.box()

                # single kmi tools, get their label from the title
                if len(keylist) == 1:
                    label = name.title().replace("_", " ")

                # multi kmi tools, get it from the label tag, while the title is printed once, before the first item
                else:
                    if idx == 0:
                        box.label(text=name.title().replace("_", " "))

                    label = item.get("label")

                row = box.split(factor=0.15)
                row.label(text=label)

                # layout.context_pointer_set("keymap", km)
                rna_keymap_ui.draw_kmi(["ADDON", "USER", "DEFAULT"], kc, km, kmi, row, 0)

                # draw info, if available
                infos = item.get("info", [])
                for text in infos:
                    row = box.split(factor=0.15)
                    row.separator()
                    row.label(text=text, icon="INFO")

                isdrawn = True
                idx += 1

        drawn.append(isdrawn)

    return any(d for d in drawn)


def get_keymap_item(name, idname, key=None, alt=False, ctrl=False, shift=False, properties=[]):
    wm = bpy.context.window_manager
    kc = wm.keyconfigs.user

    km = kc.keymaps.get(name)

    if bpy.app.version >= (3, 0, 0):
        alt = int(alt)
        ctrl = int(ctrl)
        shift = int(shift)

    if km:
        kmi = km.keymap_items.get(idname)

        if kmi:
            found = True if key is None else all([kmi.type == key and kmi.alt is alt and kmi.ctrl is ctrl and kmi.shift is shift])

            if found:
                if properties:
                    if all([getattr(kmi.properties, name, False) == prop for name, prop in properties]):
                        return kmi
                else:
                    return kmi


# STATUS BAR

def init_status(self, context, title='', func=None):
    self.bar_orig = statusbar.draw

    if func:
        statusbar.draw = func
    else:
        statusbar.draw = draw_basic_status(self, context, title)


def draw_basic_status(self, context, title):
    def draw(self, context):
        layout = self.layout

        row = layout.row(align=True)
        row.label(text=title)

        row.label(text="", icon='MOUSE_LMB')
        row.label(text="Finish")

        if context.window_manager.keyconfigs.active.name.startswith('blender'):
            row.label(text="", icon='MOUSE_MMB')
            row.label(text="Viewport")

        row.label(text="", icon='MOUSE_RMB')
        row.label(text="Cancel")

    return draw


def finish_status(self):
    statusbar.draw = self.bar_orig


# MODAL

def init_timer_modal(self, debug=False):

    # set start value from current system time
    self.start = time()

    # init countdown from operators time prop, and factor in any user based timeout modulation
    self.countdown = self.time * get_prefs().modal_hud_timeout

    if debug:
        print(f"initiating timer with a countdown of {self.time}s ({self.time * get_prefs().modal_hud_timeout}s)")


def set_countdown(self, debug=False):
    '''
    set the operators countdown prop, based on the time passed since init_timer_modal() was called
    '''
    
    self.countdown = self.time * get_prefs().modal_hud_timeout - (time() - self.start)

    if debug:
        print("countdown:", self.countdown)


def get_timer_progress(self, debug=False):
    '''
    get timer progress, expressed on a range of 0-1
    '''

    progress =  self.countdown / (self.time * get_prefs().modal_hud_timeout)

    if debug:
        print("progress:", progress)

    return progress

