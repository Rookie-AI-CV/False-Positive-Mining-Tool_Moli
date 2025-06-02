import os
import shutil
from datetime import datetime
from config import *

def main(target_root_dir):
    # 创建临时目录
    temp_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), TEMP_DIR_NAME)
    os.makedirs(temp_dir, exist_ok=True)
    
    # 创建烟雾和火焰子目录
    smoke_dir = os.path.join(temp_dir, SMOKE_DIR_NAME)
    fire_dir = os.path.join(temp_dir, FIRE_DIR_NAME)
    os.makedirs(smoke_dir, exist_ok=True)
    os.makedirs(fire_dir, exist_ok=True)
    
    # 遍历目标根目录下的所有子目录
    for root, dirs, files in os.walk(target_root_dir):
        # 跳过临时目录
        if TEMP_DIR_NAME in root:
            continue
            
        # 只处理目标根目录下的图片
        if root == target_root_dir:
            continue
            
        # 确定目标目录（烟雾或火焰）
        if os.path.basename(root) == SMOKE_DIR_NAME:
            target_dir = smoke_dir
        elif os.path.basename(root) == FIRE_DIR_NAME:
            target_dir = fire_dir
        else:
            continue
            
        # 复制所有PNG文件到对应目录
        for file in files:
            if file.lower().endswith(IMAGE_EXTENSION):
                source_path = os.path.join(root, file)
                target_path = os.path.join(target_dir, file)
                
                # 如果目标文件已存在，添加序号
                base, ext = os.path.splitext(file)
                counter = 1
                while os.path.exists(target_path):
                    target_path = os.path.join(target_dir, f"{base}_{counter}{ext}")
                    counter += 1
                
                shutil.copy2(source_path, target_path)
                print(f"已复制: {source_path} -> {target_path}")
    
    return temp_dir

if __name__ == "__main__":
    main() 