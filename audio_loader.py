# 修改load_audio_files函数，增强错误处理和路径安全检查
import os
import pathlib

def load_audio_files(folder_path):
    """
    从指定的文件夹路径递归加载所有音频文件，包括子文件夹中的文件
    """
    audio_files = []
    try:
        # 首先检查文件夹是否存在
        if not os.path.exists(folder_path):
            return f"错误：文件夹不存在: {folder_path}"
        
        # 检查是否有读取权限
        if not os.access(folder_path, os.R_OK):
            return f"错误：没有读取文件夹的权限: {folder_path}"
        
        # 使用os.walk递归遍历所有文件夹和子文件夹
        for root, dirs, files in os.walk(folder_path):
            # 对文件名进行排序
            files.sort()
            # 只加载wav文件
            for filename in files:
                if filename.endswith(".wav"):  # 音频文件格式
                    file_path = os.path.join(root, filename)
                    # 使用pathlib确保路径格式正确且可访问
                    path_obj = pathlib.Path(file_path)
                    # 再次检查文件是否存在且可访问
                    if path_obj.exists() and path_obj.is_file() and os.access(file_path, os.R_OK):
                        # 规范化路径格式
                        audio_files.append(os.path.normpath(file_path))
        
        print(f"总共找到{len(audio_files)}个音频文件")
        return audio_files
    except PermissionError as e:
        return f"权限错误：无法访问文件夹或文件: {str(e)}"
    except Exception as e:
        return f"加载音频文件时出错: {str(e)}"
