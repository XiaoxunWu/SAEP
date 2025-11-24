import os

# 获取当前文件所在目录的绝对路径
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))

# 配置文件，定义常量
SAVE_FILE = "./evalute_score.csv"

# 音频文件夹路径
AUDIO_FOLDER_TEST = "./deg"
AUDIO_FOLDER_EVAL = "./listen"
AUDIO_FOLDER_REF = "./ref"
SPACE_AUDIO_FOLDER = "./space"

# CSV文件路径
ANSWERS_CSV_PATH = os.path.join(AUDIO_FOLDER_REF, "ref_audio.csv")
SPACE_ANSWERS_CSV_PATH = os.path.join(SPACE_AUDIO_FOLDER, "ref_space.csv")
# SNR_CSV_PATH = os.path.join(CURRENT_DIR, "SNR_30.csv")#评估页面的空间信息
DEV_SPACE_PATH = "./our52_5.csv"
# 评分保存文件路径
TEST_AUDIO_CSV_PATH = os.path.join(CURRENT_DIR, "test_audio.csv")
TEST_SPACE_CSV_PATH = os.path.join(CURRENT_DIR, "test_space.csv")
