import bpy
import bgl
import gpu
from mathutils import Vector
from . text import Draw_Text, Draw_Text_Wrap, SetSizeGetDim
if not bpy.app.background:
    from . rectangle import Draw_Rectangle
    from . image import Draw_Image
from . utils import spacecoordstoscreencoords, get_armature_object


def draw_callback_px(self, context):
    try:
        if self.area != context.area:
            return
    except ReferenceError as e:
        print(e)
        return
    if not context or not hasattr(context, 'area') or not context.area or not hasattr(context, 'scene') or context.scene == None:
        print("Unsafe context!")
        return
    arm_obj = get_armature_object(context)
    if not arm_obj:
        return
    guide_props = context.scene.blenrig_guide
    mw = arm_obj.matrix_world
    color = (1, 0, 0, 1)
    for b in self.bones_to_display:
        # OLD: mw @ b.matrix @ b.location
        cxy = spacecoordstoscreencoords(context, (mw @ b.matrix).to_translation())
        if cxy:
            dim = SetSizeGetDim(0, 64 * self.scale, 72, '•')
            _cxy = cxy-Vector((dim[0]*0.5, dim[1]*1.22))
            Draw_Text(*_cxy, '•', 64 * self.scale, 72, 0, *color) # dim[0]/2, dim[1]*1.25
            dim = SetSizeGetDim(0, 48 * self.scale, 72, '○')
            _cxy = cxy-Vector((dim[0]*0.5, dim[1]*0.32))
            Draw_Text(*_cxy, '○', 48 * self.scale, 72, 0, 0,0,0,1)
    gpu.state.blend_set('ALPHA')
    # Fondo.
    if not bpy.app.background:
        Draw_Rectangle(self.widget_pos, self.widget_size, (0, 0, 0, .5))

    # Cabecera.
    margin = 5 * self.scale
    p = self.widget_pos+Vector((0, self.widget_size.y))-Vector((0, self.header_height))
    s = Vector((self.widget_size.x, self.header_height))
    if not bpy.app.background:
        Draw_Rectangle(p, s, (.12, .12, .12, 1))

    text = self.title
    dim = SetSizeGetDim(0, 16 * self.scale, 72, '#')
    Draw_Text(*p + Vector((margin*2, margin/2+dim[1]/2)), text, 13 * self.scale, 72, 0, 1, 1, 1, 1)

    # Imagen.
    gpu.state.blend_set('ALPHA')
    if not bpy.app.background:
        Draw_Rectangle(self.widget_pos+Vector((0, self.text_box_height)), self.image_size, (0, 0, 0, .9))

    if guide_props.active_image:
        Draw_Image(self.widget_pos+Vector((5, self.text_box_height+5)), self.image_size-Vector((10, 10)), guide_props.active_image)

    # Caja de texto.
    s = Vector((self.widget_size.x, self.text_box_height))
    if not bpy.app.background:
        Draw_Rectangle(self.widget_pos, s, (.12, .12, .12, 1))

    dim = SetSizeGetDim(0, 12 * self.scale, 72, self.text)
    p = self.widget_pos + Vector((margin, -margin + s.y - dim[1]))
    sx = int(s.x - margin * 2)
    Draw_Text_Wrap(*p, sx, self.text, 12 * self.scale, 72, 0, 1, 1, 1, 1)

    # Para cerrar y finalizar.
    dim = SetSizeGetDim(0, self.button_text_size * self.scale, 72, 'x')
    if not bpy.app.background:
        Draw_Rectangle(self.x_button_pos, [self.button_size.y]*2, (.4, .4, .4, .6))
    Draw_Text(self.x_button_pos.x + self.button_size.y / 2 - dim[0] / 2, self.x_button_pos.y + self.button_size.y / 2 - dim[1] / 2, 'x', self.button_text_size * self.scale, 72, 0, 1, 1, 1, 1)

    # Botoncito para pasar anterior y siguiente paso.
    dim = SetSizeGetDim(0, self.button_text_size * self.scale, 72, self.prev_button_text)
    
    if not bpy.app.background:
        Draw_Rectangle(self.prev_button_pos, self.button_size, (.4, .4, .4, .6))
    Draw_Text(self.prev_button_pos.x + self.button_size.x / 2 - dim[0] / 2, self.prev_button_pos.y + self.button_size.y / 2 - dim[1] / 2, self.prev_button_text, self.button_text_size * self.scale, 72, 0, 1, 1, 1, 1)
    if not self.prev_button_enabled:
        gpu.state.blend_set('ALPHA')
        if not bpy.app.background:
            Draw_Rectangle(self.prev_button_pos, self.button_size, (.08, .08, .08, .8))

    dim = SetSizeGetDim(0, self.button_text_size * self.scale, 72, self.next_button_text)
    if not bpy.app.background:
        Draw_Rectangle(self.next_button_pos, self.button_size, (.4, .4, .4, .6))
    Draw_Text(self.next_button_pos.x + self.button_size.x / 2 - dim[0] / 2, self.next_button_pos.y + self.button_size.y / 2 - dim[1] / 2, self.next_button_text, self.button_text_size * self.scale, 72, 0, 1, 1, 1, 1)
    if not self.next_button_enabled:
        gpu.state.blend_set('ALPHA')
        if not bpy.app.background:
            Draw_Rectangle(self.next_button_pos, self.button_size, (.08, .08, .08, .8))

    gpu.state.blend_set('NONE')
