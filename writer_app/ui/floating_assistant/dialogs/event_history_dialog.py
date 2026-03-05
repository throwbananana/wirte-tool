import tkinter as tk
from tkinter import ttk
from datetime import datetime
from writer_app.core.icon_manager import IconManager

class EventHistoryDialog(tk.Toplevel):
    """事件历史记录对话框"""
    
    def __init__(self, parent, event_system):
        super().__init__(parent)
        self.parent = parent
        self.event_system = event_system
        self.title("事件足迹")
        self.geometry("500x600")
        
        # 设置主题颜色
        self.bg_color = "#2D2D2D"
        self.fg_color = "#E0E0E0"
        self.accent_color = "#4A90E2"
        self.configure(bg=self.bg_color)
        
        self.icon_manager = IconManager()
        
        self._init_ui()
        self._load_data()
        
    def _init_ui(self):
        # 顶部标题栏
        header_frame = tk.Frame(self, bg=self.bg_color)
        header_frame.pack(fill=tk.X, padx=15, pady=15)
        
        title_label = tk.Label(
            header_frame, 
            text="✨ 助手的观察日记", 
            font=("Microsoft YaHei UI", 16, "bold"),
            bg=self.bg_color,
            fg=self.fg_color
        )
        title_label.pack(side=tk.LEFT)
        
        # 过滤选项
        filter_frame = tk.Frame(self, bg=self.bg_color)
        filter_frame.pack(fill=tk.X, padx=15, pady=(0, 10))
        
        self.filter_var = tk.StringVar(value="all")
        
        style = ttk.Style()
        style.configure("Filter.TRadiobutton", background=self.bg_color, foreground=self.fg_color)
        
        filters = [
            ("全部", "all"),
            ("成就", "achievement"),
            ("里程碑", "milestone"),
            ("互动", "interaction"),
            ("系统", "system")
        ]
        
        for text, value in filters:
            rb = ttk.Radiobutton(
                filter_frame, 
                text=text, 
                value=value, 
                variable=self.filter_var,
                style="Filter.TRadiobutton",
                command=self._load_data
            )
            rb.pack(side=tk.LEFT, padx=5)
            
        # 内容列表区
        list_frame = tk.Frame(self, bg=self.bg_color)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=(0, 15))
        
        # 滚动条
        scrollbar = ttk.Scrollbar(list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 列表画布
        self.canvas = tk.Canvas(
            list_frame, 
            bg=self.bg_color, 
            highlightthickness=0,
            yscrollcommand=scrollbar.set
        )
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        scrollbar.config(command=self.canvas.yview)
        
        # 内部容器
        self.content_frame = tk.Frame(self.canvas, bg=self.bg_color)
        self.canvas_window = self.canvas.create_window((0, 0), window=self.content_frame, anchor="nw")
        
        self.content_frame.bind("<Configure>", self._on_frame_configure)
        self.canvas.bind("<Configure>", self._on_canvas_configure)
        
        # 鼠标滚轮支持
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)

    def _on_frame_configure(self, event):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        
    def _on_canvas_configure(self, event):
        self.canvas.itemconfig(self.canvas_window, width=event.width)
        
    def _on_mousewheel(self, event):
        self.canvas.yview_scroll(int(-1*(event.delta/120)), "units")

    def _load_data(self):
        # 清空现有内容
        for widget in self.content_frame.winfo_children():
            widget.destroy()
            
        logs = self.event_system.get_event_log()
        # 倒序排列（最新的在上面）
        logs.reverse()
        
        filter_type = self.filter_var.get()
        
        for log in logs:
            event_id = log.get("id", "")
            message = log.get("message", "")
            timestamp = log.get("timestamp", "")
            
            # 分类逻辑
            category = "system"
            if "complex:" in event_id:
                category = "complex"
            elif "achievement" in event_id or "milestone" in event_id:
                category = "achievement"
            elif "interaction" in event_id or "chat" in event_id:
                category = "interaction"
            
            # 过滤
            if filter_type != "all":
                if filter_type == "achievement" and category != "achievement":
                    continue
                if filter_type == "interaction" and category != "interaction":
                    continue
                if filter_type == "system" and category != "system":
                    continue
            
            self._create_log_item(timestamp, event_id, message, category)
            
    def _create_log_item(self, timestamp, event_id, message, category):
        item_frame = tk.Frame(self.content_frame, bg=self.bg_color, pady=5)
        item_frame.pack(fill=tk.X)
        
        # 图标与颜色
        icon = "📝"
        text_color = self.fg_color
        
        if category == "complex":
            icon = "🌟" # 复合规则高亮
            text_color = "#FFD700" # 金色
        elif category == "achievement":
            icon = "🏆"
        elif category == "interaction":
            icon = "💬"
            
        # 时间格式化
        try:
            dt = datetime.fromisoformat(timestamp)
            time_str = dt.strftime("%m-%d %H:%M")
        except:
            time_str = timestamp
            
        # 布局
        top_frame = tk.Frame(item_frame, bg=self.bg_color)
        top_frame.pack(fill=tk.X)
        
        tk.Label(
            top_frame, 
            text=f"{icon} {time_str}", 
            font=("Arial", 9), 
            fg="#888888", 
            bg=self.bg_color
        ).pack(side=tk.LEFT)
        
        # 消息内容
        if message:
            msg_label = tk.Label(
                item_frame, 
                text=message, 
                font=("Microsoft YaHei UI", 10), 
                fg=text_color, 
                bg=self.bg_color,
                wraplength=400,
                justify=tk.LEFT
            )
            msg_label.pack(fill=tk.X, padx=(20, 0))
        else:
            # 如果没有消息，显示ID
            id_label = tk.Label(
                item_frame, 
                text=f"事件触发: {event_id}", 
                font=("Arial", 9, "italic"), 
                fg="#666666", 
                bg=self.bg_color,
                padx=20
            )
            id_label.pack(fill=tk.X, anchor="w")
            
        # 分割线
        ttk.Separator(self.content_frame, orient='horizontal').pack(fill='x', pady=5)
