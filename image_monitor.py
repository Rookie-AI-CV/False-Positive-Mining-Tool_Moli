import tkinter as tk
from tkinter import ttk, messagebox
import os
import shutil
import time
from datetime import datetime
import threading
from PIL import Image, ImageTk
import io
import zipfile
import consolidate_images
from config import *

class ImagePreviewWindow:
    def __init__(self, parent, image_path):
        self.window = tk.Toplevel(parent)
        self.window.title("图片预览")
        
        # 获取屏幕尺寸
        screen_width = self.window.winfo_screenwidth()
        screen_height = self.window.winfo_screenheight()
        
        # 加载图片
        image = Image.open(image_path)
        
        # 计算缩放比例，使图片适应屏幕
        width_ratio = screen_width * 0.8 / image.width
        height_ratio = screen_height * 0.8 / image.height
        scale_ratio = min(width_ratio, height_ratio)
        
        # 缩放图片
        new_width = int(image.width * scale_ratio)
        new_height = int(image.height * scale_ratio)
        image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
        
        # 转换为PhotoImage
        self.photo = ImageTk.PhotoImage(image)
        
        # 创建标签显示图片
        label = tk.Label(self.window, image=self.photo)
        label.pack(padx=10, pady=10)
        
        # 添加关闭按钮
        close_button = ttk.Button(self.window, text="关闭", command=self.window.destroy)
        close_button.pack(pady=5)

class ImageScanner:
    def __init__(self, source_dir, target_dir, status_label, preview_frame, stats_label):
        self.source_dir = source_dir
        self.target_dir = target_dir
        self.status_label = status_label
        self.preview_frame = preview_frame
        self.stats_label = stats_label
        self.processed_files = set()
        self.is_running = True
        self.scan_thread = None
        self.photo_images = []  # 保持对PhotoImage的引用
        print(f"初始化扫描器: 源目录={source_dir}, 目标目录={target_dir}")
        self.start_scanning()

    def start_scanning(self):
        self.scan_thread = threading.Thread(target=self._scan_loop)
        self.scan_thread.daemon = True
        self.scan_thread.start()
        print("开始扫描")

    def _scan_loop(self):
        while self.is_running:
            try:
                self._scan_directory()
                self._update_preview()
                time.sleep(1)  # 每秒扫描一次
            except Exception as e:
                error_msg = f"扫描出错: {str(e)}"
                self.status_label.config(text=error_msg)
                print(error_msg)

    def _scan_directory(self):
        if not os.path.exists(self.source_dir):
            print(f"源目录不存在: {self.source_dir}")
            return

        # 获取源目录中的所有文件
        try:
            files = os.listdir(self.source_dir)
        except Exception as e:
            print(f"读取目录失败: {str(e)}")
            return

        for filename in files:
            if filename.lower().endswith(IMAGE_EXTENSION):
                # 检查文件是否已处理
                if filename in self.processed_files:
                    continue

                source_path = os.path.join(self.source_dir, filename)
                
                # 确保文件存在且不是目录
                if not os.path.isfile(source_path):
                    continue

                try:
                    # 创建目标目录
                    os.makedirs(self.target_dir, exist_ok=True)
                    
                    # 构建目标路径
                    target_path = os.path.join(self.target_dir, filename)
                    
                    # 移动文件
                    shutil.move(source_path, target_path)
                    
                    # 更新状态
                    current_time = datetime.now().strftime("%H:%M:%S")
                    status_text = f"状态: {current_time} - 已移动文件: {filename}"
                    self.status_label.config(text=status_text)
                    
                    # 记录已处理的文件
                    self.processed_files.add(filename)
                    print(f"已移动文件: {filename} -> {target_path}")
                    
                except Exception as e:
                    error_msg = f"移动文件 {filename} 时出错: {str(e)}"
                    self.status_label.config(text=error_msg)
                    print(error_msg)

    def _update_preview(self):
        if not os.path.exists(self.target_dir):
            return

        # 清除现有的预览
        for widget in self.preview_frame.winfo_children():
            widget.destroy()
        self.photo_images.clear()

        # 获取目标目录中的所有PNG文件
        try:
            files = [f for f in os.listdir(self.target_dir) if f.lower().endswith(IMAGE_EXTENSION)]
            files.sort(key=lambda x: os.path.getmtime(os.path.join(self.target_dir, x)), reverse=True)
            
            # 更新统计信息
            self.stats_label.config(text=f"图片总数: {len(files)}")
            
            # 创建预览网格
            row = 0
            col = 0
            max_cols = 4  # 每行最多显示4张图片
            
            for filename in files:
                try:
                    # 加载并缩放图片
                    image_path = os.path.join(self.target_dir, filename)
                    image = Image.open(image_path)
                    image.thumbnail((150, 150))  # 缩略图大小
                    photo = ImageTk.PhotoImage(image)
                    self.photo_images.append(photo)  # 保持引用
                    
                    # 创建图片按钮
                    btn = ttk.Button(self.preview_frame, image=photo, 
                                   command=lambda p=image_path: self._show_preview(p))
                    btn.grid(row=row, column=col, padx=5, pady=5)
                    
                    col += 1
                    if col >= max_cols:
                        col = 0
                        row += 1
                        
                except Exception as e:
                    print(f"加载预览图片失败 {filename}: {str(e)}")
                    
        except Exception as e:
            print(f"更新预览失败: {str(e)}")

    def _show_preview(self, image_path):
        ImagePreviewWindow(self.preview_frame.winfo_toplevel(), image_path)

class ImageMonitorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("图片监控系统")
        self.root.geometry("800x600")
        
        # 创建变量
        self.source_dir = tk.StringVar()
        self.target_root_dir = tk.StringVar()
        self.selected_location = tk.StringVar()
        self.selected_object = tk.StringVar()
        
        # 创建界面
        self.create_widgets()
        
        # 初始化扫描器
        self.scanner = None

        # 绑定所有配置变更事件
        self.source_dir.trace_add("write", self._on_config_change)
        self.target_root_dir.trace_add("write", self._on_config_change)
        self.selected_location.trace_add("write", self._on_config_change)
        self.selected_object.trace_add("write", self._on_config_change)

    def _on_config_change(self, *args):
        # 检查所有必要的配置是否已设置
        if (self.source_dir.get() and 
            self.target_root_dir.get() and 
            self.selected_location.get() and 
            self.selected_object.get()):
            
            # 停止当前扫描器
            if self.scanner:
                self.scanner.is_running = False
                if self.scanner.scan_thread:
                    self.scanner.scan_thread.join()
                self.scanner = None
            
            # 创建新的扫描器
            target_dir = os.path.join(self.target_root_dir.get(), 
                                    self.selected_location.get(), 
                                    self.selected_object.get())
            self.scanner = ImageScanner(self.source_dir.get(), target_dir, 
                                      self.status_label, self.preview_frame, self.stats_label)
            self.status_label.config(text=f"状态: 正在监控 {self.source_dir.get()}")
        else:
            # 如果配置不完整，停止监控
            if self.scanner:
                self.scanner.is_running = False
                if self.scanner.scan_thread:
                    self.scanner.scan_thread.join()
                self.scanner = None
            self.status_label.config(text="状态: 等待配置完成")

    def create_widgets(self):
        # 创建左右分栏
        paned = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True)
        
        # 左侧控制面板
        control_frame = ttk.Frame(paned)
        paned.add(control_frame, weight=1)
        
        # 源目录选择
        source_frame = ttk.LabelFrame(control_frame, text="源目录设置", padding=10)
        source_frame.pack(fill="x", padx=10, pady=5)
        
        ttk.Entry(source_frame, textvariable=self.source_dir, width=50).pack(side="left", padx=5)
        ttk.Button(source_frame, text="选择目录", command=self.select_source_dir).pack(side="left", padx=5)
        
        # 目标根目录选择
        target_root_frame = ttk.LabelFrame(control_frame, text="目标根目录设置", padding=10)
        target_root_frame.pack(fill="x", padx=10, pady=5)
        
        ttk.Entry(target_root_frame, textvariable=self.target_root_dir, width=50).pack(side="left", padx=5)
        ttk.Button(target_root_frame, text="选择目录", command=self.select_target_root_dir).pack(side="left", padx=5)
        
        # 目标设置
        target_frame = ttk.LabelFrame(control_frame, text="目标设置", padding=10)
        target_frame.pack(fill="x", padx=10, pady=5)
        
        # 地点选择
        location_frame = ttk.Frame(target_frame)
        location_frame.pack(fill="x", pady=5)
        ttk.Label(location_frame, text="地点:").pack(side="left", padx=5)
        ttk.Combobox(location_frame, textvariable=self.selected_location, values=LOCATIONS, state="readonly").pack(side="left", padx=5)
        
        # 对象选择
        object_frame = ttk.Frame(target_frame)
        object_frame.pack(fill="x", pady=5)
        ttk.Label(object_frame, text="对象:").pack(side="left", padx=5)
        ttk.Combobox(object_frame, textvariable=self.selected_object, values=OBJECTS, state="readonly").pack(side="left", padx=5)
        
        # 汇总按钮
        consolidate_frame = ttk.Frame(control_frame)
        consolidate_frame.pack(fill="x", padx=10, pady=5)
        ttk.Button(consolidate_frame, text="汇总并压缩", command=self.consolidate_and_zip).pack(pady=5)
        
        # 状态显示
        self.status_label = ttk.Label(control_frame, text="状态: 未开始监控")
        self.status_label.pack(pady=5)
        
        # 右侧预览面板
        preview_frame = ttk.Frame(paned)
        paned.add(preview_frame, weight=2)
        
        # 预览标题和统计
        preview_header = ttk.Frame(preview_frame)
        preview_header.pack(fill="x", padx=10, pady=5)
        ttk.Label(preview_header, text="图片预览", font=("Arial", 12, "bold")).pack(side="left")
        self.stats_label = ttk.Label(preview_header, text="图片总数: 0")
        self.stats_label.pack(side="right")
        
        # 预览区域（带滚动条）
        preview_canvas = tk.Canvas(preview_frame)
        scrollbar = ttk.Scrollbar(preview_frame, orient="vertical", command=preview_canvas.yview)
        self.preview_frame = ttk.Frame(preview_canvas)
        
        preview_canvas.configure(yscrollcommand=scrollbar.set)
        
        scrollbar.pack(side="right", fill="y")
        preview_canvas.pack(side="left", fill="both", expand=True)
        
        preview_canvas.create_window((0, 0), window=self.preview_frame, anchor="nw")
        self.preview_frame.bind("<Configure>", lambda e: preview_canvas.configure(scrollregion=preview_canvas.bbox("all")))

    def select_source_dir(self):
        from tkinter import filedialog
        directory = filedialog.askdirectory()
        if directory:
            self.source_dir.set(directory)
            print(f"已选择源目录: {directory}")

    def select_target_root_dir(self):
        from tkinter import filedialog
        directory = filedialog.askdirectory()
        if directory:
            self.target_root_dir.set(directory)
            print(f"已选择目标根目录: {directory}")

    def consolidate_and_zip(self):
        if not self.target_root_dir.get():
            messagebox.showerror("错误", "请选择目标根目录")
            return

        try:
            # 获取目标根目录名称
            target_dir_name = os.path.basename(self.target_root_dir.get())
            
            # 运行汇总程序
            temp_dir = consolidate_images.main(self.target_root_dir.get())
            
            # 创建压缩文件
            zip_name = f"{target_dir_name}.zip"
            with zipfile.ZipFile(zip_name, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for root, dirs, files in os.walk(temp_dir):
                    for file in files:
                        file_path = os.path.join(root, file)
                        arcname = os.path.relpath(file_path, temp_dir)
                        zipf.write(file_path, arcname)
            
            # 删除临时目录
            shutil.rmtree(temp_dir)
            
            messagebox.showinfo("成功", f"汇总完成，已生成压缩包：{zip_name}")
            
        except Exception as e:
            messagebox.showerror("错误", f"汇总失败: {str(e)}")

if __name__ == "__main__":
    root = tk.Tk()
    app = ImageMonitorApp(root)
    root.mainloop() 