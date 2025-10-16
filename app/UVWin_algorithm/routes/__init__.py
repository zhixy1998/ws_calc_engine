from fastapi import APIRouter
from . import least_squares_fitting
from . import calculate_concentration_or_abs
from . import algebraic_operations
from . import get_peak
from . import spectral_arithmetic_operations
from . import spectrum_transform
from . import detect_step_skipe
from . import smoothed
from . import differentiated
from . import get_valley
from . import get_peaks_and_valleys
from . import excel_smooth_plot

router = APIRouter()


router.include_router(least_squares_fitting.router, prefix="/least_squares_fitting", tags=["最小二乘拟合"])
router.include_router(calculate_concentration_or_abs.router, prefix='/calculate_concentration_or_abs', tags=["计算浓度或吸光率"])
router.include_router(algebraic_operations.router, prefix='/algebraic_operations', tags=['代数运算，用户自定义运算'])
router.include_router(get_peak.router, prefix='/get_peak', tags=['寻峰'])
router.include_router(get_valley.router, prefix='/get_valley', tags=['寻谷'])
router.include_router(get_peaks_and_valleys.router, prefix='/get_peaks_and_valleys', tags=['同时寻峰寻谷'])
router.include_router(spectral_arithmetic_operations.router, prefix='/spectral_arithmetic_operations', tags=['谱图的四则运算'])
router.include_router(spectrum_transform.router, prefix='/spectrum_transform', tags=['谱图变换'])
router.include_router(detect_step_skipe.router, prefix='/detect_step_skipe', tags=['消除台阶或者倒刺'])
router.include_router(smoothed.router, prefix='/smoothed', tags=['平滑'])
router.include_router(differentiated.router, prefix='/differentiated', tags=['微分'])
router.include_router(excel_smooth_plot.router, prefix='/excel_smooth_plot', tags=['Excel平滑并绘制图表'])