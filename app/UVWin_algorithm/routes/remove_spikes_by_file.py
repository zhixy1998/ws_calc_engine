import re
import matplotlib
import matplotlib.pyplot as plt

from pydantic import BaseModel, Field
from fastapi import APIRouter, UploadFile, File, Form



matplotlib.use('Agg')  # Use non-interactive backend
# 设置中文字体支持
plt.rcParams['font.sans-serif'] = ['Arial Unicode MS', 'SimHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

router = APIRouter()

class OutputSchema(BaseModel):
    code: int = Field(..., description="状态码")
    message: str = Field(..., description="消息")
    data: dict = Field(..., description="返回数据")


@router.post('/remove_spikes_by_file', response_model=OutputSchema)
async def remove_spikes_by_file(
    file: UploadFile = File(..., description="包含光谱数据的Excel文件"),
    spik_x: int = Form(..., description="尖峰开始点")
):
    """
    传入图片, 根据图片拿到x, y的列表, 然后返回去除尖刺后的x, y, 还要渲染一张图片。
    """
    content = await file.read()
    # 确保 content 为字符串，然后按行切分
    if isinstance(content, (bytes, bytearray)):
        content_str = content.decode('utf-8', errors='ignore')
    else:
        content_str = str(content)

    # 更稳健的正则：匹配 wl:<number> 之后的任意空白，再匹配 spec:<number>
    pattern = r"wl:\s*([+-]?\d+(?:\.\d+)?)\s+spec:\s*([+-]?\d+(?:\.\d+)?)"
    x = []
    y = []
    x_y_map = {}
    for line in content_str.splitlines():
        match = re.search(pattern, line)
        if match:
            try:
                x_value = float(match.group(1))
                y_value = float(match.group(2))
            except ValueError:
                continue
            x_y_map[x_value] = y_value
            x.append(x_value)
            y.append(y_value)

    x_before = list(x)
    y_before = list(y)
    # generate_image(x_before, y_before, '去除尖刺前')
    index = x.index(spik_x)
    print('y刺值:', x[index])
    avarage = sum(y[index-5: index-1] + y[index+1: index+5]) / 8
    y[index] = avarage
    # generate_image(x, y, '去除尖刺后')
    # generate_compare_image(x_before, y_before, x, y, '去刺前后对比')

    print('尖刺:========', find_spikes(x, y, window=3, threshold=5, method='median'))
    return {"code": 0, "message": "成功", "data": {"x": x, "y": y}}


def find_spikes(x, y, window=11, threshold=5, method='median'):
    """
    返回被判定为尖刺点的 x 值列表。
    - window: 滑动窗口长度（奇数），用于计算局部基线
    - threshold: 阈值，表示 y - baseline > threshold * sigma 时视为尖刺
    - method: 'median' 或 'mean' 计算局部基线
    """
    import numpy as np
    x = np.asarray(x)
    y = np.asarray(y)
    if window < 3:
        window = 3
    # 计算局部基线（用中位数或均值的滑动窗口）
    pad = window // 2
    yy = np.pad(y, (pad, pad), mode='reflect')
    baseline = np.empty_like(y)
    for i in range(len(y)):
        seg = yy[i:i+window]
        baseline[i] = np.median(seg) if method == 'median' else np.mean(seg)
    resid = y - baseline
    sigma = np.std(resid)
    if sigma == 0:
        return []
    spike_idx = np.where(resid > threshold * sigma)[0]
    return list(x[spike_idx])


def generate_image(x, y, name):
    # 画图并保存
    try:
        fig, ax = plt.subplots(figsize=(32, 12), dpi=200)
        ax.plot(x, y, '-', linewidth=0.6, color='tab:blue')
        ax.scatter(x, y, s=40, color='red', alpha=0.9, edgecolors='none')
        for xi, yi in zip(x, y):
            ax.text(xi + 1, yi, f'{xi:.1f},{yi:.4g}', fontsize=8, color='gray', ha='right', va='center')
        ax.set_xlabel('wl')
        ax.set_ylabel('spec')
        ax.set_title('Spectrum (detailed points, wide)')
        ax.grid(True, linestyle='--', alpha=0.4)
        plt.tight_layout()
        out_path = f'{name}.png'
        fig.savefig(out_path, dpi=300, bbox_inches='tight')
        plt.close(fig)
    except Exception:
        out_path = ''


def generate_compare_image(x1, y1, x2, y2, name):
    """
    去刺前后对比图：两条谱线不同颜色叠加，无吸光度点标注。
    x1, y1: 去刺前；x2, y2: 去刺后
    """
    try:
        fig, ax = plt.subplots(figsize=(32, 12), dpi=200)
        ax.plot(x1, y1, '-', linewidth=1.2, color='tab:blue', label='去刺前', alpha=0.7)
        ax.plot(x2, y2, '-', linewidth=1.2, color='tab:orange', label='去刺后', alpha=0.9)
        ax.set_xlabel('wl')
        ax.set_ylabel('spec')
        ax.set_title('去刺前后对比谱线')
        ax.grid(True, linestyle='--', alpha=0.4)
        ax.legend(fontsize=16)
        plt.tight_layout()
        out_path = f'{name}.png'
        fig.savefig(out_path, dpi=300, bbox_inches='tight')
        plt.close(fig)
    except Exception:
        out_path = ''
