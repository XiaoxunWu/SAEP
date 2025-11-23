import os
import pandas as pd
import datetime

# 从配置文件导入常量
from config import SAVE_FILE

def save_rating_to_file(username, device_type, device_model, other_device_model, gender, birth_year, hearing_impaired, nationality, audio_test, note_agreement, ratings, *args):
    try:
        # 处理设备型号为"其他"的情况
        if device_model == "其他":
            device_model = other_device_model

        # 确保 birth_year 可以转换为整数
        try:
            birth_year = int(birth_year)
        except ValueError:
            return f"保存评分时出错: 出生年份 '{birth_year}' 不是有效的整数。"
        # 计算年龄
        current_year = datetime.datetime.now().year
        age = current_year - birth_year

        # 判断是测试页面还是评估页面
        # 如果参数数量 >= 6，说明是测试页面（包含音频文件和所有细节分数）
        # 如果参数数量 == 2，说明是评估页面（只包含空间一致性分数和音频文件）
        is_evaluation_page = len(args) == 2
        
        if is_evaluation_page:
            # 评估页面逻辑：只保存音频质量分数和空间一致性分数
            spatial_ratings = args[0]
            audio_files = args[1]
            
            # 检查评分和音频文件数量是否一致
            num_audios = len(audio_files)
            if len(ratings) != num_audios or len(spatial_ratings) != num_audios:
                return f"保存评分时出错: 评分、空间一致性评分和音频文件数量不匹配。"
            
            # 准备数据
            data = []
            for i in range(num_audios):
                row = {
                    "用户名": username,
                    "设备类型": device_type,
                    "设备型号": device_model,
                    "性别": gender,
                    "年龄": age,
                    "是否有耳部疾病等听力受损情况": hearing_impaired,
                    "国籍": nationality,
                    "是否接受过音频质量评估测试": audio_test,
                    "是否同意注意事项": note_agreement,
                    "音频路径": audio_files[i],
                    "音频质量评分": ratings[i],
                    "空间一致性评分": spatial_ratings[i]
                }
                data.append(row)
        else:
            # 测试页面逻辑：保存距离、方位角、仰角等细节分数
            if len(args) >= 4:
                distance_notes = args[0]
                azimuth_notes = args[1]
                elevation_notes = args[2]
                audio_files = args[3]
                
                # 检查是否所有列表长度一致
                num_audios = len(audio_files)
                if len(ratings) != num_audios or len(distance_notes) != num_audios or len(azimuth_notes) != num_audios or len(elevation_notes) != num_audios:
                    return f"保存评分时出错: 评分、声源位置备注和音频文件数量不匹配。"
                
                # 准备数据
                data = []
                for i in range(num_audios):
                    row = {
                        "用户名": username,
                        "设备类型": device_type,
                        "设备型号": device_model,
                        "性别": gender,
                        "年龄": age,
                        "是否有耳部疾病等听力受损情况": hearing_impaired,
                        "国籍": nationality,
                        "是否接受过音频质量评估测试": audio_test,
                        "是否同意注意事项": note_agreement,
                        "音频路径": audio_files[i],
                        "评分": ratings[i],
                        "声源距离": distance_notes[i],
                        "声源方位角": azimuth_notes[i],
                        "声源仰角": elevation_notes[i]
                    }
                    data.append(row)
            else:
                return f"保存评分时出错: 参数不足，无法处理测试页面数据。"

        # 创建DataFrame
        df = pd.DataFrame(data)

        try:
            # 如果文件存在且不为空，读取现有数据并追加
            if os.path.exists(SAVE_FILE) and os.path.getsize(SAVE_FILE) > 0:
                try:
                    existing_df = pd.read_csv(SAVE_FILE, encoding='utf-8')
                    df = pd.concat([existing_df, df], ignore_index=True, sort=False)
                except Exception as e:
                    print(f"读取现有文件时出错: {str(e)}")
                    # 如果读取失败，只保存新数据
                    pass
            
            # 保存到CSV文件
            df.to_csv(SAVE_FILE, index=False, encoding='utf-8')
            return f"评分已保存到: {SAVE_FILE}\n用户名: {username}, 设备类型: {device_type}, 设备型号: {device_model}"
        except PermissionError:
            return f"保存评分时出错: 没有权限写入文件 {SAVE_FILE}。"
        except Exception as e:
            return f"保存评分时出错: {str(e)}"

    except Exception as e:
        return f"保存评分时出错: {str(e)}"