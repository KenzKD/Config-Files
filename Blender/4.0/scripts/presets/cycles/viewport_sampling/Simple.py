import bpy
cycles = bpy.context.scene.cycles

cycles.use_preview_adaptive_sampling = True
cycles.preview_samples = 32
cycles.preview_adaptive_threshold = 0.10000000149011612
cycles.preview_adaptive_min_samples = 0
cycles.use_preview_denoising = True
cycles.preview_denoiser = 'OPTIX'
cycles.preview_denoising_input_passes = 'RGB_ALBEDO_NORMAL'
cycles.preview_denoising_prefilter = 'FAST'
cycles.preview_denoising_start_sample = 1
