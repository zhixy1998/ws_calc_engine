
import io
import matplotlib
import pandas as pd
from typing import Optional
import matplotlib.pyplot as plt

from pydantic import BaseModel, Field
from scipy.signal import savgol_filter
from fastapi.responses import StreamingResponse
from fastapi import APIRouter, UploadFile, File, Form

from exceptions.error import ErrorCode
from exceptions.command_exception import APIException

matplotlib.use('Agg')  # Use non-interactive backend
# 设置中文字体支持
plt.rcParams['font.sans-serif'] = ['Arial Unicode MS', 'SimHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False



router = APIRouter()


class ExcelInputSchema(BaseModel):
    window_length: Optional[int] = Field(5, description='平滑窗口长度')
    polyorder: Optional[int] = Field(3, description='多项式阶数')
    round_num: int = Field(4, description='小数点后几位')


class PlotOutputData(BaseModel):
    image_base64: str = Field(..., description="生成的图片(base64编码)")
    smoothed_data: dict = Field(..., description="平滑后的数据")


class PlotOutputSchema(BaseModel):
    code: int = Field(..., description="状态码")
    message: Optional[str] = Field(..., description="消息")
    data: PlotOutputData = Field(..., description='返回数据')
    

@router.post('/plot')
async def smooth_excel_data_and_plot(
    file: UploadFile = File(..., description="Excel文件"),
    window_length: int = Form(5, description="平滑窗口长度"),
    polyorder: int = Form(3, description="多项式阶数"),
    round_num: int = Form(4, description="小数点后几位"),
    title: str = Form("多系列数据平滑处理结果", description="图表标题")
):
    """
    处理Excel文件，平滑多个Y数据系列，并返回图片
    
    Excel文件格式要求：
    - 第一行：表头
    - 第二行开始：数据行
    - 每行第一列：X值
    - 每行其余列：Y值（可以有多个Y系列）
    """
    try:
        # 验证文件类型
        if not file.filename or not file.filename.endswith(('.xlsx', '.xls')):
            raise APIException(ErrorCode.PARAMETER_ERROR, "请上传Excel文件(.xlsx或.xls格式)")
        
        # 验证文件大小
        if file.size and file.size > 10 * 1024 * 1024:  # 10MB限制
            raise APIException(ErrorCode.PARAMETER_ERROR, "文件大小不能超过10MB")
        
        # 读取Excel文件
        try:
            contents = await file.read()
            # 重置文件指针
            await file.seek(0)
            df = pd.read_excel(io.BytesIO(contents))
        except UnicodeDecodeError:
            raise APIException(ErrorCode.PARAMETER_ERROR, "文件编码错误，请确保上传的是有效的Excel文件")
        except Exception as read_error:
            raise APIException(ErrorCode.PARAMETER_ERROR, f"无法读取Excel文件: {str(read_error)}")
        
        if df.empty:
            raise APIException(ErrorCode.PARAMETER_ERROR, "Excel文件为空")
        
        # 获取列名
        columns = df.columns.tolist()
        if len(columns) < 2:
            raise APIException(ErrorCode.PARAMETER_ERROR, "Excel文件至少需要2列数据（X和Y）")
        
        # 第一列作为X，其余列作为Y
        x_column = columns[0]
        y_columns = columns[1:]
        
        x_data = df[x_column].values
        
        # 验证数据
        if len(x_data) < window_length:
            raise APIException(ErrorCode.PARAMETER_ERROR, f"数据点数量({len(x_data)})小于窗口长度({window_length})")
        
        # 创建图形
        plt.figure(figsize=(12, 8))
        
        smoothed_data = {}
        colors = plt.cm.tab20(range(len(y_columns)))  # 使用不同颜色
        
        # 处理每个Y系列
        for i, y_column in enumerate(y_columns):
            y_data = df[y_column].values
            
            # 检查是否有NaN值
            if pd.isna(y_data).any():
                # 移除NaN值对应的x和y
                mask = ~pd.isna(y_data)
                x_clean = x_data[mask]
                y_clean = y_data[mask]
            else:
                x_clean = x_data
                y_clean = y_data
            
            if len(y_clean) < window_length:
                continue  # 跳过数据点不足的系列
            
            # 平滑处理
            y_smooth = savgol_filter(y_clean, window_length=window_length, polyorder=polyorder)
            
            # 绘制原始数据和平滑数据
            # plt.plot(x_clean, y_clean, 'o-', alpha=0.3, color=colors[i], 
            #         label=f'{y_column} (原始)', markersize=3)
            plt.plot(x_clean, y_smooth, '-', linewidth=2, color=colors[i], 
                    label=f'{y_column} (平滑)', alpha=0.8)
            
            # 保存平滑后的数据
            smoothed_data[y_column] = {
                'x': [round(float(x), round_num) for x in x_clean.tolist()],
                'y_original': [round(float(y), round_num) for y in y_clean.tolist()],
                'y_smoothed': [round(float(y), round_num) for y in y_smooth.tolist()]
            }
        
        # 设置图形属性
        plt.xlabel(x_column, fontsize=12)
        # plt.ylabel('Y值', fontsize=12)
        plt.title(title, fontsize=14, fontweight='bold')
        plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
        plt.grid(True, alpha=0.3)
        
        # 设置Y轴刻度间隔为0.1
        y_min = min([min(smoothed_data[col]['y_smoothed']) for col in smoothed_data.keys()])
        y_max = max([max(smoothed_data[col]['y_smoothed']) for col in smoothed_data.keys()])
        plt.ylim(y_min - 0.1, y_max + 0.1)  # 稍微扩展范围
        plt.yticks([i * 0.1 for i in range(int((y_min - 0.1) * 10), int((y_max + 0.1) * 10) + 1)])
        
        plt.tight_layout()
        
        # 将图片保存到内存缓冲区
        img_buffer = io.BytesIO()
        plt.savefig(img_buffer, format='png', dpi=300, bbox_inches='tight')
        img_buffer.seek(0)
        plt.close()  # 关闭图形以释放内存
        
        # 返回图片文件流
        return StreamingResponse(
            io.BytesIO(img_buffer.getvalue()),
            media_type="image/png",
            headers={"Content-Disposition": "attachment; filename=smoothed_plot.png"}
        )
        
    except APIException:
        raise
    except UnicodeDecodeError:
        raise APIException(ErrorCode.PARAMETER_ERROR, "文件编码错误，请上传有效的Excel文件")
    except Exception as e:
        raise APIException(ErrorCode.SYSTEM_ERROR, f"处理Excel文件时发生错误: {str(e)}")
    finally:
        # 确保文件被关闭
        if 'file' in locals():
            await file.close()


@router.post('/data', response_model=PlotOutputSchema)
async def smooth_excel_data_only(
    file: UploadFile = File(..., description="Excel文件"),
    window_length: int = Form(5, description="平滑窗口长度"),
    polyorder: int = Form(3, description="多项式阶数"),
    round_num: int = Form(4, description="小数点后几位")
):
    """
    处理Excel文件，平滑多个Y数据系列，只返回数据不生成图片
    
    Excel文件格式要求：
    - 第一行：表头
    - 第二行开始：数据行
    - 每行第一列：X值
    - 每行其余列：Y值（可以有多个Y系列）
    """
    try:
        # 验证文件类型
        if not file.filename or not file.filename.endswith(('.xlsx', '.xls')):
            raise APIException(ErrorCode.PARAMETER_ERROR, "请上传Excel文件(.xlsx或.xls格式)")
        
        # 验证文件大小
        if file.size and file.size > 10 * 1024 * 1024:  # 10MB限制
            raise APIException(ErrorCode.PARAMETER_ERROR, "文件大小不能超过10MB")
        
        # 读取Excel文件
        try:
            contents = await file.read()
            # 重置文件指针
            await file.seek(0)
            df = pd.read_excel(io.BytesIO(contents))
        except UnicodeDecodeError:
            raise APIException(ErrorCode.PARAMETER_ERROR, "文件编码错误，请确保上传的是有效的Excel文件")
        except Exception as read_error:
            raise APIException(ErrorCode.PARAMETER_ERROR, f"无法读取Excel文件: {str(read_error)}")
        
        if df.empty:
            raise APIException(ErrorCode.PARAMETER_ERROR, "Excel文件为空")
        
        # 获取列名
        columns = df.columns.tolist()
        if len(columns) < 2:
            raise APIException(ErrorCode.PARAMETER_ERROR, "Excel文件至少需要2列数据（X和Y）")
        
        # 第一列作为X，其余列作为Y
        x_column = columns[0]
        y_columns = columns[1:]
        
        x_data = df[x_column].values
        
        # 验证数据
        if len(x_data) < window_length:
            raise APIException(ErrorCode.PARAMETER_ERROR, f"数据点数量({len(x_data)})小于窗口长度({window_length})")
        
        smoothed_data = {}
        
        # 处理每个Y系列
        for y_column in y_columns:
            y_data = df[y_column].values
            
            # 检查是否有NaN值
            if pd.isna(y_data).any():
                # 移除NaN值对应的x和y
                mask = ~pd.isna(y_data)
                x_clean = x_data[mask]
                y_clean = y_data[mask]
            else:
                x_clean = x_data
                y_clean = y_data
            
            if len(y_clean) < window_length:
                continue  # 跳过数据点不足的系列
            
            # 平滑处理
            y_smooth = savgol_filter(y_clean, window_length=window_length, polyorder=polyorder)
            
            # 保存平滑后的数据
            smoothed_data[y_column] = {
                'x': [round(float(x), round_num) for x in x_clean.tolist()],
                'y_original': [round(float(y), round_num) for y in y_clean.tolist()],
                'y_smoothed': [round(float(y), round_num) for y in y_smooth.tolist()]
            }
        
        return {
            'code': 200,
            'message': 'success',
            'data': {
                'image_base64': '',  # 不返回图片
                'smoothed_data': smoothed_data
            }
        }
        
    except APIException:
        raise
    except UnicodeDecodeError:
        raise APIException(ErrorCode.PARAMETER_ERROR, "文件编码错误，请上传有效的Excel文件")
    except Exception as e:
        raise APIException(ErrorCode.SYSTEM_ERROR, f"处理Excel文件时发生错误: {str(e)}")
    finally:
        # 确保文件被关闭
        if 'file' in locals():
            await file.close()