import os

# 获取当前文件所在目录的绝对路径
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))

# 配置文件，定义常量
# SAVE_FOLDER = r"D:\WXX\UDiffText-main\audio_demo6"  # 修改为您的自定义保存路径
# SAVE_FILE = os.path.join(SAVE_FOLDER, "evalute_score.csv")
SAVE_FILE = r"D:\WXX\UDiffText-main\audio_demo6\evalute_score.csv"
# print(SAVE_FILE)  # 打印保存路径用于调试

# 音频文件夹路径
AUDIO_FOLDER_TEST = r"D:\WXX\UDiffText-main\audio_demo6\deg"
AUDIO_FOLDER_EVAL = r"D:\WXX\pyroom\listen"
AUDIO_FOLDER_REF = r"D:\WXX\UDiffText-main\audio_demo6\ref"
SPACE_AUDIO_FOLDER = r"D:\WXX\UDiffText-main\audio_demo6\space"

# CSV文件路径
ANSWERS_CSV_PATH = os.path.join(AUDIO_FOLDER_REF, "ref_audio.csv")
SPACE_ANSWERS_CSV_PATH = os.path.join(SPACE_AUDIO_FOLDER, "ref_space.csv")
# SNR_CSV_PATH = os.path.join(CURRENT_DIR, "SNR_30.csv")#评估页面的空间信息
DEV_SPACE_PATH = r"D:\WXX\UDiffText-main\audio_demo6\our52_5.csv"
# 评分保存文件路径
TEST_AUDIO_CSV_PATH = os.path.join(CURRENT_DIR, "test_audio.csv")
TEST_SPACE_CSV_PATH = os.path.join(CURRENT_DIR, "test_space.csv")

# FIG_SIZE = (6, 6)        # 统一图像尺寸（原来是 (3,3)）
# FIG_DPI = 110            # 统一 DPI（原来保存时 dpi=40）
# FONT_SIZE = 13           # 统一字体大小
# TICK_TARGET = 7          # 目标刻度数量（控制密度）
# CROSSHAIR_ALPHA = 0.35   # 十字参考线透明度
# CROSSHAIR_LW = 1.2       # 十字参考线线宽
# POINT_SIZE = 90          # 点大小（看得清但不挡视线）