import bpy
cycles = bpy.context.scene.cycles

cycles.max_bounces = 3
cycles.diffuse_bounces = 1
cycles.glossy_bounces = 1
cycles.transmission_bounces = 3
cycles.volume_bounces = 3
cycles.transparent_max_bounces = 3
cycles.caustics_reflective = True
cycles.caustics_refractive = True
cycles.blur_glossy = 1.0
cycles.use_fast_gi = True
cycles.ao_bounces = 1
cycles.ao_bounces_render = 1
