from fastapi import APIRouter
from . import least_squares_fitting
from . import calculate_concentration_or_abs
from . import algebraic_operations
from . import get_peak
from . import spectral_arithmetic_operations


router = APIRouter()


router.include_router(least_squares_fitting.router, prefix="/least_squares_fitting", tags=["最小二乘拟合"])
router.include_router(calculate_concentration_or_abs.router, prefix='/calculate_concentration_or_abs', tags=["计算浓度或吸光率"])
router.include_router(algebraic_operations.router, prefix='/algebraic_operations', tags=['代数运算，用户自定义运算'])
router.include_router(get_peak.router, prefix='/get_peak', tags=['寻峰'])