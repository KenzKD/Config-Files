import bpy
cycles = bpy.context.scene.cycles

cycles.use_adaptive_sampling = True
cycles.samples = 256
cycles.adaptive_threshold = 0.009999999776482582
cycles.adaptive_min_samples = 0
cycles.time_limit = 0.0
cycles.use_denoising = True
cycles.denoiser = 'OPTIX'
cycles.denoising_input_passes = 'RGB_ALBEDO_NORMAL'
cycles.denoising_prefilter = 'ACCURATE'
