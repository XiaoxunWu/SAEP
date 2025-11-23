import gradio as gr
import pandas as pd
import os

from audio_loader import load_audio_files
from config import (
    AUDIO_FOLDER_TEST, AUDIO_FOLDER_EVAL, AUDIO_FOLDER_REF, SPACE_AUDIO_FOLDER,
    ANSWERS_CSV_PATH, SPACE_ANSWERS_CSV_PATH, DEV_SPACE_PATH,
    TEST_AUDIO_CSV_PATH, TEST_SPACE_CSV_PATH
)
import numpy as np
import datetime
from rating_saver import save_rating_to_file
import matplotlib.pyplot as plt
import io
from PIL import Image
import xlrd
import matplotlib
import time
matplotlib.use('Agg')  # 设置后端为Agg，避免线程问题
import threading
AUDIO_CSV_LOCK = threading.Lock()
SPACE_CSV_LOCK = threading.Lock()
# 修复变量定义顺序问题
# 1. 首先定义FIG_SIZE和FIG_DPI等配置变量
FIG_SIZE = (6, 6)        # 统一图像尺寸（原来是 (3,3)）
FIG_DPI = 110            # 统一 DPI（原来保存时 dpi=40）
FONT_SIZE = 13           # 统一字体大小
TICK_TARGET = 7          # 目标刻度数量（控制密度）
CROSSHAIR_ALPHA = 0.35   # 十字参考线透明度
CROSSHAIR_LW = 1.2       # 十字参考线线宽
POINT_SIZE = 90          # 点大小（看得清但不挡视线）

def initialize_default_view():
    """初始化默认的视图图像，避免使用None值，确保与create_views样式一致"""
    try:
        # 字体与通用样式 - 与create_views保持一致
        plt.rcParams['font.sans-serif'] = ['SimHei']
        plt.rcParams['axes.unicode_minus'] = False
        plt.rcParams['font.size'] = FONT_SIZE

        fig = plt.figure(figsize=FIG_SIZE)
        ax = plt.axes(projection='3d')

        # 背景纯白
        ax.set_facecolor('white')
        fig.patch.set_facecolor('white')

        # 默认坐标（距离=5，方位角=0，高度=0）
        x, y, z = 0, 5, 0  # 对应距离=5，方位角=0

        # 统一坐标轴范围（保底10）
        max_range = 10
        max_range = int(np.ceil(max_range))

        # —— 十字参考线：前后左右 + 上下（与create_views保持一致）——
        line_len = max_range * 0.95
        # X 轴（左右）
        ax.plot([-line_len, line_len], [0, 0], [0, 0],
                linestyle='--', alpha=CROSSHAIR_ALPHA, linewidth=CROSSHAIR_LW, color='k', zorder=1)
        # Y 轴（前后）
        ax.plot([0, 0], [-line_len, line_len], [0, 0],
                linestyle='--', alpha=CROSSHAIR_ALPHA, linewidth=CROSSHAIR_LW, color='k', zorder=1)
        
        # 添加绿色箭头指向Y轴正方向（前方向）
        arrow_length = line_len * 0.2  # 箭头长度为线长的20%
        ax.quiver(0, line_len - arrow_length, 0, 0, arrow_length, 0, 
                  color='g', arrow_length_ratio=0.15, linewidth=2, zorder=2)
        # 在箭头旁边添加"前"字标注
        ax.text(0, line_len, 0.5, "前", fontsize=10, ha='center', va='bottom', color='g', zorder=2)
        # Z 轴（上下）
        ax.plot([0, 0], [0, 0], [-line_len, line_len],
                linestyle='--', alpha=CROSSHAIR_ALPHA, linewidth=CROSSHAIR_LW, color='k', zorder=1)

        # 参考点与默认点（与create_views保持一致的样式）
        ax.scatter(0, 0, 0, c='black', marker='o', s=POINT_SIZE, label='您的位置', zorder=5)
        ax.scatter(x, y, z, c='blue', marker='o', s=POINT_SIZE, label='声音来源', zorder=6)

        # 原点连线
        ax.plot([0, x], [0, y], [0, z], 'b--', alpha=0.45, zorder=4)

        # 坐标轴范围与标签
        ax.set_xlim([-max_range, max_range])
        ax.set_ylim([-max_range, max_range])
        ax.set_zlim([-max_range, max_range])
        ax.set_xlabel('X轴')
        ax.set_ylabel('Y轴')
        ax.set_zlabel('Z轴')

        # 统一刻度密度
        total_span = 2 * max_range
        step = max(1, int(np.ceil(total_span / (TICK_TARGET - 1))))
        ticks = np.arange(-max_range, max_range + 1, step)
        ax.set_xticks(ticks)
        ax.set_yticks(ticks)
        ax.set_zticks(ticks)

        # 标题 - 使用与create_views一致的格式
        ax.set_title(f'声音位置 (距离=5m)')

        # 视角 - 与create_views保持一致
        ax.view_init(elev=30, azim=225)
        # ax.grid(False)
        # 启用网格线，设置合适的样式
        import matplotlib.ticker as ticker
        # 启用主网格线，设置适当的样式使其清晰但不干扰主要内容
        ax.grid(True, linestyle='-', alpha=0.2, color='gray', linewidth=0.8)
        # 添加次网格线，使查看更精确
        ax.grid(True, linestyle=':', alpha=0.1, color='gray', linewidth=0.5, which='minor')
        ax.xaxis.set_minor_locator(ticker.MultipleLocator(1))
        ax.yaxis.set_minor_locator(ticker.MultipleLocator(1))
        ax.zaxis.set_minor_locator(ticker.MultipleLocator(1))

        # 保存为图像（统一 DPI）
        buf = io.BytesIO()
        plt.savefig(buf, format='png', bbox_inches='tight', dpi=FIG_DPI,
                    facecolor='white', edgecolor='none')
        plt.close(fig)
        buf.seek(0)
        return Image.open(buf)
    except Exception as e:
        print(f"初始化默认视图图像时出错: {str(e)}")
        # 出错时创建一个简单的备用图像
        try:
            fig = plt.figure(figsize=FIG_SIZE)
            ax = plt.axes(projection='3d')
            # 设置与create_views一致的基本样式
            ax.set_facecolor('white')
            fig.patch.set_facecolor('white')
            ax.set_xlim([-10, 10])
            ax.set_ylim([-10, 10])
            ax.set_zlim([-10, 10])
            ax.set_xlabel('X轴')
            ax.set_ylabel('Y轴')
            ax.set_zlabel('Z轴')
            ax.text(0, 0, 0, "默认视图", fontsize=12, ha='center')
            ax.view_init(elev=30, azim=225)
            # 保存为图像
            buf = io.BytesIO()
            plt.savefig(buf, format='png', bbox_inches='tight', dpi=FIG_DPI,
                        facecolor='white', edgecolor='none')
            plt.close(fig)
            buf.seek(0)
            return Image.open(buf)
        except:
            # 如果所有尝试都失败，返回None
            return None

# 初始化默认视图图像
DEFAULT_VIEW_IMG = initialize_default_view()

# 添加全局变量用于存储音频文件名到空间数据的映射
audio_to_spatial_data = {}
last_update_time = {}
# 禁用Gradio analytics以避免连接超时
os.environ['GRADIO_ANALYTICS_ENABLED'] = 'False'
# 修改评估音频加载方式 - 从CSV文件读取文件名并从指定目录递归加载
audio_files_eval = []
audio_files_ref = []
audio_files_test = []
space_audio_files = []

def load_space_audio_files():
    """从space文件夹加载音频文件"""
    try:
        result = load_audio_files(SPACE_AUDIO_FOLDER)
        # 检查返回值是否为列表
        return result if isinstance(result, list) else []
    except Exception as e:
        print(f"加载space文件夹中的音频文件时出错: {str(e)}")
        return []

# 加载空间音频文件
space_audio_files = load_space_audio_files()

# 先加载参考音频文件 - 移动到这里
result = load_audio_files(AUDIO_FOLDER_REF)
audio_files_ref = result if isinstance(result, list) else []
# print(f"成功加载{len(audio_files_ref)}个参考音频文件")

# 然后再加载测试音频文件并进行配对
try:
    # 加载deg文件夹中的测试音频
    result = load_audio_files(AUDIO_FOLDER_TEST)
    all_test_audio = result if isinstance(result, list) else []
    # print(f"成功加载{len(all_test_audio)}个测试音频文件")
    
    # 创建参考音频文件名到路径的映射
    ref_audio_map = {os.path.basename(file_path): file_path for file_path in audio_files_ref}
    
    # 创建测试音频文件名到路径的映射
    test_audio_map = {os.path.basename(file_path): file_path for file_path in all_test_audio}
    
    # 基于文件名匹配，确保参考音频和测试音频配对
    paired_audio_files = []
    for ref_filename, ref_path in ref_audio_map.items():
        if ref_filename in test_audio_map:
            paired_audio_files.append(test_audio_map[ref_filename])
            # print(f"找到配对音频: 参考-{ref_filename}, 测试-{ref_filename}")
    
    # 如果有配对的音频，使用配对的音频；否则使用所有测试音频
    if paired_audio_files:
        audio_files_test = paired_audio_files
        # print(f"成功配对{len(audio_files_test)}组音频文件")
    else:
        audio_files_test = all_test_audio
        print("警告：没有找到匹配的音频对，使用所有测试音频")
        
    # 确保至少有一个测试音频文件
    if not audio_files_test:
        print("错误：没有找到任何测试音频文件")
        audio_files_test = []
        
    # # 如果有测试音频，确保有对应的参考音频
    # if audio_files_test and not audio_files_ref:
    #     print("错误：没有找到任何参考音频文件")
    #     # 尝试重新加载参考音频
    #     audio_files_ref = load_audio_files(AUDIO_FOLDER_REF)
except Exception as e:
    print(f"加载测试音频时出错: {str(e)}")
    audio_files_test = []


try:
    # 使用pandas读取CSV文件，添加编码参数支持中文编码
    # 尝试使用不同的编码格式
    try:
        snr_df = pd.read_csv(DEV_SPACE_PATH, encoding='gbk')  # 优先使用GBK编码
        print(f"成功以GBK编码读取50.csv文件，共{len(snr_df)}条记录")
    except UnicodeDecodeError:
        try:
            snr_df = pd.read_csv(DEV_SPACE_PATH, encoding='utf-8')
            print(f"成功以UTF-8编码读取50.csv文件，共{len(snr_df)}条记录")
        except UnicodeDecodeError:
            snr_df = pd.read_csv(DEV_SPACE_PATH, encoding='latin1')  # 使用latin1作为最后的备选
            print(f"成功以LATIN1编码读取50.csv文件，共{len(snr_df)}条记录")
    
    # 确保Stereo_audio列存在
    if 'Stereo_audio' in snr_df.columns:
        # 获取所有文件名（包括重复的），按照CSV中的顺序
        all_csv_filenames = snr_df['Stereo_audio'].tolist()
        print(f"从CSV中读取到{len(all_csv_filenames)}个音频文件名")
        
        # 同时提取空间数据并创建映射
        required_columns = ['Stereo_audio', 'Azimuth', 'Elevation', 'Horizontal_Distance']
        if all(col in snr_df.columns for col in required_columns):
            print("从50.csv提取空间数据")
            for index, row in snr_df.iterrows():
                filename = row['Stereo_audio']
                try:
                    azimuth = float(row['Azimuth'])        # 方位角
                    elevation = float(row['Elevation'])    # 仰角
                    distance = float(row['Horizontal_Distance'])  # 水平距离
                    # 存储到映射中
                    audio_to_spatial_data[filename] = {
                        'distance': distance,
                        'azimuth': azimuth,
                        'elevation': elevation
                    }
                except Exception as e:
                    print(f"警告：处理文件 {filename} 的空间数据时出错: {e}")
        else:
            print(f"警告：CSV文件缺少必要的列")
        
        # 使用load_audio_files递归获取AUDIO_FOLDER_EVAL中所有的音频文件路径
        all_audio_files = load_audio_files(AUDIO_FOLDER_EVAL)
        
        # 如果load_audio_files返回的是错误信息，处理错误
        if isinstance(all_audio_files, str):
            print(f"加载音频文件失败: {all_audio_files}")
            audio_files_eval = []
        else:
            print(f"递归加载完成，共找到{len(all_audio_files)}个音频文件")
            
            # 创建文件名到文件路径的映射（只保留文件名部分作为键）
            audio_file_map = {os.path.basename(file_path): file_path for file_path in all_audio_files}
            
            # 根据CSV中的文件名顺序查找对应的文件路径，包括重复的文件名
            found_count = 0
            audio_files_eval = []
            for filename in all_csv_filenames:
                if filename in audio_file_map:
                    # 检查文件是否真的存在
                    if os.path.exists(audio_file_map[filename]):
                        audio_files_eval.append(audio_file_map[filename])
                        found_count += 1
                        # print(f"找到匹配文件: {audio_file_map[filename]}")
                    else:
                        print(f"警告：文件路径存在但实际文件不存在: {audio_file_map[filename]}")
                else:
                    print(f"警告：未找到文件: {filename}")
            
            # 如果没有找到任何匹配文件，使用所有音频文件
            if found_count == 0 and all_audio_files:
                print("警告：未找到任何匹配的音频文件，使用所有可用音频文件")
                # 只添加确实存在的文件
                audio_files_eval = [f for f in all_audio_files if os.path.exists(f)]
except Exception as e:
    print(f"读取50.csv文件时出错: {str(e)}")
    # 回退到直接加载方式，但确保只添加存在的文件
    audio_files_eval = []
    try:
        temp_files = load_audio_files(AUDIO_FOLDER_EVAL)
        if not isinstance(temp_files, str):
            audio_files_eval = [f for f in temp_files if os.path.exists(f)]
    except Exception as e2:
        print(f"回退加载也失败: {str(e2)}")


# # 加载参考音频文件
# audio_files_ref = load_audio_files(AUDIO_FOLDER_REF)  # 加载所有参考音频文件
# print(f"成功加载{len(audio_files_ref)}个参考音频文件")
# # 读取音频分数文件
# print(f"尝试读取音频答案文件：{ANSWERS_CSV_PATH}")
try:
    if not os.path.exists(ANSWERS_CSV_PATH):
        print(f"警告：音频答案文件不存在：{ANSWERS_CSV_PATH}")
        audio_answers_df = pd.DataFrame(columns=['音频文件名', '分数'])
        audio_file_names = []
        correct_scores = []
    else:
        # 修改为使用pd.read_csv读取CSV文件
        audio_answers_df = pd.read_csv(ANSWERS_CSV_PATH)
        # print(f"成功读取CSV文件")
        # print(f"文件列名：{audio_answers_df.columns.tolist()}")
        
        if audio_answers_df.empty:
            print("警告：音频答案文件为空")
            audio_file_names = []
            correct_scores = []
        else:
            # 使用正确的列名获取数据
            # 使用正确的列名获取数据
            if 'Stereo_audio' in audio_answers_df.columns and 'MOS' in audio_answers_df.columns:
                # 清理文件名空白
                audio_file_names = audio_answers_df['Stereo_audio'].astype(str).str.strip().tolist()
                # 强制把 MOS 转为数值，无法解析的记为 NaN
                mos_series = pd.to_numeric(audio_answers_df['MOS'], errors='coerce')
                # 可选：打印出哪些行是非数值，便于你修CSV
                bad_rows = mos_series.isna()
                if bad_rows.any():
                    print(f"[ANS] 非数值 MOS 行索引: {audio_answers_df.index[bad_rows].tolist()}")
                    print(audio_answers_df.loc[bad_rows, ['Stereo_audio','MOS']])
                correct_scores = mos_series.tolist()
            else:
                # 如果列名不匹配，尝试使用索引
                print("警告：未找到预期的列名，尝试使用索引")
                audio_file_names = audio_answers_df.iloc[:, 0].astype(str).str.strip().tolist()
                mos_series = pd.to_numeric(audio_answers_df.iloc[:, 1], errors='coerce')
                bad_rows = mos_series.isna()
                if bad_rows.any():
                    print(f"[ANS] 非数值 MOS 行索引(索引模式): {audio_answers_df.index[bad_rows].tolist()}")
                    print(audio_answers_df.loc[bad_rows, audio_answers_df.columns[:2]])
                correct_scores = mos_series.tolist()

except Exception as e:
            print(f"读取音频分数文件出错：{str(e)}")
            # print(f"文件路径：{ANSWERS_CSV_PATH}")
            # print(f"文件是否存在：{os.path.exists(ANSWERS_CSV_PATH)}")
            if os.path.exists(ANSWERS_CSV_PATH):
                print(f"文件大小：{os.path.getsize(ANSWERS_CSV_PATH)} bytes")
            audio_answers_df = pd.DataFrame(columns=['音频文件名', '分数'])
            audio_file_names = []
            correct_scores = []

# 读取空间答案 Excel 文件
try:
    if not os.path.exists(SPACE_ANSWERS_CSV_PATH):
        print(f"警告：空间答案文件不存在：{SPACE_ANSWERS_CSV_PATH}")
        space_answers_df = pd.DataFrame(columns=['音频文件名', '距离', '方位角', '仰角'])
        space_file_names = []
        correct_distances = []
        correct_azimuths = []
        correct_elevations = []
    else:
        # print(f"尝试读取空间答案文件：{SPACE_ANSWERS_CSV_PATH}")
        # 修改为使用pd.read_csv读取CSV文件
        try:
            space_answers_df = pd.read_csv(SPACE_ANSWERS_CSV_PATH)
            # print(f"成功读取CSV文件")
            # print(f"文件列名：{space_answers_df.columns.tolist()}")
            
            if space_answers_df.empty:
                print("警告：空间答案文件为空")
                space_file_names = []
                correct_distances = []
                correct_azimuths = []
                correct_elevations = []
            else:
                # 使用正确的列名获取数据
                if 'Stereo_audio' in space_answers_df.columns and 'Azimuth' in space_answers_df.columns and 'Elevation' in space_answers_df.columns and 'Horizontal_Distance' in space_answers_df.columns:
                    space_file_names = space_answers_df['Stereo_audio'].tolist()
                    correct_azimuths = space_answers_df['Azimuth'].tolist()
                    correct_elevations = space_answers_df['Elevation'].tolist()
                    correct_distances = space_answers_df['Horizontal_Distance'].tolist()
                    # print(f"成功读取数据，空间文件数量：{len(space_file_names)}")
                else:
                    # 如果列名不匹配，尝试使用索引
                    print("警告：未找到预期的列名，尝试使用索引")
                    space_file_names = space_answers_df.iloc[:, 0].tolist()
                    correct_azimuths = space_answers_df.iloc[:, 1].tolist()
                    correct_elevations = space_answers_df.iloc[:, 2].tolist()
                    correct_distances = space_answers_df.iloc[:, 3].tolist()
                    # print(f"使用索引成功读取数据，空间文件数量：{len(space_file_names)}")
        except Exception as csv_error:
            print(f"读取CSV文件失败：{str(csv_error)}")
            # 尝试使用Excel读取方法作为后备
            try:
                workbook = xlrd.open_workbook(SPACE_ANSWERS_CSV_PATH)
                sheet = workbook.sheet_by_index(0)
                
                # 读取数据
                space_file_names = []
                correct_distances = []
                correct_azimuths = []
                correct_elevations = []
                
                for row in range(1, sheet.nrows):  # 假设第一行是标题
                    space_file_names.append(str(sheet.cell_value(row, 0)))
                    correct_azimuths.append(float(sheet.cell_value(row, 1)))
                    correct_elevations.append(float(sheet.cell_value(row, 2)))
                    correct_distances.append(float(sheet.cell_value(row, 3)))
                
                # print(f"使用xlrd成功读取文件，共{len(space_file_names)}条记录")
                space_answers_df = pd.DataFrame({
                    '音频文件名': space_file_names,
                    '方位角': correct_azimuths,
                    '仰角': correct_elevations,
                    '距离': correct_distances
                })
            except Exception as excel_error:
                print(f"使用xlrd读取失败：{str(excel_error)}")
                # 尝试使用openpyxl读取
                try:
                    space_answers_df = pd.read_excel(SPACE_ANSWERS_CSV_PATH, engine='openpyxl')
                    # print(f"使用openpyxl成功读取文件")
                    # print(f"文件列名：{space_answers_df.columns.tolist()}")
                    if space_answers_df.empty:
                        print("警告：空间答案文件为空")
                        space_file_names = []
                        correct_distances = []
                        correct_azimuths = []
                        correct_elevations = []
                    else:
                        space_file_names = space_answers_df.iloc[:, 0].tolist()
                        correct_azimuths = space_answers_df.iloc[:, 1].tolist()
                        correct_elevations = space_answers_df.iloc[:, 2].tolist()
                        correct_distances = space_answers_df.iloc[:, 3].tolist()
                        # print(f"使用索引成功读取数据，空间文件数量：{len(space_file_names)}")
                except Exception as openpyxl_error:
                    print(f"使用openpyxl读取失败：{str(openpyxl_error)}")
                    raise
except Exception as e:
    print(f"读取空间答案文件出错：{str(e)}")
    # print(f"文件路径：{SPACE_ANSWERS_CSV_PATH}")
    # print(f"文件是否存在：{os.path.exists(SPACE_ANSWERS_CSV_PATH)}")
    if os.path.exists(SPACE_ANSWERS_CSV_PATH):
        print(f"文件大小：{os.path.getsize(SPACE_ANSWERS_CSV_PATH)} bytes")
    space_answers_df = pd.DataFrame(columns=['音频文件名', '距离', '方位角', '仰角'])
    space_file_names = []
    correct_distances = []
    correct_azimuths = []
    correct_elevations = []

def on_confirm(username, audio_index, user_choice, distance, angle, height):
    try:
        # import os, numpy as np, pandas as pd
        # import gradio as gr

        # 获取当前脚本所在目录
        current_dir = os.path.dirname(os.path.abspath(__file__))
        # 获取项目根目录（当前目录的上一级）
        root_dir = os.path.dirname(current_dir)

        if audio_index < 5:
            # 前五个音频处理
            if (not audio_file_names) or audio_index >= len(audio_file_names):
                return "警告：未找到音频答案文件或答案不完整", gr.update(visible=True)
            if (not correct_scores) or audio_index >= len(correct_scores):
                return "警告：未找到正确分数或答案不完整", gr.update(visible=True)

            audio_file_name = audio_file_names[audio_index]
            try:
                correct_answer = float(correct_scores[audio_index])
            except (ValueError, TypeError):
                return f"配置错误：第{audio_index + 1}个音频的参考分数不是有效数字，请检查答案表 MOS 列", gr.update(visible=True)


            # 安全解析用户评分
            try:
                user_score = float(user_choice)
            except (ValueError, TypeError):
                return "请先选择或输入有效的评分数字", gr.update(visible=True)

            error = abs(user_score - correct_answer)

            # 使用配置文件中的路径
            csv_path = TEST_AUDIO_CSV_PATH
            print(f"[Audio] 保存文件路径: {csv_path}")

            # 读取或初始化
            try:
                if os.path.exists(csv_path) and os.path.getsize(csv_path) > 0:
                    df = pd.read_csv(csv_path)
                else:
                    df = pd.DataFrame(columns=['用户名','音频文件名','音频文件正确分数','用户评分','误差','RMSE分数'])
            except pd.errors.EmptyDataError:
                df = pd.DataFrame(columns=['用户名','音频文件名','音频文件正确分数','用户评分','误差','RMSE分数'])

            # 追加记录
            new_row = {
                '用户名': username,
                '音频文件名': audio_file_name,
                '音频文件正确分数': correct_answer,
                '用户评分': user_score,
                '误差': error,
            }
            df.loc[len(df)] = new_row

            # 确保数值列为数值类型
            for col in ['音频文件正确分数','用户评分','误差','RMSE分数']:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce')

            # 计算 RMSE（前5条）
            user_data = df[df['用户名'] == username].head(5)
            if len(user_data) == 5:
                rmse = float(np.sqrt(np.nanmean((user_data['误差'] ** 2).values)))
                df.loc[df['用户名'] == username, 'RMSE分数'] = rmse

            # 确保目录存在（处理空目录名）
            dirpath = os.path.dirname(csv_path) or '.'
            os.makedirs(dirpath, exist_ok=True)
            tmp_path = csv_path + ".tmp"
            with AUDIO_CSV_LOCK:                       # ← 这里用 AUDIO_CSV_LOCK
                df.to_csv(tmp_path, index=False, encoding='utf-8-sig')
                os.replace(tmp_path, csv_path)
            print(f"[Audio] 文件已保存到: {csv_path}")  # ← 日志也改回 Audio


            result = f"该音频参考分数为: {correct_answer}"

        else:
            # 空间音频处理
            space_index = audio_index - 5
            if (not space_file_names) or space_index >= len(space_file_names):
                return "警告：未找到空间答案文件或答案不完整", gr.update(visible=True)
            if (space_index >= len(correct_distances) or
                space_index >= len(correct_azimuths) or
                space_index >= len(correct_elevations)):
                return "警告：空间答案数组长度不一致", gr.update(visible=True)

            audio_file_name = space_file_names[space_index]
            correct_distance = float(correct_distances[space_index])
            correct_azimuth = float(correct_azimuths[space_index])
            correct_elevation = float(correct_elevations[space_index])

            # 安全解析用户输入
            try:
                user_distance = float(distance)
                user_azimuth = float(angle)
                user_height = float(height)
            except (ValueError, TypeError):
                return "请先选择空间位置", gr.update(visible=True)

            # 计算仰角（-90~90）
            # horizontal_distance = np.sqrt(user_distance**2 - user_height**2)
            # user_elevation = np.degrees(np.arctan2(user_height, max(1e-9, horizontal_distance)))
            # user_elevation = max(-90, min(90, user_elevation))
            # 用户选择的是水平距离，仰角 = arctan(高度 / 水平距离)
            if user_distance == 0:
                # 距离为0时：
                # - 高度 > 0：正上方，仰角 = 90°
                # - 高度 < 0：正下方，仰角 = -90°
                # - 高度 = 0：就在听者位置，仰角 = 0°
                if user_height > 0:
                    user_elevation = 90.0
                elif user_height < 0:
                    user_elevation = -90.0
                else:
                    user_elevation = 0.0
            else:
                # 计算仰角：arctan(高度 / 水平距离)
                user_elevation = np.degrees(np.arctan2(user_height, user_distance))
                user_elevation = max(-90, min(90, user_elevation))
                
            # 误差
            distance_error = abs(user_distance - correct_distance)
            azimuth_error = abs(user_azimuth - correct_azimuth)
            elevation_error = abs(user_elevation - correct_elevation)

            # 保存
            csv_path = TEST_SPACE_CSV_PATH
            print(f"[Space] 保存文件路径: {csv_path}")

            try:
                if os.path.exists(csv_path) and os.path.getsize(csv_path) > 0:
                    df = pd.read_csv(csv_path)
                else:
                    df = pd.DataFrame(columns=[
                        '用户名','音频文件名','声源距离','声源方位角','声源仰角',
                        '用户点击距离','用户点击方位角','用户选择高度','用户感知声源仰角',
                        '距离误差','方位角误差','仰角误差','方位判断RMSE'
                    ])
            except pd.errors.EmptyDataError:
                df = pd.DataFrame(columns=[
                    '用户名','音频文件名','声源距离','声源方位角','声源仰角',
                    '用户点击距离','用户点击方位角','用户选择高度','用户感知声源仰角',
                    '距离误差','方位角误差','仰角误差','方位判断RMSE'
                ])

            df.loc[len(df)] = {
                '用户名': username,
                '音频文件名': audio_file_name,
                '声源距离': correct_distance,
                '声源方位角': correct_azimuth,
                '声源仰角': correct_elevation,
                '用户点击距离': user_distance,
                '用户点击方位角': user_azimuth,
                '用户选择高度': user_height,
                '用户感知声源仰角': user_elevation,
                '距离误差': distance_error,
                '方位角误差': azimuth_error,
                '仰角误差': elevation_error
            }

            # 数值列规范
            for col in ['声源距离','声源方位角','声源仰角','用户点击距离','用户点击方位角',
                        '用户选择高度','用户感知声源仰角','距离误差','方位角误差','仰角误差','方位判断RMSE']:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce')

            # 计算更准确的方位角误差（考虑环状特性）
            def calculate_angular_error(angle1, angle2):
                diff = abs(angle1 - angle2)
                return min(diff, 360 - diff)
            
            # 计算 RMSE（最近4条）
            user_data = df[df['用户名'] == username].tail(4)
            if len(user_data) == 4:
                # 计算距离RMSE
                distance_rmse = float(np.sqrt(np.nanmean(user_data['距离误差'].values.astype(float) ** 2)))
                
                # 计算方位角环状RMSE
                azimuth_errors = [calculate_angular_error(user_data['声源方位角'].iloc[i], user_data['用户点击方位角'].iloc[i]) 
                                 for i in range(len(user_data))]
                azimuth_rmse = float(np.sqrt(np.mean(np.array(azimuth_errors) ** 2)))
                
                # 计算仰角RMSE
                elevation_rmse = float(np.sqrt(np.nanmean(user_data['仰角误差'].values.astype(float) ** 2)))
                
                # 分别存储或计算综合评分
                df.loc[df['用户名'] == username, '距离RMSE'] = distance_rmse
                df.loc[df['用户名'] == username, '方位角RMSE'] = azimuth_rmse
                df.loc[df['用户名'] == username, '仰角RMSE'] = elevation_rmse

            dirpath = os.path.dirname(csv_path) or '.'
            os.makedirs(dirpath, exist_ok=True)
            tmp_path = csv_path + ".tmp"
            with SPACE_CSV_LOCK:
                df.to_csv(tmp_path, index=False, encoding='utf-8-sig')
                os.replace(tmp_path, csv_path)
            print(f"[Space] 文件已保存到: {csv_path}")


            result = (f"音频{audio_index + 1}的参考方位是：距离={correct_distance:.2f}, "
                      f"方位角={correct_azimuth:.2f}°, 仰角={correct_elevation:.2f}°")

        return result, gr.update(visible=True)

    except Exception as e:
        print(f"Error in on_confirm: {str(e)}")
        try:
            print(f"Current directory: {current_dir}")
        except Exception:
            pass
        return f"处理时出错: {str(e)}", gr.update(visible=True)

        
def create_views(distance=5, azimuth=0, height=0):
    try:
        # 字体与通用样式
        plt.rcParams['font.sans-serif'] = ['SimHei']
        plt.rcParams['axes.unicode_minus'] = False
        plt.rcParams['font.size'] = FONT_SIZE

        fig = plt.figure(figsize=FIG_SIZE)
        ax = plt.axes(projection='3d')

        # 背景纯白
        ax.set_facecolor('white')
        fig.patch.set_facecolor('white')

        # 计算坐标
        azimuth_rad = np.radians(azimuth)
        x = distance * np.sin(azimuth_rad)
        y = distance * np.cos(azimuth_rad)
        z = height

        # 统一坐标轴范围（保底10）
        max_range = max(abs(x), abs(y), abs(z), 10)
        max_range = int(np.ceil(max_range))

        # —— 十字参考线：前后左右 + 上下（尽量不遮挡点，放低 zorder/半透明）——
        line_len = max_range * 0.95
        # X 轴（左右）
        ax.plot([-line_len, line_len], [0, 0], [0, 0],
                linestyle='--', alpha=CROSSHAIR_ALPHA, linewidth=CROSSHAIR_LW, color='k', zorder=1)
        # Y 轴（前后）
        ax.plot([0, 0], [-line_len, line_len], [0, 0],
                linestyle='--', alpha=CROSSHAIR_ALPHA, linewidth=CROSSHAIR_LW, color='k', zorder=1)
        
        # 添加绿色箭头指向Y轴正方向（前方向）
        arrow_length = line_len * 0.2  # 箭头长度为线长的20%
        ax.quiver(0, line_len - arrow_length, 0, 0, arrow_length, 0, 
                  color='g', arrow_length_ratio=0.15, linewidth=2, zorder=2)
        # 在箭头旁边添加"前"字标注
        ax.text(0, line_len, 0.5, "前", fontsize=10, ha='center', va='bottom', color='g', zorder=2)
        # Z 轴（上下）
        ax.plot([0, 0], [0, 0], [-line_len, line_len],
                linestyle='--', alpha=CROSSHAIR_ALPHA, linewidth=CROSSHAIR_LW, color='k', zorder=1)

        # 参考点与选择点（抬高 zorder，确保不被线遮住）
        ax.scatter(0, 0, 0, c='black', marker='o', s=POINT_SIZE, label='您的位置', zorder=5)
        ax.scatter(x, y, z, c='blue', marker='o', s=POINT_SIZE, label='声音来源', zorder=6)

        # 原点连线（轻量）
        ax.plot([0, x], [0, y], [0, z], 'b--', alpha=0.45, zorder=4)

        # 方位角弧线（阈值内减少绘制，保证流畅）
        if abs(azimuth) > 10:
            arc_radius = max_range * 0.35
            arc_angles = np.linspace(0, azimuth, 24)
            arc_rad = np.radians(arc_angles)
            arc_x = arc_radius * np.sin(arc_rad)
            arc_y = arc_radius * np.cos(arc_rad)
            ax.plot(arc_x, arc_y, np.zeros_like(arc_x), 'm-', alpha=0.6, linewidth=1.2, zorder=3)

        # 坐标轴范围与标签
        ax.set_xlim([-max_range, max_range])
        ax.set_ylim([-max_range, max_range])
        ax.set_zlim([-max_range, max_range])
        ax.set_xlabel('X轴')
        ax.set_ylabel('Y轴')
        ax.set_zlabel('Z轴')

        # 统一刻度密度：根据 TICK_TARGET 自动推步长
        # 让总刻度数量约等于 TICK_TARGET（两侧对称）
        total_span = 2 * max_range
        step = max(1, int(np.ceil(total_span / (TICK_TARGET - 1))))
        ticks = np.arange(-max_range, max_range + 1, step)
        ax.set_xticks(ticks)
        ax.set_yticks(ticks)
        ax.set_zticks(ticks)

        # 标题
        ax.set_title(f'声音位置 (距离={int(round(distance))}m)')

        # 视角
        ax.view_init(elev=30, azim=225)

        # 关网格
        # ax.grid(False)
        # 启用网格线，设置合适的样式
        import matplotlib.ticker as ticker
        # 启用主网格线，设置适当的样式使其清晰但不干扰主要内容
        ax.grid(True, linestyle='-', alpha=0.2, color='gray', linewidth=0.8)
        # 添加次网格线，使查看更精确
        ax.grid(True, linestyle=':', alpha=0.1, color='gray', linewidth=0.5, which='minor')
        ax.xaxis.set_minor_locator(ticker.MultipleLocator(1))
        ax.yaxis.set_minor_locator(ticker.MultipleLocator(1))
        ax.zaxis.set_minor_locator(ticker.MultipleLocator(1))

        # 保存为图像（统一 DPI）
        buf = io.BytesIO()
        plt.savefig(buf, format='png', bbox_inches='tight', dpi=FIG_DPI,
                    facecolor='white', edgecolor='none')
        plt.close(fig)  # 只关闭本 figure，避免影响其它图
        buf.seek(0)
        image = Image.open(buf)

        return image
    except Exception as e:
        print(f"Error in create_views: {str(e)}")
        plt.close('all')
        # 创建一个简单的默认图像而不是返回None
        fig = plt.figure(figsize=FIG_SIZE)
        ax = fig.add_subplot(111, projection='3d')
        # 添加基本的文本信息
        ax.text(0, 0, 0, "图像加载失败", fontsize=12, ha='center')
        # 设置坐标轴范围
        ax.set_xlim([-5, 5])
        ax.set_ylim([-5, 5])
        ax.set_zlim([-5, 5])
        # 保存为图像
        buf = io.BytesIO()
        plt.savefig(buf, format='png', bbox_inches='tight', dpi=FIG_DPI,
                    facecolor='white', edgecolor='none')
        plt.close(fig)
        buf.seek(0)
        image = Image.open(buf)
        return image


def create_update_view_func(idx):
    last_call = [0]  # 使用列表作为可变对象来存储时间戳
    
    def update_view(d, a, h):
        try:
            # 添加防抖逻辑
            current_time = time.time()
            if current_time - last_call[0] < 0.3:  # 300ms内不重复更新
                return gr.update()  # 保持当前图像不变
            last_call[0] = current_time
            
            # 确保输入值是数值类型
            d = float(d)
            a = float(a)
            h = float(h)
            
            # 直接调用create_views
            image = create_views(d, a, h)
            # 关键修复：确保返回有效值
            if image is None:
                # 如果create_views返回None，返回一个空的gr.update而不是尝试设置None值
                return gr.update()  # 保持当前图像不变
            return gr.update(value=image)
        except Exception as e:
            print(f"Error in update_view: {str(e)}")
            # 出错时返回空的gr.update而不是DEFAULT_VIEW_IMG
            return gr.update()
    return update_view

def handle_submit_test(username, device_type, device_model, gender, birth_year, hearing_impaired, nationality, audio_test, note_agreement, *ratings_and_spatial):
    # 这是原有的测试页面提交逻辑
    try:
        # 获取音频文件列表（测试页面的音频）
        audio_files = audio_files_test

        if not audio_files:
            return "错误：没有找到音频文件"

        # 分离评分和空间信息
        num_audios = len(audio_files)
        ratings = list(map(float, ratings_and_spatial[:num_audios]))
        spatial_ratings = list(map(float, ratings_and_spatial[num_audios:num_audios*2]))
        
        # 获取距离、方位角和仰角数据
        distances = []
        azimuths = []
        elevations = []
        
        for i in range(num_audios):
            if i < len(audio_files):
                audio_filename = os.path.basename(audio_files[i])
                distance = 5.0
                azimuth = 0.0
                height = 0.0

                
                # 通过文件名匹配查找空间数据
                for j, filename in enumerate(space_file_names):
                    if filename == audio_filename:
                        distance = correct_distances[j]
                        azimuth = correct_azimuths[j]
                        height = correct_elevations[j]
                        break
                
                # 正确计算仰角
                horizontal_distance = np.sqrt(distance**2 - height**2)
                calculated_elevation = np.degrees(np.arctan2(height, max(1e-9, horizontal_distance)))
                
                distances.append(distance)
                azimuths.append(azimuth)
                elevations.append(calculated_elevation)  # 使用计算的仰角值
            else:
                distances.append(5.0)
                azimuths.append(0.0)
                elevations.append(0.0)
        
        # 检查数据完整性
        if len(ratings) != num_audios or len(spatial_ratings) != num_audios:
            return f"错误：数据不完整。评分数量：{len(ratings)}，空间评分数量：{len(spatial_ratings)}，音频数量：{num_audios}"

        # 保存数据（使用原有参数顺序）
        result = save_rating_to_file(
            username, device_type, device_model, gender, birth_year, 
            hearing_impaired, nationality, audio_test, note_agreement,
            ratings, distances, azimuths, elevations
        )
        
        return result
    except Exception as e:
        print(f"提交处理出错: {str(e)}")
        return f"提交处理出错: {str(e)}"

# 评估页面专用的提交处理函数

def handle_submit_eval(username, device_type, device_model, gender, birth_year, hearing_impaired, nationality, audio_test, note_agreement, *ratings_and_spatial):
    try:
        # 获取音频文件列表（评估页面的音频，限制为52个）
        global audio_files_eval
        audio_files = audio_files_eval[:52]  # 使用52个音频文件

        if not audio_files:
            return "错误：没有找到音频文件"

        # 打印接收到的参数（调试用）
        print(f"评估页面 - 评分数量: {len(ratings_and_spatial)}")
        print(f"评估页面 - 音频文件数量: 52")
        
        # 分离评分和空间一致性评分
        num_audios = 52  # 固定为52个音频
        ratings = list(map(float, ratings_and_spatial[:num_audios]))
        spatial_ratings = list(map(float, ratings_and_spatial[num_audios:num_audios*2]))
        
        # 检查数据完整性
        if len(ratings) != num_audios or len(spatial_ratings) != num_audios:
            return f"错误：数据不完整。评分数量：{len(ratings)}，空间评分数量：{len(spatial_ratings)}，音频数量：{num_audios}"

        # 保存数据，只传递音频质量分数和空间一致性分数
        other_device_model = ""  # 或者使用device_model
        result = save_rating_to_file(
            username, device_type, device_model, other_device_model, gender, birth_year, 
            hearing_impaired, nationality, audio_test, note_agreement,
            ratings, spatial_ratings, audio_files  # 只传递两个评分列表和音频文件
        )
        
        return result
    except Exception as e:
        print(f"评估页面提交处理出错: {str(e)}")
        return f"评估页面提交处理出错: {str(e)}"


# 创建 UI
def create_ui():
    css = """
        .gradio-container {
            font-family: system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, 'Open Sans', 'Helvetica Neue', sans-serif;
        }
        .gradio-container .prose {
            font-size: var(--text-md);
        }
        .gradio-container button, 
        .gradio-container label,
        .gradio-container input,
        .gradio-container select,
        .gradio-container textarea {
            font-size: var(--text-md);
        }
    """
    
    with gr.Blocks(title="音频质量评估系统", css=css) as demo:
        # # 添加一个隐藏的锚点作为页面顶部标记
        # page_anchor = gr.HTML(value='<a id="page_top"></a>', visible=False)
        
        # 用 State 来保存当前的步骤
        current_step = gr.State("信息收集")  # 初始状态为"信息搜集"

        # 信息搜集页面
        with gr.Column(visible=True) as info_col:
            gr.Markdown("## 信息收集")
            markdown_text = '<span style="font-size: 16px; color: grey;">请如实填写以下信息</span>'
            gr.Markdown(markdown_text)
            username_input = gr.Textbox(label="用户名", placeholder="请输入用户名")
            device_type_input = gr.Dropdown(label="设备类型", choices=["耳机", "扬声器"])
            # 设备型号选项
            device_model_choices = ["AirPods (第2代)", "AirPods (第3代)", "AirPods Pro", "AirPods Max", "WF-1000XM4", "WF-C500", "WH-1000XM5", "WH-CH720N", "FreeBuds Pro 2", "FreeBuds 5i", "FreeBuds Studio", "Redmi Buds 4 Pro", "Mi True Wireless Earphones 2", "Mi Headphones", "Lollipods Pro", "NeoBuds Pro", "W860NB", "其他"]
            device_model_input = gr.Dropdown(label="设备型号", choices=device_model_choices)
            other_device_model_input = gr.Textbox(label="请输入具体设备型号", visible=False)

            # 新增性别选择
            gender_input = gr.Radio(label="性别", choices=["男", "女", "其他"], value=None)

            # 新增出生年份选择
            current_year = datetime.datetime.now().year
            birth_year_input = gr.Dropdown(label="出生年份", choices=list(range(1965, current_year + 1)))

            # 新增听力水平认知，将 Checkbox 替换为 Radio
            yes_no_choices = ["是", "否"]
            hearing_impaired_input = gr.Radio(label="是否有耳部疾病等听力受损情况", choices=yes_no_choices, value=None)

            # 新增国籍信息收集
            nationality_input = gr.Textbox(label="国籍", placeholder="请输入国籍")

            audio_test_input = gr.Radio(label="是否接受过音频质量评估测试", choices=yes_no_choices, value=None)

            # 新增注意事项
            note_text = gr.Markdown(
                value="""
                    ## 注意事项

                    ### 一、基本要求
                    1. 主观听力测试即将开始，请保持所在环境尽量安静\n
                    2. 请一次性完成所有题目，中途请勿退出

                    ### 二、测试流程说明
                    在下一个页面，您将熟悉空间音频评分的流程：

                    ### 1. 音频质量评估（前五个音频）
                    • 您可以通过参考音频来对失真音频进行打分\n
                    • 参考音频是被认为干净无噪声的最高分音频（5分），后续正式的音频评估将没有参考音频\n
                    • 请忽视内容与音调，仅在音质方面给出评分\n
                    • 评分范围：1-5分（1分为音质最差，5分为音质最好）

                    ### 2. 空间感知评估（后四个音频）
                    • 主要关注个人空间感知情况，后续正式的音频空间感评估将只有空间感一致性评估，将更加简单\n
                    • 距离：表示声音来源距离（0-10米）\n
                    • 方位角：表示声音来源方向（-180至180度）\n
                    - 以您的正前方为0度，正右方为90度，粉色弧线辅助您获取大致的方向\n
                    • 仰角：表示声音来源高度（-10至10米）\n
                    • 3D图示说明：\n
                    - 黑点：您所处的位置\n
                    - 蓝点：您判断的声音来源位置\n
                    - 绿色：指向您的正前方

                    ### 三、正式评估
                    • 在音频评估页面，请认真听取每个音频并给出音质评分以及空间感（声源）一致性评分（通过图像判断，声音是否来自这一方向）！\n
                    • 空间感一致性评分范围：1-5分（1分为根本不是这个方向，5分为方向是完全匹配的）

                    ### 四、评估许可
                    • 请确认您已阅读并理解以上注意事项，同意参与本评估测试，并同意收集的内容供研究所用。\n
                    • 您的个人信息将被严格保密，不会被用于任何商业目的，不会被公开共享。本评估测试仅用于研究目的，不涉及任何个人隐私。\n
                    • 本页面与本评估版权归nbu.wxx所有，仅被用于内部研究。
                    """
            )
            note_agreement = gr.Checkbox(label="我已阅读并知晓以上注意事项")

            info_submit_button = gr.Button("提交信息")

            def show_other_device_model(choice):
                if choice == "其他":
                    return gr.update(visible=True)
                else:
                    return gr.update(visible=False)

            device_model_input.change(
                show_other_device_model,
                inputs=[device_model_input],
                outputs=[other_device_model_input]
            )
            

        # 音频测试页面（资格测试）
        with gr.Column(visible=False) as audio_test_col:
            gr.Markdown("## 资格测试")
            # 添加固定定位的评分标准表格
            rating_criteria_css = """
            <style>
            .rating-criteria {
                position: fixed;
                top: 10px;
                left: 10px;  /* 从right: 10px改为left: 10px */
                width: 300px;
                background-color: white;
                border: 1px solid #ddd;
                border-radius: 8px;
                padding: 10px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                z-index: 1000;
                max-height: 80vh;
                overflow-y: auto;
            }
            .rating-criteria h3 {
                margin-top: 0;
                color: #333;
                font-size: 16px;
            }
            .rating-criteria table {
                width: 100%;
                border-collapse: collapse;
                font-size: 14px;
            }
            .rating-criteria th, .rating-criteria td {
                border: 1px solid #ddd;
                padding: 5px;
                text-align: left;
            }
            .rating-criteria th {
                background-color: #f5f5f5;
            }
            </style>
            """
            
            # 评分标准HTML内容
            rating_criteria_html = f"""
            {rating_criteria_css}
            <div class="rating-criteria">
                <h3>评分标准参考</h3>
                
                <h4>音频质量评估说明</h4>
                <ul>
                    <li>您可以通过参考音频来对失真音频进行打分</li>
                    <li>参考音频是被认为干净无噪声的最高分音频（5分），后续正式的音频评估将没有参考音频</li>
                    <li>请忽视内容与音调，仅在音质方面给出评分</li>
                    <li>评分范围：1-5分（1分为音质最差，5分为音质最好）</li>
                </ul>
                
                <h4>空间感知评估说明</h4>
                <ul>
                    <li>主要关注个人空间感知情况，后续正式的音频空间感评估将只有空间感一致性评估，将更加简单</li>
                    <li>距离：表示声音来源距离（0-10米）</li>
                    <li>方位角：表示声音来源方向（-180至180度）</li>
                        <li>以您的正前方为0度，正右方为90度，粉色弧线辅助您获取大致的方向</li>
                    <li>仰角：表示声音来源高度（-10至10米）</li>
                    <li>3D图示说明：</li>
                    <ul>
                        <li>黑点：您所处的位置</li>
                        <li>蓝点：您判断的声音来源位置</li>
                        <li>绿色：指向您的正前方</li>
                    </ul>
                </ul>
            </div>
            """
            
            # 使用HTML组件显示评分标准
            gr.HTML(rating_criteria_html)

            markdown_text = '<span style="font-size: 15px; color: grey;">## 接下来请听音频给出质量打分，打分后点击"确定"将会显示参考分数，您可以作为后续评估的参考</span>'
            gr.Markdown(markdown_text)
            # 存储每个问题的组件
            audio_players = []
            # option_radios = []
            confirm_buttons = []
            feedback_texts = []
            rating_sliders = []
            # test_js_code = ""

            # 前五个音频的质量评分测试
            for i in range(5):
                with gr.Row():
                    # 对于前5个音频，显示参考音频
                    with gr.Column(scale=1):
                        ref_audio_player = gr.Audio(label=f"参考音频{i + 1}", value=audio_files_ref[i], type="filepath", interactive=False, elem_id=f"test_ref_audio_{i}")
                    with gr.Column(scale=1):
                        audio_player = gr.Audio(label=f"音频{i + 1}", value=audio_files_test[i], type="filepath", interactive=False, elem_id=f"test_deg_audio_{i}")
                    with gr.Column(scale=1):
                        rating_slider = gr.Slider(label=f"音频{i + 1}质量评分", minimum=1, maximum=5, step=0.1, value=3, elem_id=f"test_rating_{i}")
                        rating_sliders.append(rating_slider)
                        audio_players.append(audio_player)
                
                with gr.Row():
                    confirm_button = gr.Button(f"确认评分{i + 1}", elem_id=f"test_confirm_{i}")
                    confirm_buttons.append(confirm_button)
                
                with gr.Row():
                    feedback_text = gr.Textbox(label=f"音频反馈结果{i + 1}", visible=True, elem_id=f"test_feedback_{i}")
                    feedback_texts.append(feedback_text)

                    def create_confirm_handler(idx):
                        def handle_confirm(username, score):
                            try:
                                # 添加输入验证
                                if not username:
                                    return [gr.update(interactive=True), gr.update(value="请先输入用户名")]
                                
                                # 调用on_confirm获取正确答案
                                result, _ = on_confirm(username, idx, score, 0, 0, 0)
                                
                                # 禁用滑块并显示包含正确答案的反馈
                                return [
                                    gr.update(interactive=False),
                                    gr.update(value=result)
                                ]
                            except Exception as e:
                                error_msg = f"处理反馈时出错: {str(e)}"
                                print(error_msg)
                                # 确保反馈文本可见并显示错误信息
                                return [
                                    gr.update(interactive=True),  # rating slider
                                    gr.update(value=error_msg)  # show error
                                ]
                        return handle_confirm

                    # 修改绑定确认按钮事件
                    confirm_buttons[i].click(
                        fn=create_confirm_handler(i),
                        inputs=[username_input, rating_sliders[i]],
                        outputs=[rating_sliders[i], feedback_texts[i]]
                    )

            # 后四个音频的空间位置判断测试
            markdown_text = '<span style="font-size: 15px; color: grey;">## 注意：空间一致性评分=通过查看图像判断声音是否来自这一方向，评分范围：1-5分（1分为根本不是这个方向，5分为方向是完全匹配的）</span>'
            gr.Markdown(markdown_text)
            
            # 存储空间位置选择的组件
            space_controls = []
            space_images = []  # 存储三视图组件

            # 创建四个空间控制组件
            for i in range(4):
                audio_idx = i  # 使用前四个音频文件索引0-3
                with gr.Row():
                    audio_player = gr.Audio(
                        label=f"音频{audio_idx + 1}空间评估",
                        value=audio_files_test[audio_idx] if audio_idx < len(audio_files_test) else None,
                        type="filepath",
                        interactive=False
                    )
                    audio_players.append(audio_player)
                    
                    with gr.Column():
                        # 距离选择
                        distance_slider = gr.Slider(
                            label=f"声源距离 (0-10)",
                            minimum=0,
                            maximum=10,
                            step=0.1,
                            value=5,
                            interactive=True, 
                            elem_id=f"space_distance_{i}"
                        )
                        # 方位角选择
                        azimuth_slider = gr.Slider(
                            label=f"声源方位角 (-180° 到 180°)",
                            minimum=-180,
                            maximum=180,
                            step=1,
                            value=0,
                            interactive=True, elem_id=f"space_azimuth_{i}"
                        )
                        # 高度选择
                        height_slider = gr.Slider(
                            label=f"声源高度 (-10 到 10)",
                            minimum=-10,
                            maximum=10,
                            step=0.1,
                            value=0,
                            interactive=True, elem_id=f"space_height_{i}"
                        )
                    
                    # 将滑块添加到space_controls列表
                    space_controls.append((distance_slider, azimuth_slider, height_slider))
                
                # 三视图显示 - 不设置初始图像
                view_image = gr.Image(label="空间位置三视图", interactive=False, value=DEFAULT_VIEW_IMG, elem_id=f"space_view_{i}")

                space_images.append(view_image)

                update_view = create_update_view_func(audio_idx)
                # 使用gr.on来绑定事件
                gr.on(
                    triggers=[distance_slider.change, azimuth_slider.change, height_slider.change],
                    fn=update_view,
                    inputs=[distance_slider, azimuth_slider, height_slider],
                    outputs=[view_image]     # ← 用列表
                    # queue=False
                )

                
                with gr.Row():
                    confirm_button = gr.Button(f"确认{audio_idx + 1}", elem_id=f"space_confirm_{i}")
                    confirm_buttons.append(confirm_button)
                
                with gr.Row():
                    feedback_text = gr.Textbox(label=f"反馈结果{audio_idx + 1}", visible=True, elem_id=f"space_feedback_{i}")
                    feedback_texts.append(feedback_text)

                    # 统一的空间确认按钮处理函数
                    def create_space_feedback_handler(idx):
                        def handle_space_feedback(username, d, a, h):
                            try:
                                # 计算正确的索引
                                space_idx = idx
                                  
                                # 获取正确的空间数据
                                correct_distance = correct_distances[space_idx] if space_idx < len(correct_distances) else 5.0
                                correct_azimuth = correct_azimuths[space_idx] if space_idx < len(correct_azimuths) else 0
                                correct_elevation = correct_elevations[space_idx] if space_idx < len(correct_elevations) else 0.0
                                
                                # 生成正确答案的图像
                                correct_image = create_views(correct_distance, correct_azimuth, correct_elevation)
                                
                                # 调用on_confirm函数
                                result, _ = on_confirm(username, idx + 5, 0, d, a, h)
                                
                                # 返回禁用的滑块、反馈文本和正确答案的图像
                                return [
                                    gr.update(interactive=False),  # distance slider
                                    gr.update(interactive=False),  # azimuth slider
                                    gr.update(interactive=False),  # height slider
                                    gr.update(value=result),  # feedback text
                                    gr.update(value=correct_image if correct_image is not None else None)  # 只在图像存在时更新
                                ]
                            except Exception as e:
                                print(f"Error in space feedback handler {idx}: {str(e)}")
                                # 出错时也返回有效的响应
                                return [
                                    gr.update(interactive=True),
                                    gr.update(interactive=True),
                                    gr.update(interactive=True),
                                    gr.update(value=f"处理反馈时出错: {str(e)}"),
                                    gr.update()  # 出错时不更新图像，避免DOM错误
                                ]
                        return handle_space_feedback

                    # 单一的事件绑定，处理所有输出
                    confirm_buttons[5 + audio_idx].click(
                        fn=create_space_feedback_handler(audio_idx),
                        inputs=[username_input, space_controls[audio_idx][0], space_controls[audio_idx][1], space_controls[audio_idx][2]],
                        outputs=[
                            space_controls[audio_idx][0], 
                            space_controls[audio_idx][1], 
                            space_controls[audio_idx][2], 
                            feedback_texts[5 + audio_idx],
                            space_images[audio_idx]
                        ]
                    )


            # 跳转按钮（初始设置为不可见）
            jump_button = gr.Button("点击跳转到音频评估页面", visible=False)

            # 修改为每个确认按钮添加检查，只控制跳转按钮
            gr.on(
                triggers=[btn.click for btn in confirm_buttons],
                fn=lambda: gr.update(visible=True),
                inputs=[],
                outputs=[jump_button]
                # queue=False
            )

        # 音频评估页面
        with gr.Column(visible=False) as audio_eval_col:
            gr.Markdown("## 音频评估")
            
            # 添加固定定位的评分标准表格
            rating_criteria_css = """
            <style>
            .rating-criteria {
                position: fixed;
                top: 10px;
                left: 10px;  /* 从right: 10px改为left: 10px */
                width: 300px;
                background-color: white;
                border: 1px solid #ddd;
                border-radius: 8px;
                padding: 10px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                z-index: 1000;
                max-height: 80vh;
                overflow-y: auto;
            }
            .rating-criteria h3 {
                margin-top: 0;
                color: #333;
                font-size: 16px;
            }
            .rating-criteria table {
                width: 100%;
                border-collapse: collapse;
                font-size: 14px;
            }
            .rating-criteria th, .rating-criteria td {
                border: 1px solid #ddd;
                padding: 5px;
                text-align: left;
            }
            .rating-criteria th {
                background-color: #f5f5f5;
            }
            </style>
            """
            
            # 评分标准HTML内容
            rating_criteria_html = f"""
            {rating_criteria_css}
            <div class="rating-criteria">
                <h3>评分标准参考</h3>
                
                <h4>音频质量评分标准</h4>
                <table>
                    <tr>
                        <th>分值</th>
                        <th>等级</th>
                    </tr>
                    <tr>
                        <td>5-优秀</td>
                        <td>听起来非常自然、干净、真实，没有明显杂音或失真</td>
                    </tr>
                    <tr>
                        <td>4-良好</td>
                        <td>声音总体清晰自然，有轻微问题但不影响聆听</td>
                    </tr>
                    <tr>
                        <td>3-一般</td>
                        <td>声音基本可听，但能明显察觉一些问题</td>
                    </tr>
                    <tr>
                        <td>2-较差</td>
                        <td>声音不自然，有明显噪声、模糊或刺耳感</td>
                    </tr>
                    <tr>
                        <td>1-很差</td>
                        <td>声音严重失真、含糊或噪声太多，难以听清</td>
                    </tr>
                </table>
                
                <h4>空间感一致性评分标准</h4>
                <table>
                    <tr>
                        <th>分值</th>
                        <th>等级</th>
                    </tr>
                    <tr>
                        <td>5-优秀</td>
                        <td>声音方向和距离完全准确、自然，空间感逼真</td>
                    </tr>
                    <tr>
                        <td>4-良好</td>
                        <td>声音方向和空间感大致正确，偶尔有轻微偏差</td>
                    </tr>
                    <tr>
                        <td>3-一般</td>
                        <td>基本能感觉到不同方向或远近，但偶尔会错位</td>
                    </tr>
                    <tr>
                        <td>2-较差</td>
                        <td>方向或距离经常不对，空间感弱或不自然</td>
                    </tr>
                    <tr>
                        <td>1-很差</td>
                        <td>声音都挤在一起或方向混乱，没有真实空间感</td>
                    </tr>
                </table>
            </div>
            """
            
            # 使用HTML组件显示评分标准
            gr.HTML(rating_criteria_html)
            
            # 原有页面内容
            markdown_text = '<span style="font-size: 15px; color: grey;">## 接下来请听音频给出空间位置判断，选择后点击"确定"将会显示参考方位，您可以作为后续评估的参考</span>'
            rating_inputs_eval = []
            spatial_rating_inputs = []  # 空间感一致性评分输入
            audio_players = []
            space_images = []  # 存储空间坐标系图像
            
            # 52个音频的质量评分和空间感一致性评分
            for i in range(52):
                with gr.Row():
                    # 安全处理音频文件路径
                    audio_file_path = None
                    if audio_files_eval and i < len(audio_files_eval):
                        file_path = audio_files_eval[i]
                        # 确保是有效的文件路径而不是错误信息字符串
                        if isinstance(file_path, str) and os.path.exists(file_path) and os.path.isfile(file_path):
                            audio_file_path = os.path.normpath(file_path)
                        else:
                            print(f"警告：无效的音频文件路径: {file_path}")
                    
                    # 创建音频播放器，即使没有文件也创建UI组件
                    audio_player = gr.Audio(
                        label=f"音频{i + 1}播放", 
                        value=audio_file_path,  # 可能为None，但不会导致错误
                        type="filepath", 
                        elem_id=f"eval_audio_{i}"
                    )
                    audio_players.append(audio_player)
                
                with gr.Row():
                    # 质量评分部分
                    rating_input = gr.Slider(
                        label=f"音频{i + 1}质量评分 (1到5分)",
                        minimum=1,
                        maximum=5,
                        step=0.1,
                        value=3.0,  # 设置默认值
                        interactive=True, elem_id=f"eval_rating_{i}"
                    )
                    rating_inputs_eval.append(rating_input)
                    
                    # 空间感一致性评分部分
                    with gr.Column():
                        spatial_rating = gr.Slider(
                            label=f"音频{i + 1}空间感一致性评分 (1到5分)",
                            minimum=1,
                            maximum=5,
                            step=0.1,
                            value=3.0,  # 设置默认值
                            interactive=True, elem_id=f"eval_spatial_{i}"
                        )
                        spatial_rating_inputs.append(spatial_rating)
                        
                        # 获取当前音频文件名（安全处理）
                        audio_filename = "" 
                        if audio_files_eval and i < len(audio_files_eval):
                            audio_filename = os.path.basename(audio_files_eval[i])
                        
                        # 查找对应的空间数据
                        distance = 5.0
                        azimuth = 0.0
                        height = 0.0
                        
                        # 首先尝试从snr_30.csv创建的映射中获取空间数据
                        if audio_filename and audio_filename in audio_to_spatial_data:
                            # print(f"从snr_30.csv映射中找到音频{audio_filename}的空间数据")
                            spatial_data = audio_to_spatial_data[audio_filename]
                            distance = spatial_data['distance']
                            azimuth = spatial_data['azimuth']
                            height = spatial_data['elevation']
                        # 如果从snr_30.csv没有找到，仍然可以尝试从原来的space_file_names中查找作为后备
                        elif audio_filename and space_file_names:
                            for j, filename in enumerate(space_file_names):
                                if filename == audio_filename:
                                    distance = correct_distances[j] if j < len(correct_distances) else 5.0
                                    azimuth = correct_azimuths[j] if j < len(correct_azimuths) else 0.0
                                    height = correct_elevations[j] if j < len(correct_elevations) else 0.0
                                    break
                        
                        # 空间坐标系图像显示
                        initial_image = None
                        try:
                            if audio_filename in audio_to_spatial_data:
                                spatial_data = audio_to_spatial_data[audio_filename]
                                distance = spatial_data['distance']
                                azimuth = spatial_data['azimuth']
                                height = spatial_data['elevation']
                                initial_image = create_views(distance, azimuth, height)
                        except Exception as e:
                            print(f"创建初始图像时出错: {str(e)}")
                            initial_image = DEFAULT_VIEW_IMG

                        view_image = gr.Image(
                            label="空间位置三视图", 
                            interactive=False,
                            value=initial_image if initial_image else DEFAULT_VIEW_IMG, 
                            elem_id=f"eval_view_{i}"
                        )
                        space_images.append(view_image)
            
            # 提交评估按钮
            eval_submit_button = gr.Button("提交评估")
            output_text = gr.Textbox(label="保存结果")
            
            # 绑定提交评估按钮事件到专用的评估页面处理函数
            eval_submit_button.click(
                fn=handle_submit_eval,  # 使用评估页面专用的处理函数
                inputs=[
                    username_input,
                    device_type_input,
                    device_model_input,
                    gender_input,
                    birth_year_input,
                    hearing_impaired_input,
                    nationality_input,
                    audio_test_input,
                    note_agreement
                ] + rating_inputs_eval + spatial_rating_inputs,
                outputs=output_text
            )

            def jump_to_eval():
                # 添加JavaScript来滚动到顶部
                # js_scroll = "window.scrollTo({top: 0, behavior: 'smooth'});"
                # 页面切换逻辑和JavaScript滚动
                return gr.update(visible=False), gr.update(visible=True), "音频评估"

            jump_button.click(
                fn=jump_to_eval,
                inputs=[],
                outputs=[audio_test_col, audio_eval_col, current_step]
            )

        # 点击"提交信息"后更新 State 状态，并通过 State 控制页面显示
        def on_info_submit(username, device_type, device_model, other_device_model, gender, birth_year, hearing_impaired, nationality, audio_test, note_agreement, current_step):
            if device_model == "其他":
                device_model = other_device_model
            if username and device_type and device_model and gender and birth_year and hearing_impaired is not None and nationality and audio_test is not None and note_agreement:
                return "信息提交成功！现在可以开始测试音频。", gr.update(visible=False), gr.update(visible=True), gr.update(visible=False), "音频测试"
            else:
                return "请填写所有信息！", gr.update(visible=True), gr.update(visible=False), gr.update(visible=False), current_step

        info_submit_button.click(
            on_info_submit,
            inputs=[username_input, device_type_input, device_model_input, other_device_model_input, gender_input, birth_year_input, hearing_impaired_input, nationality_input, audio_test_input, note_agreement, current_step],
            outputs=[output_text, info_col, audio_test_col, audio_eval_col, current_step]
        )

    return demo

