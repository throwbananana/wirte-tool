"""
悬浮写作助手 - 对话框模块
包含所有UI对话框类
"""
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog
import os
import copy
from datetime import datetime
from typing import Dict, List, Optional, Any
from PIL import Image, ImageTk

from ..states import AssistantState, STATE_NAMES, STATE_EMOJIS
from ..tools import NameGenerator, NameType, Gender
from ..constants import FOODS, ACHIEVEMENTS
from writer_app.core.icon_manager import IconManager

def get_icon(name, fallback):
    return IconManager().get_icon(name, fallback=fallback)

def get_icon_font(size=12):
    return IconManager().get_font(size=size)



class NameGeneratorDialog(tk.Toplevel):
    """起名生成器对话框"""

    def __init__(self, parent):
        super().__init__(parent)
        self.title("起名助手")
        self.geometry("420x520")
        self.result = None
        self.generated_names = []
        self._setup_ui()
        self.transient(parent)
        self.grab_set()

    def _setup_ui(self):
        # 类型选择
        type_frame = ttk.LabelFrame(self, text="名字类型")
        type_frame.pack(fill=tk.X, padx=10, pady=5)

        self.name_type = tk.StringVar(value="chinese")
        types = [
            ("中文名", "chinese"),
            ("英文名", "english"),
            ("日式名", "japanese"),
            ("奇幻/武侠", "fantasy")
        ]
        for text, value in types:
            ttk.Radiobutton(type_frame, text=text, variable=self.name_type,
                            value=value).pack(side=tk.LEFT, padx=10, pady=5)

        # 性别选择
        gender_frame = ttk.LabelFrame(self, text="性别倾向")
        gender_frame.pack(fill=tk.X, padx=10, pady=5)

        self.gender = tk.StringVar(value="any")
        for text, value in [("不限", "any"), ("男性", "male"), ("女性", "female")]:
            ttk.Radiobutton(gender_frame, text=text, variable=self.gender,
                            value=value).pack(side=tk.LEFT, padx=10, pady=5)

        # 数量选择
        count_frame = ttk.Frame(self)
        count_frame.pack(fill=tk.X, padx=10, pady=5)
        ttk.Label(count_frame, text="生成数量:").pack(side=tk.LEFT)
        self.count_var = tk.IntVar(value=5)
        ttk.Spinbox(count_frame, from_=1, to=20, textvariable=self.count_var,
                    width=5).pack(side=tk.LEFT, padx=5)

        # 生成按钮
        btn_frame = ttk.Frame(self)
        btn_frame.pack(fill=tk.X, padx=10, pady=5)
        ttk.Button(btn_frame, text=f"{get_icon('sparkle', '✨')} 生成名字", command=self._generate).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text=f"{get_icon('arrow_sync', '🔄')} 再来一次", command=self._generate).pack(side=tk.LEFT, padx=5)

        # 结果显示
        result_frame = ttk.LabelFrame(self, text="生成结果")
        result_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        # 使用Listbox带滚动条
        list_frame = ttk.Frame(result_frame)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        self.result_list = tk.Listbox(list_frame, font=("Microsoft YaHei", 11),
                                       selectmode=tk.EXTENDED)
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL,
                                   command=self.result_list.yview)
        self.result_list.configure(yscrollcommand=scrollbar.set)

        self.result_list.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # 底部按钮
        btn_frame = ttk.Frame(self)
        btn_frame.pack(fill=tk.X, padx=10, pady=10)
        ttk.Button(btn_frame, text=f"{get_icon('copy', '📋')} 复制选中", command=self._copy_selected).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text=f"{get_icon('copy_add', '📋')} 复制全部", command=self._copy_all).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text=f"{get_icon('checkmark_circle', '✨')} 使用并关闭", command=self._use_and_close).pack(side=tk.RIGHT, padx=5)

    def _generate(self):
        """生成名字"""
        name_type_str = self.name_type.get()
        gender_str = self.gender.get()
        count = self.count_var.get()

        # 转换类型
        name_type = {
            "chinese": NameType.CHINESE,
            "english": NameType.ENGLISH,
            "japanese": NameType.JAPANESE,
            "fantasy": NameType.FANTASY,
        }.get(name_type_str, NameType.CHINESE)

        gender = {
            "male": Gender.MALE,
            "female": Gender.FEMALE,
            "any": Gender.ANY,
        }.get(gender_str, Gender.ANY)

        self.generated_names = NameGenerator.generate(name_type, gender, count)

        self.result_list.delete(0, tk.END)
        for name in self.generated_names:
            self.result_list.insert(tk.END, name)

    def _copy_selected(self):
        """复制选中的名字"""
        selection = self.result_list.curselection()
        if selection:
            names = [self.result_list.get(i) for i in selection]
            self.clipboard_clear()
            self.clipboard_append("\n".join(names))

    def _copy_all(self):
        """复制全部名字"""
        if self.generated_names:
            self.clipboard_clear()
            self.clipboard_append("\n".join(self.generated_names))

    def _use_and_close(self):
        """使用并关闭"""
        self.result = "\n".join(self.generated_names)
        self.destroy()


class TimerDialog(tk.Toplevel):
    """计时器设置对话框"""

    def __init__(self, parent):
        super().__init__(parent)
        self.title("设置计时")
        self.geometry("280x180")
        self.result = None
        self._setup_ui()
        self.transient(parent)
        self.grab_set()

    def _setup_ui(self):
        ttk.Label(self, text="计时时长（分钟）:",
                  font=("Microsoft YaHei", 10)).pack(pady=10)

        self.minutes_var = tk.IntVar(value=25)
        spin = ttk.Spinbox(self, from_=1, to=120, textvariable=self.minutes_var,
                            width=10, font=("Microsoft YaHei", 12))
        spin.pack()

        # 快捷按钮
        quick_frame = ttk.Frame(self)
        quick_frame.pack(pady=15)
        for mins in [5, 15, 25, 45, 60]:
            ttk.Button(quick_frame, text=f"{mins}分", width=5,
                       command=lambda m=mins: self._set_and_start(m)).pack(side=tk.LEFT, padx=3)

        ttk.Button(self, text=f"{get_icon('play', '▶')} 开始计时", command=self._start,
                   style="Accent.TButton").pack(pady=10)

    def _set_and_start(self, mins):
        self.result = mins
        self.destroy()

    def _start(self):
        self.result = self.minutes_var.get()
        self.destroy()


class QuickNoteDialog(tk.Toplevel):
    """快速笔记对话框"""

    def __init__(self, parent, config_manager):
        super().__init__(parent)
        self.title("快速笔记")
        self.geometry("450x350")
        self.config_manager = config_manager
        self._setup_ui()
        self._load_notes()
        self.transient(parent)

    def _setup_ui(self):
        # 工具栏
        toolbar = ttk.Frame(self)
        toolbar.pack(fill=tk.X, padx=10, pady=5)

        ttk.Button(toolbar, text=f"{get_icon('delete', '🗑️')} 清空", command=self._clear).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text=f"{get_icon('copy', '📋')} 复制", command=self._copy).pack(side=tk.LEFT, padx=2)

        # 文本区域
        text_frame = ttk.Frame(self)
        text_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        self.text = tk.Text(text_frame, wrap=tk.WORD, font=("Microsoft YaHei", 10))
        scrollbar = ttk.Scrollbar(text_frame, orient=tk.VERTICAL, command=self.text.yview)
        self.text.configure(yscrollcommand=scrollbar.set)

        self.text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # 底部按钮
        btn_frame = ttk.Frame(self)
        btn_frame.pack(fill=tk.X, padx=10, pady=10)
        ttk.Button(btn_frame, text=f"{get_icon('save', '💾')} 保存", command=self._save).pack(side=tk.RIGHT, padx=5)
        ttk.Button(btn_frame, text="关闭", command=self.destroy).pack(side=tk.RIGHT, padx=5)

    def _load_notes(self):
        notes = self.config_manager.get("quick_notes", "")
        self.text.insert("1.0", notes)

    def _save(self):
        notes = self.text.get("1.0", tk.END).strip()
        self.config_manager.set("quick_notes", notes)
        self.config_manager.save()
        messagebox.showinfo("保存成功", "笔记已保存")

    def _clear(self):
        if messagebox.askyesno("确认", "确定要清空笔记吗："):
            self.text.delete("1.0", tk.END)

    def _copy(self):
        content = self.text.get("1.0", tk.END).strip()
        if content:
            self.clipboard_clear()
            self.clipboard_append(content)


class CharacterCardDialog(tk.Toplevel):
    """角色卡生成对话框"""

    def __init__(self, parent):
        super().__init__(parent)
        self.title("角色卡生成器")
        self.geometry("500x600")
        self.result = None
        self._setup_ui()
        self.transient(parent)
        self.grab_set()

    def _setup_ui(self):
        # 模板选择
        template_frame = ttk.LabelFrame(self, text="角色模板")
        template_frame.pack(fill=tk.X, padx=10, pady=5)

        self.template_var = tk.StringVar(value="protagonist")
        templates = [
            ("主角", "protagonist"),
            ("反派", "antagonist"),
            ("配角", "supporting"),
            ("奇幻", "fantasy"),
        ]
        for text, value in templates:
            ttk.Radiobutton(template_frame, text=text, variable=self.template_var,
                            value=value).pack(side=tk.LEFT, padx=10, pady=5)

        # 生成选项
        options_frame = ttk.Frame(self)
        options_frame.pack(fill=tk.X, padx=10, pady=5)

        ttk.Label(options_frame, text="名字类型:").pack(side=tk.LEFT)
        self.name_type_var = tk.StringVar(value="chinese")
        ttk.Combobox(options_frame, textvariable=self.name_type_var,
                     values=["chinese", "english", "japanese", "fantasy"],
                     width=10, state="readonly").pack(side=tk.LEFT, padx=5)

        ttk.Label(options_frame, text="性别:").pack(side=tk.LEFT, padx=(10, 0))
        self.gender_var = tk.StringVar(value="any")
        ttk.Combobox(options_frame, textvariable=self.gender_var,
                     values=["any", "male", "female"],
                     width=8, state="readonly").pack(side=tk.LEFT, padx=5)

        ttk.Button(options_frame, text=f"{get_icon('games', '🎲')} 随机生成", command=self._generate).pack(side=tk.RIGHT, padx=5)

        # 角色卡内容
        card_frame = ttk.LabelFrame(self, text="角色信息")
        card_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        # 创建输入字段
        self.fields = {}
        field_names = ["姓名", "年龄", "性别", "外貌特征", "性格", "特长", "背景", "目标"]

        for i, field in enumerate(field_names):
            row = ttk.Frame(card_frame)
            row.pack(fill=tk.X, padx=5, pady=2)

            ttk.Label(row, text=f"{field}:", width=10, anchor="e").pack(side=tk.LEFT)

            if field in ["背景", "目标"]:
                # 多行文本
                text = tk.Text(row, height=3, width=40, font=("Microsoft YaHei", 9))
                text.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
                self.fields[field] = text
            else:
                # 单行输入
                entry = ttk.Entry(row, width=40)
                entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
                self.fields[field] = entry

        # 底部按钮
        btn_frame = ttk.Frame(self)
        btn_frame.pack(fill=tk.X, padx=10, pady=10)
        ttk.Button(btn_frame, text=f"{get_icon('copy', '📋')} 复制", command=self._copy).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text=f"{get_icon('delete', '🗑️')} 清空", command=self._clear).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text=f"{get_icon('checkmark_circle', '✨')} 使用并关闭", command=self._use).pack(side=tk.RIGHT, padx=5)

    def _generate(self):
        """随机生成"""
        from ..tools import CharacterCardGenerator

        name_type = {
            "chinese": NameType.CHINESE,
            "english": NameType.ENGLISH,
            "japanese": NameType.JAPANESE,
            "fantasy": NameType.FANTASY,
        }.get(self.name_type_var.get(), NameType.CHINESE)

        gender = {
            "male": Gender.MALE,
            "female": Gender.FEMALE,
            "any": Gender.ANY,
        }.get(self.gender_var.get(), Gender.ANY)

        card = CharacterCardGenerator.generate_basic(name_type, gender)

        # 填充字段
        for field, widget in self.fields.items():
            value = card.get(field, "")
            if isinstance(widget, tk.Text):
                widget.delete("1.0", tk.END)
                widget.insert("1.0", value)
            else:
                widget.delete(0, tk.END)
                widget.insert(0, value)

    def _get_card_text(self) -> str:
        """获取角色卡文本"""
        lines = ["【角色卡】"]
        for field, widget in self.fields.items():
            if isinstance(widget, tk.Text):
                value = widget.get("1.0", tk.END).strip()
            else:
                value = widget.get().strip()
            if value:
                lines.append(f"{field}: {value}")
        return "\n".join(lines)

    def _copy(self):
        """复制角色卡"""
        text = self._get_card_text()
        self.clipboard_clear()
        self.clipboard_append(text)

    def _clear(self):
        """清空字段"""
        for widget in self.fields.values():
            if isinstance(widget, tk.Text):
                widget.delete("1.0", tk.END)
            else:
                widget.delete(0, tk.END)

    def _use(self):
        """使用并关闭"""
        self.result = self._get_card_text()
        self.destroy()


class SceneGeneratorDialog(tk.Toplevel):
    """场景生成器对话框"""

    def __init__(self, parent):
        super().__init__(parent)
        self.title("场景生成器")
        self.geometry("400x400")
        self.result = None
        self._setup_ui()
        self.transient(parent)
        self.grab_set()

    def _setup_ui(self):
        # 类别选择
        cat_frame = ttk.LabelFrame(self, text="场景类别")
        cat_frame.pack(fill=tk.X, padx=10, pady=5)

        self.category_var = tk.StringVar(value="random")
        categories = [("随机", "random"), ("室内", "indoor"),
                      ("室外", "outdoor"), ("奇幻", "fantasy"), ("科幻", "scifi")]
        for text, value in categories:
            ttk.Radiobutton(cat_frame, text=text, variable=self.category_var,
                            value=value).pack(side=tk.LEFT, padx=8, pady=5)

        # 生成按钮
        ttk.Button(self, text=f"{get_icon('games', '🎲')} 生成场景", command=self._generate).pack(pady=10)

        # 结果显示
        result_frame = ttk.LabelFrame(self, text="场景信息")
        result_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        self.result_text = tk.Text(result_frame, wrap=tk.WORD,
                                    font=("Microsoft YaHei", 10), height=10)
        self.result_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # 底部按钮
        btn_frame = ttk.Frame(self)
        btn_frame.pack(fill=tk.X, padx=10, pady=10)
        ttk.Button(btn_frame, text=f"{get_icon('copy', '📋')} 复制", command=self._copy).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text=f"{get_icon('checkmark_circle', '✨')} 使用并关闭", command=self._use).pack(side=tk.RIGHT, padx=5)

    def _generate(self):
        """生成场景"""
        from ..tools import SceneGenerator

        category = self.category_var.get()
        if category == "random":
            category = None

        scene = SceneGenerator.generate_random(category)

        text = "【场景设定】\n"
        for key, value in scene.items():
            text += f"{key}: {value}\n"

        text += f"\n【场景描述】\n{SceneGenerator.generate_description(scene)}"

        self.result_text.delete("1.0", tk.END)
        self.result_text.insert("1.0", text)

    def _copy(self):
        """复制"""
        text = self.result_text.get("1.0", tk.END).strip()
        if text:
            self.clipboard_clear()
            self.clipboard_append(text)

    def _use(self):
        """使用并关闭"""
        self.result = self.result_text.get("1.0", tk.END).strip()
        self.destroy()


class PromptCardDialog(tk.Toplevel):
    """写作提示卡对话框"""

    def __init__(self, parent, prompt_drawer=None):
        super().__init__(parent)
        self.title("写作提示卡")
        self.geometry("400x350")
        self.prompt_drawer = prompt_drawer
        self.result = None
        self._setup_ui()
        self.transient(parent)
        self.grab_set()

    def _setup_ui(self):
        # 类别选择
        cat_frame = ttk.LabelFrame(self, text="提示类别")
        cat_frame.pack(fill=tk.X, padx=10, pady=5)

        self.category_var = tk.StringVar(value="all")
        categories = [("全部", "all"), ("情节", "plot"), ("人物", "character"),
                      ("场景", "scene"), ("对话", "dialogue")]
        for text, value in categories:
            ttk.Radiobutton(cat_frame, text=text, variable=self.category_var,
                            value=value).pack(side=tk.LEFT, padx=8, pady=5)

        # 抽取按钮
        ttk.Button(self, text=f"{get_icon('board', '🃏')} 抽取提示卡", command=self._draw).pack(pady=10)

        # 结果显示
        result_frame = ttk.LabelFrame(self, text="提示内容")
        result_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        self.result_text = tk.Text(result_frame, wrap=tk.WORD,
                                    font=("Microsoft YaHei", 12), height=5)
        self.result_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # 底部按钮
        btn_frame = ttk.Frame(self)
        btn_frame.pack(fill=tk.X, padx=10, pady=10)
        ttk.Button(btn_frame, text=f"{get_icon('copy', '📋')} 复制", command=self._copy).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text=f"{get_icon('star', '⭐')} 收藏", command=self._favorite).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text=f"{get_icon('checkmark_circle', '✨')} 使用并关闭", command=self._use).pack(side=tk.RIGHT, padx=5)

    def _draw(self):
        """抽取提示卡"""
        import random
        from ..constants import WRITING_PROMPTS

        category = self.category_var.get()
        prompts = WRITING_PROMPTS

        # 简单的类别过滤：实际可以更复杂：
        prompt = random.choice(prompts)

        self.result_text.delete("1.0", tk.END)
        self.result_text.insert("1.0", f"\"{prompt}\"")

    def _copy(self):
        """复制"""
        text = self.result_text.get("1.0", tk.END).strip()
        if text:
            self.clipboard_clear()
            self.clipboard_append(text)

    def _favorite(self):
        """收藏"""
        text = self.result_text.get("1.0", tk.END).strip()
        if text:
            messagebox.showinfo("收藏", "已添加到收藏夹！")

    def _use(self):
        """使用并关闭"""
        self.result = self.result_text.get("1.0", tk.END).strip()
        self.destroy()


class AchievementDialog(tk.Toplevel):
    """成就对话框"""

    def __init__(self, parent, unlocked_achievements: list, all_achievements: dict):
        super().__init__(parent)
        self.title("成就")
        self.geometry("450x500")
        self.unlocked = unlocked_achievements
        self.all_achievements = all_achievements
        self._setup_ui()
        self.transient(parent)
        self.grab_set()

    def _setup_ui(self):
        # 统计信息
        total = len(self.all_achievements)
        unlocked = len(self.unlocked)
        progress = (unlocked / total * 100) if total > 0 else 0

        stats_frame = ttk.Frame(self)
        stats_frame.pack(fill=tk.X, padx=10, pady=10)

        ttk.Label(stats_frame, text=f"{get_icon('trophy', '🏆')} 成就进度: {unlocked}/{total} ({progress:.1f}%)",
                  font=("Microsoft YaHei", 12, "bold")).pack()

        # 进度条
        progress_bar = ttk.Progressbar(stats_frame, length=400, mode='determinate')
        progress_bar['value'] = progress
        progress_bar.pack(pady=5)

        # 成就列表
        list_frame = ttk.LabelFrame(self, text="成就列表")
        list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        # 带滚动条的canvas
        canvas = tk.Canvas(list_frame, highlightthickness=0)
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)

        scrollable_frame.bind("<Configure>",
                               lambda e: canvas.configure(scrollregion=canvas.bbox("all")))

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        # 本地滚轮绑定
        def _bind_mousewheel(event, c=canvas):
            c.bind_all("<MouseWheel>", lambda e: c.yview_scroll(int(-1 * (e.delta / 120)), "units"))

        def _unbind_mousewheel(event, c=canvas):
            c.unbind_all("<MouseWheel>")

        canvas.bind("<Enter>", _bind_mousewheel)
        canvas.bind("<Leave>", _unbind_mousewheel)

        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # 渲染成就
        for ach_id, ach_data in self.all_achievements.items():
            is_unlocked = ach_id in self.unlocked
            self._create_achievement_card(scrollable_frame, ach_id, ach_data, is_unlocked)

        # 关闭按钮
        ttk.Button(self, text="关闭", command=self.destroy).pack(pady=10)

    def _create_achievement_card(self, parent, ach_id, ach_data, is_unlocked):
        """创建成就卡片"""
        card = ttk.Frame(parent, relief="solid", borderwidth=1)
        card.pack(fill=tk.X, padx=5, pady=3)

        # 图标和名称
        icon = ach_data.get("icon", get_icon("trophy", "🏆")) if is_unlocked else get_icon("lock_closed", "🔒")
        name = ach_data.get("name", ach_id)
        desc = ach_data.get("description", "")
        xp = ach_data.get("xp", 0)

        # 状态颜色
        fg_color = "#4CAF50" if is_unlocked else "#9E9E9E"

        row = ttk.Frame(card)
        row.pack(fill=tk.X, padx=5, pady=5)

        ttk.Label(row, text=icon, font=get_icon_font(16)).pack(side=tk.LEFT)
        info_frame = ttk.Frame(row)
        info_frame.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=10)

        name_label = ttk.Label(info_frame, text=name, font=("Microsoft YaHei", 10, "bold"))
        name_label.pack(anchor=tk.W)

        desc_label = ttk.Label(info_frame, text=desc, font=("Microsoft YaHei", 8))
        desc_label.pack(anchor=tk.W)

        if is_unlocked:
            ttk.Label(row, text=f"+{xp} XP", font=("Microsoft YaHei", 9),
                      foreground="#FFD700").pack(side=tk.RIGHT)



class CollectionDialog(tk.Toplevel):
    """收藏品对话框"""

    def __init__(self, parent, collection: list):
        super().__init__(parent)
        self.title("收藏品")
        self.geometry("400x450")
        self.collection = collection
        self._setup_ui()
        self.transient(parent)
        self.grab_set()

    def _setup_ui(self):
        # 统计
        ttk.Label(self, text=f"{get_icon('box', '📦')} 收藏品: {len(self.collection)} 件",
                  font=("Microsoft YaHei", 12, "bold")).pack(pady=10)

        # 收藏列表
        list_frame = ttk.LabelFrame(self, text="收藏列表")
        list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        # 带滚动条的列表
        self.listbox = tk.Listbox(list_frame, font=("Microsoft YaHei", 10))
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.listbox.yview)
        self.listbox.configure(yscrollcommand=scrollbar.set)

        self.listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y, pady=5)

        # 填充数据
        if self.collection:
            for item in self.collection:
                if isinstance(item, dict):
                    name = item.get("name", str(item))
                else:
                    name = str(item)
                self.listbox.insert(tk.END, f"📦 {name}")
        else:
            self.listbox.insert(tk.END, "还没有收藏品哦~")

        # 关闭按钮
        ttk.Button(self, text="关闭", command=self.destroy).pack(pady=10)


class FeedDialog(tk.Toplevel):
    """喂食对话框"""

    def __init__(self, parent, foods: list):
        super().__init__(parent)
        self.title("喂食")
        self.geometry("350x400")
        self.foods = foods
        self.result = None
        self._setup_ui()
        self.transient(parent)
        self.grab_set()

    def _setup_ui(self):
        ttk.Label(self, text=f"{get_icon('food_cookie', '🍪')} 选择食物",
                  font=("Microsoft YaHei", 12, "bold")).pack(pady=10)

        # 食物列表
        list_frame = ttk.Frame(self)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        canvas = tk.Canvas(list_frame, highlightthickness=0)
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)

        scrollable_frame.bind("<Configure>",
                               lambda e: canvas.configure(scrollregion=canvas.bbox("all")))

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        # 本地滚轮绑定
        def _bind_mousewheel(event, c=canvas):
            c.bind_all("<MouseWheel>", lambda e: c.yview_scroll(int(-1 * (e.delta / 120)), "units"))

        def _unbind_mousewheel(event, c=canvas):
            c.unbind_all("<MouseWheel>")

        canvas.bind("<Enter>", _bind_mousewheel)
        canvas.bind("<Leave>", _unbind_mousewheel)

        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # 渲染食物按钮
        for food in self.foods:
            self._create_food_button(scrollable_frame, food)

        # 取消按钮
        ttk.Button(self, text="取消", command=self.destroy).pack(pady=10)

    def _create_food_button(self, parent, food):
        """创建食物按钮"""
        btn_frame = ttk.Frame(parent)
        btn_frame.pack(fill=tk.X, padx=5, pady=3)

        emoji = food.get("emoji", get_icon("food_cookie", "🍪"))
        name = food.get("name", "食物")
        rarity = food.get("rarity", "普通")
        mood_boost = food.get("mood_boost", 0)

        # 稀有度颜色
        rarity_colors = {
            "普通": "#9E9E9E",
            "稀有": "#2196F3",
            "传说": "#FFD700"
        }
        color = rarity_colors.get(rarity, "#9E9E9E")

        btn = tk.Button(
            btn_frame,
            text=f"  {name} ({rarity})", # Text part
            font=("Microsoft YaHei", 10),
            bg="#3D3D3D",
            fg="white",
            activebackground="#555555",
            relief=tk.FLAT,
            cursor="hand2",
            anchor="w",
            command=lambda f=food: self._select(f)
        )
        # Use a label for the icon to support font
        icon_lbl = tk.Label(btn, text=emoji, font=get_icon_font(12), bg="#3D3D3D", fg=color)
        icon_lbl.pack(side=tk.LEFT, padx=5)
        btn.pack(fill=tk.X)


        # 效果提示
        effect_text = f"心情+{mood_boost}" if mood_boost > 0 else ""
        if effect_text:
            ttk.Label(btn_frame, text=effect_text,
                      font=("Microsoft YaHei", 8)).pack(anchor=tk.E)

    def _select(self, food):
        """选择食物"""
        self.result = food
        self.destroy()


class AffectionDialog(tk.Toplevel):
    """陪伴详情对话框"""

    def __init__(self, parent, pet_system):
        super().__init__(parent)
        from ..constants import ASSISTANT_NAME
        self.title(f"与 {ASSISTANT_NAME} 的羁绊")
        self.geometry("350x400")
        self.pet_system = pet_system
        self._setup_ui()
        self.transient(parent)
        self.grab_set()

    def _setup_ui(self):
        data = self.pet_system.data
        from ..constants import ASSISTANT_NAME

        # 头像区域：简化）
        ttk.Label(self, text="❤️", font=("Segoe UI Emoji", 48)).pack(pady=10)

        # 等级和经验
        level_frame = ttk.LabelFrame(self, text="等级信息")
        level_frame.pack(fill=tk.X, padx=10, pady=5)

        ttk.Label(level_frame, text=f"当前等级: Lv.{data.level}",
                  font=("Microsoft YaHei", 12, "bold")).pack(pady=5)

        # 经验条
        from ..pet_system import PetSystem
        current_xp = data.total_xp
        next_level_xp = PetSystem.LEVEL_XP.get(data.level + 1, 99999)
        prev_level_xp = PetSystem.LEVEL_XP.get(data.level, 0)
        xp_progress = ((current_xp - prev_level_xp) / (next_level_xp - prev_level_xp) * 100) if next_level_xp > prev_level_xp else 100

        ttk.Label(level_frame, text=f"经验值: {current_xp} / {next_level_xp}",
                  font=("Microsoft YaHei", 9)).pack()

        xp_bar = ttk.Progressbar(level_frame, length=300, mode='determinate')
        xp_bar['value'] = min(xp_progress, 100)
        xp_bar.pack(pady=5)

        # 陪伴状态
        relation_frame = ttk.LabelFrame(self, text="陪伴状态")
        relation_frame.pack(fill=tk.X, padx=10, pady=5)

        relation_text = self.pet_system.get_affection_level()
        ttk.Label(relation_frame, text=relation_text,
                  font=("Microsoft YaHei", 12, "bold")).pack(pady=5)

        # 心情状态
        mood_frame = ttk.LabelFrame(self, text="心情状态")
        mood_frame.pack(fill=tk.X, padx=10, pady=5)

        mood_emoji = self.pet_system.get_mood_emoji()
        mood_name = self.pet_system.get_mood_name()
        ttk.Label(mood_frame, text=f"{mood_emoji} {mood_name}",
                  font=("Microsoft YaHei", 12)).pack(pady=5)

        # 统计信息
        stats_frame = ttk.LabelFrame(self, text="统计")
        stats_frame.pack(fill=tk.X, padx=10, pady=5)

        ttk.Label(stats_frame, text=f"总对话次数: {data.total_chats}",
                  font=("Microsoft YaHei", 9)).pack(anchor=tk.W, padx=5)
        ttk.Label(stats_frame, text=f"解锁成就: {len(data.unlocked_achievements)}",
                  font=("Microsoft YaHei", 9)).pack(anchor=tk.W, padx=5)
        ttk.Label(stats_frame, text=f"相识时间: {data.created_at[:10] if data.created_at else '未知'}",
                  font=("Microsoft YaHei", 9)).pack(anchor=tk.W, padx=5)

        # 关闭按钮
        ttk.Button(self, text="关闭", command=self.destroy).pack(pady=10)


class GameDialog(tk.Toplevel):
    """小游戏选择对话框"""

    def __init__(self, parent, game_manager):
        super().__init__(parent)
        from ..constants import ASSISTANT_NAME
        self.title(f"与 {ASSISTANT_NAME} 游玩")
        self.geometry("300x250")
        self.game_manager = game_manager
        self.result = None
        self._setup_ui()
        self.transient(parent)
        self.grab_set()

    def _setup_ui(self):
        ttk.Label(self, text="选择要玩的游戏:",
                  font=("Microsoft YaHei", 11, "bold")).pack(pady=10)

        games = self.game_manager.get_available_games()
        for name, game_id in games:
            btn = ttk.Button(self, text=f"{get_icon('games', '🎮')} {name}",
                             command=lambda gid=game_id: self._select(gid))
            btn.pack(fill=tk.X, padx=20, pady=3)

        ttk.Button(self, text="取消", command=self.destroy).pack(pady=10)

    def _select(self, game_id):
        self.result = game_id
        self.destroy()


class WardrobeDialog(tk.Toplevel):
    """衣柜对话框 - 管理立绘套装"""

    # 状态分类
    STATE_CATEGORIES = {
        "基础状态": [
            ("idle", "待机"), ("thinking", "思考"),
            ("success", "成功"), ("error", "错误")
        ],
        "情绪表情": [
            ("happy", "开心"), ("sad", "难过"), ("excited", "兴奋"),
            ("shy", "害羞"), ("angry", "生气"), ("surprised", "惊讶"),
            ("curious", "好奇"), ("love", "喜爱"), ("worried", "担心")
        ],
        "动作状态": [
            ("eating", "进食"), ("sleeping", "睡眠"), ("greeting", "问候"),
            ("cheering", "鼓励"), ("reading", "阅读"), ("writing", "写作"),
            ("celebrating", "庆祝"), ("playing", "玩耍")
        ],
        "默契专属": [
            ("blush", "脸红"), ("trust", "信任"),
            ("devoted", "专注")
        ],
        "时间特殊": [
            ("morning", "早安"), ("night", "晚安"), ("midnight", "深夜")
        ],
        "四季服装": [
            ("spring", "春装"), ("summer", "夏装"),
            ("autumn", "秋装"), ("winter", "冬装")
        ],
        "中国节日": [
            ("spring_festival", "春节"), ("lantern", "元宵"),
            ("qingming", "清明"), ("dragon_boat", "端午"),
            ("qixi", "七夕"), ("mid_autumn", "中秋"),
            ("double_ninth", "重阳")
        ],
        "西方节日": [
            ("new_year", "元旦"), ("valentines", "情人节"),
            ("easter", "复活节"), ("halloween", "万圣节"),
            ("thanksgiving", "感恩节"), ("christmas", "圣诞节")
        ],
        "服装-日常": [
            ("sportswear", "运动服"), ("casual", "休闲服"),
            ("formal", "正装"), ("pajamas", "睡衣"), ("uniform", "制服")
        ],
        "服装-特殊": [
            ("maid", "女仆装"), ("swimsuit", "泳装"),
            ("kimono", "和服"), ("cheongsam", "旗袍"),
            ("gothic", "哥特风"), ("lolita", "洛丽塔"),
            ("fantasy", "幻想风"), ("knight", "骑士装"),
            ("witch", "魔女装"), ("idol", "偶像装")
        ],
        "场景/活动": [
            ("cooking", "做饭"), ("gaming", "打游戏"),
            ("music", "音乐"), ("shopping", "购物"),
            ("travel", "旅行"), ("beach", "海滩"),
            ("mountain", "登山"), ("cafe", "咖啡厅"),
            ("school", "学校"), ("office", "办公室")
        ]
    }

    def __init__(self, parent, skins, current_skin, state_categories=None):
        super().__init__(parent)
        from ..constants import ASSISTANT_NAME
        self.title(f"{ASSISTANT_NAME} 的衣橱")
        self.geometry("750x580")
        self.skins = copy.deepcopy(skins)
        self.current_skin = current_skin
        self.current_editing = None
        self.result = None
        # 如果传入了自定义的状态分类，使用它
        if state_categories:
            self.STATE_CATEGORIES = state_categories
        self._setup_ui()
        self.transient(parent)
        self.grab_set()

    def _setup_ui(self):
        # 主分割布局
        main_paned = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        main_paned.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # 左侧：皮肤列表
        left_frame = ttk.Frame(main_paned, width=160)
        main_paned.add(left_frame, weight=1)

        ttk.Label(left_frame, text="套装列表",
                  font=("Microsoft YaHei", 10, "bold")).pack(pady=5)

        list_frame = ttk.Frame(left_frame)
        list_frame.pack(fill=tk.BOTH, expand=True)

        self.listbox = tk.Listbox(list_frame, width=18, font=("Microsoft YaHei", 9))
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.listbox.yview)
        self.listbox.configure(yscrollcommand=scrollbar.set)

        self.listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.listbox.bind("<<ListboxSelect>>", self._on_select)

        # 皮肤操作按钮
        btn_frame = ttk.Frame(left_frame)
        btn_frame.pack(fill=tk.X, pady=5)
        ttk.Button(btn_frame, text=f"{get_icon('add', '+')} 新建", command=self._add_skin, width=6).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text=f"{get_icon('copy', '📋')} 复制", command=self._copy_skin, width=5).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text=f"{get_icon('delete', '-')} 删除", command=self._del_skin, width=6).pack(side=tk.LEFT, padx=2)

        # 右侧：立绘配置
        right_frame = ttk.Frame(main_paned)
        main_paned.add(right_frame, weight=3)

        self.skin_name_label = ttk.Label(right_frame, text="请选择套装",
                                          font=("Microsoft YaHei", 11, "bold"))
        self.skin_name_label.pack(pady=5)

        # 选项卡
        self.notebook = ttk.Notebook(right_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        self.vars = {}
        self._create_state_tabs()

        # 底部按钮
        bot_frame = ttk.Frame(self)
        bot_frame.pack(fill=tk.X, pady=10)

        ttk.Button(bot_frame, text=f"{get_icon('folder_open', '📂')} 批量导入", command=self._batch_import).pack(side=tk.LEFT, padx=10)
        ttk.Button(bot_frame, text=f"{get_icon('delete', '🗑️')} 清空当前", command=self._clear_current).pack(side=tk.LEFT, padx=5)
        ttk.Button(bot_frame, text=f"{get_icon('t_shirt', '👕')} 穿戴并保存", command=self._save_and_equip).pack(side=tk.RIGHT, padx=10)
        ttk.Button(bot_frame, text=f"{get_icon('save', '💾')} 仅保存", command=self._save_only).pack(side=tk.RIGHT, padx=5)

        self._refresh_list()

    def _create_state_tabs(self):
        """创建状态配置选项卡"""
        for category, states in self.STATE_CATEGORIES.items():
            tab_frame = ttk.Frame(self.notebook)
            self.notebook.add(tab_frame, text=category)

            # 创建Canvas和滚动条
            canvas = tk.Canvas(tab_frame, highlightthickness=0)
            scrollbar = ttk.Scrollbar(tab_frame, orient=tk.VERTICAL, command=canvas.yview)
            scrollable_frame = ttk.Frame(canvas)

            scrollable_frame.bind(
                "<Configure>",
                lambda e, c=canvas: c.configure(scrollregion=c.bbox("all"))
            )

            canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
            canvas.configure(yscrollcommand=scrollbar.set)

            # 局部滚轮绑定：修复全局滚轮问题）
            def _bind_mousewheel(event, canvas=canvas):
                canvas.bind_all("<MouseWheel>",
                                lambda e: canvas.yview_scroll(int(-1 * (e.delta / 120)), "units"))

            def _unbind_mousewheel(event, canvas=canvas):
                canvas.unbind_all("<MouseWheel>")

            canvas.bind("<Enter>", _bind_mousewheel)
            canvas.bind("<Leave>", _unbind_mousewheel)

            canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

            # 创建状态配置行
            for state_key, state_name in states:
                row = ttk.Frame(scrollable_frame)
                row.pack(fill=tk.X, pady=3, padx=5)

                ttk.Label(row, text=f"{state_name}:", width=12, anchor="w").pack(side=tk.LEFT)

                var = tk.StringVar()
                self.vars[state_key] = var

                entry = ttk.Entry(row, textvariable=var, width=35)
                entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=2)

                ttk.Button(row, text="...", width=3,
                           command=lambda v=var: self._pick_image(v)).pack(side=tk.LEFT, padx=2)
                
                # Eye icon for preview
                eye_btn = tk.Label(row, text=get_icon("eye", "🌸憗"), font=get_icon_font(10), bg=row["bg"], cursor="hand2")
                eye_btn.pack(side=tk.LEFT, padx=2)
                eye_btn.bind("<Button-1>", lambda e, v=var: self._preview_image(v.get()))
                
                # Dismiss icon for clear
                del_btn = tk.Label(row, text=get_icon("dismiss", "脳"), font=get_icon_font(10), bg=row["bg"], cursor="hand2")
                del_btn.pack(side=tk.LEFT, padx=2)
                del_btn.bind("<Button-1>", lambda e, v=var: v.set(""))

    def _refresh_list(self):
        """刷新皮肤列表"""
        self.listbox.delete(0, tk.END)
        for name in self.skins:
            display = f"✨ {name}" if name == self.current_skin else f"  {name}"
            self.listbox.insert(tk.END, display)
            if name == self.current_skin:
                self.listbox.itemconfig(tk.END, {'bg': '#E3F2FD'})

    def _on_select(self, event):
        """选择鐨鑲"""
        sel = self.listbox.curselection()
        if not sel:
            return

        self._save_current_editing()

        name = self.listbox.get(sel[0]).strip()
        if name.startswith("✨"):
            name = name[2:]

        self.current_editing = name
        self.skin_name_label.configure(text=f"编辑套装: {name}")

        data = self.skins.get(name, {})
        for state_key, var in self.vars.items():
            var.set(data.get(state_key, ""))

    def _save_current_editing(self):
        """保存当前编辑"""
        if self.current_editing and self.current_editing in self.skins:
            for state_key, var in self.vars.items():
                self.skins[self.current_editing][state_key] = var.get()

    def _pick_image(self, var):
        """选择图片"""
        path = filedialog.askopenfilename(
            title="选择立绘",
            filetypes=[("图片文件", "*.png;*.jpg;*.jpeg;*.gif;*.webp")]
        )
        if path:
            var.set(path)

    def _preview_image(self, path):
        """预览图片"""
        if not path or not os.path.exists(path):
            messagebox.showinfo("预览", "未设置图片或文件不存在")
            return

        try:
            preview = tk.Toplevel(self)
            preview.title("立绘预览")

            img = Image.open(path)
            max_size = 400
            if img.width > max_size or img.height > max_size:
                ratio = min(max_size / img.width, max_size / img.height)
                new_size = (int(img.width * ratio), int(img.height * ratio))
                img = img.resize(new_size, Image.Resampling.LANCZOS)

            photo = ImageTk.PhotoImage(img)
            label = ttk.Label(preview, image=photo)
            label.image = photo
            label.pack(padx=10, pady=10)

            ttk.Label(preview, text=f"尺寸: {img.width}x{img.height}").pack()
            ttk.Button(preview, text="关闭", command=preview.destroy).pack(pady=5)
        except Exception as e:
            messagebox.showerror("预览失败", str(e))

    def _batch_import(self):
        """批量导入"""
        folder = filedialog.askdirectory(title="选择立绘文件夹")
        if not folder or not self.current_editing:
            return

        imported = 0
        for state_key in self.vars:
            for ext in ['.png', '.jpg', '.gif', '.webp']:
                candidate = os.path.join(folder, f"{state_key}{ext}")
                if os.path.exists(candidate):
                    self.vars[state_key].set(candidate)
                    self.skins[self.current_editing][state_key] = candidate
                    imported += 1
                    break

        messagebox.showinfo("批量导入", f"成功导入 {imported} 个立绘")

    def _clear_current(self):
        """清空当前套装"""
        if not self.current_editing:
            return
        if messagebox.askyesno("确认", f"确定要清空套装 '{self.current_editing}' 的所有立绘吗："):
            for var in self.vars.values():
                var.set("")

    def _add_skin(self):
        """新建套装"""
        name = simpledialog.askstring("新建套装", "请输入套装名称:", parent=self)
        if name and name.strip():
            name = name.strip()
            if name in self.skins:
                messagebox.showwarning("警告", "套装名称已存在")
                return
            self.skins[name] = {k: "" for k in self.vars}
            self._refresh_list()

    def _copy_skin(self):
        """复制套装"""
        if not self.current_editing:
            return
        new_name = simpledialog.askstring("复制套装", "新套装名称:",
                                           initialvalue=f"{self.current_editing}_副本", parent=self)
        if new_name and new_name.strip():
            new_name = new_name.strip()
            if new_name in self.skins:
                messagebox.showwarning("警告", "套装名称已存在")
                return
            self.skins[new_name] = copy.deepcopy(self.skins[self.current_editing])
            self._refresh_list()

    def _del_skin(self):
        """删除套装"""
        sel = self.listbox.curselection()
        if not sel:
            return

        name = self.listbox.get(sel[0]).strip()
        if name.startswith("✨"):
            name = name[2:]

        if name == "Default":
            messagebox.showwarning("警告", "无法删除默认套装")
            return

        if messagebox.askyesno("确认删除", f"确定要删除套装 '{name}' 吗？"):
            del self.skins[name]
            if self.current_editing == name:
                self.current_editing = None
                self.skin_name_label.configure(text="请选择套装")
            self._refresh_list()

    def _save_only(self):
        """仅保存"""
        self._save_current_editing()
        self.result = {"skins": self.skins, "current": self.current_skin}
        self.destroy()

    def _save_and_equip(self):
        """保存并穿戴"""
        self._save_current_editing()
        target = self.current_editing if self.current_editing else self.current_skin
        self.result = {"skins": self.skins, "current": target}
        self.destroy()


class AssistantSettingsDialog(tk.Toplevel):
    """助手设置对话框"""

    def __init__(self, parent, config_manager):
        super().__init__(parent)
        from ..constants import ASSISTANT_NAME
        self.title(f"{ASSISTANT_NAME} 设置")
        self.geometry("350x550")
        self.config_manager = config_manager
        self.result = None
        self._photos_updated = False
        self._setup_ui()
        self.transient(parent)
        self.grab_set()

    def _setup_ui(self):
        # 闲聊设置
        p1 = ttk.LabelFrame(self, text="闲聊设置")
        p1.pack(fill=tk.X, padx=10, pady=10)

        self.v_enable = tk.BooleanVar(value=self.config_manager.get("enable_idle_chat", False))
        ttk.Checkbutton(p1, text="启用闲聊（空闲时主动发起对话）：", variable=self.v_enable).pack(anchor=tk.W, padx=5, pady=2)

        f1 = ttk.Frame(p1)
        f1.pack(fill=tk.X, pady=5, padx=5)
        ttk.Label(f1, text="闲聊间隔(分钟):").pack(side=tk.LEFT)
        self.v_int = tk.StringVar(value=str(self.config_manager.get("idle_interval", 10)))
        ttk.Entry(f1, textvariable=self.v_int, width=5).pack(side=tk.LEFT, padx=5)

        # 外观设置
        p2 = ttk.LabelFrame(self, text="外观设置")
        p2.pack(fill=tk.X, padx=10, pady=10)

        self.v_start_expanded = tk.BooleanVar(value=self.config_manager.get("assistant_start_expanded", False))
        ttk.Checkbutton(p2, text="启动时展开对话框", variable=self.v_start_expanded).pack(anchor=tk.W, padx=5, pady=2)

        # 大小滑块
        f_size = ttk.Frame(p2)
        f_size.pack(fill=tk.X, pady=5, padx=5)
        ttk.Label(f_size, text="图像大小:").pack(side=tk.LEFT)
        self.v_size = tk.IntVar(value=int(self.config_manager.get("assistant_avatar_size", 120)))
        scale_size = ttk.Scale(f_size, from_=50, to=300, variable=self.v_size, orient=tk.HORIZONTAL)
        scale_size.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        self.lbl_size = ttk.Label(f_size, text=f"{self.v_size.get()}px")
        self.lbl_size.pack(side=tk.LEFT)
        scale_size.configure(command=lambda v: self.lbl_size.configure(text=f"{int(float(v))}px"))

        # 推理模式窗口尺寸
        f_reverse = ttk.Frame(p2)
        f_reverse.pack(fill=tk.X, pady=5, padx=5)
        ttk.Label(f_reverse, text="推理窗口:").pack(side=tk.LEFT)
        self.v_reverse_w = tk.StringVar(value=str(self.config_manager.get("assistant_reverse_width", 0)))
        self.v_reverse_h = tk.StringVar(value=str(self.config_manager.get("assistant_reverse_height", 0)))
        ttk.Entry(f_reverse, textvariable=self.v_reverse_w, width=6).pack(side=tk.LEFT, padx=(6, 2))
        ttk.Label(f_reverse, text="x").pack(side=tk.LEFT)
        ttk.Entry(f_reverse, textvariable=self.v_reverse_h, width=6).pack(side=tk.LEFT, padx=(2, 6))
        ttk.Label(f_reverse, text="0为自动", foreground="gray").pack(side=tk.LEFT)
        ttk.Button(f_reverse, text="保存当前尺寸", command=self._save_reverse_window_size).pack(side=tk.RIGHT)

        # 透明度滑块
        f2 = ttk.Frame(p2)
        f2.pack(fill=tk.X, pady=5, padx=5)
        ttk.Label(f2, text="透明度:").pack(side=tk.LEFT)
        self.v_alpha = tk.DoubleVar(value=float(self.config_manager.get("assistant_alpha", 0.95)))
        scale = ttk.Scale(f2, from_=0.3, to=1.0, variable=self.v_alpha, orient=tk.HORIZONTAL)
        scale.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        self.lbl_alpha = ttk.Label(f2, text=f"{self.v_alpha.get():.2f}")
        self.lbl_alpha.pack(side=tk.LEFT)
        scale.configure(command=lambda v: self.lbl_alpha.configure(text=f"{float(v):.2f}"))

        # 快捷键设置
        p3 = ttk.LabelFrame(self, text="快捷键")
        p3.pack(fill=tk.X, padx=10, pady=10)

        f3 = ttk.Frame(p3)
        f3.pack(fill=tk.X, pady=5, padx=5)
        ttk.Label(f3, text="唤出/隐藏:").pack(side=tk.LEFT)
        self.v_hotkey = tk.StringVar(value=self.config_manager.get("assistant_hotkey", "Ctrl+Shift+A"))
        ttk.Entry(f3, textvariable=self.v_hotkey, width=15).pack(side=tk.LEFT, padx=5)

        # 剪贴板设置
        p_clip = ttk.LabelFrame(self, text="剪贴板监听")
        p_clip.pack(fill=tk.X, padx=10, pady=10)

        self.v_clipboard = tk.BooleanVar(value=self.config_manager.get("clipboard_notify_enabled", False))
        ttk.Checkbutton(
            p_clip,
            text="启用剪贴板监听：（复制文本时提示快捷操作）",
            variable=self.v_clipboard
        ).pack(anchor=tk.W, padx=5, pady=2)

        ttk.Label(
            p_clip,
            text="启用后：（复制文本时可快速进行润色、扩写等操作）",
            foreground="gray"
        ).pack(anchor=tk.W, padx=5, pady=2)

        # 数据管理
        p4 = ttk.LabelFrame(self, text="数据管理")
        p4.pack(fill=tk.X, padx=10, pady=10)
        photo_count = len(self.config_manager.get("assistant_photos", []))
        self.photo_count_var = tk.StringVar(value=f"相册照片: {photo_count} 张")
        ttk.Label(p4, textvariable=self.photo_count_var, foreground="gray").pack(anchor=tk.W, padx=5, pady=2)
        ttk.Button(p4, text=f"{get_icon('arrow_download', '📥')} 导入照片", command=self._import_photos).pack(anchor=tk.W, padx=5, pady=2)
        ttk.Button(p4, text=f"{get_icon('delete', '🗑️')} 重置养成数据", command=self._reset_pet_data).pack(anchor=tk.W, padx=5, pady=5)
        ttk.Button(p4, text=f"{get_icon('arrow_upload', '📤')} 导出对话历史", command=self._export_history).pack(anchor=tk.W, padx=5, pady=2)

        # 底部按钮
        btn_frame = ttk.Frame(self)
        btn_frame.pack(fill=tk.X, pady=10, padx=10)
        ttk.Button(btn_frame, text="取消", command=self.destroy).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text=f"{get_icon('checkmark_circle', '✨')} 确定", command=self._save).pack(side=tk.RIGHT, padx=5)

    def _reset_pet_data(self):
        """重置养成数据"""
        if messagebox.askyesno("确认", "确定要重置所有养成数据吗？\n：（陪伴记录、成就、收藏都将清空）"):
            self.config_manager.set("pet_system", {})
            self.config_manager.save()
            messagebox.showinfo("完成", "养成数据已重置")

    def _export_history(self):
        """导出对话历史"""
        # TODO: 完炵幇导出功能
        messagebox.showinfo("导出", "对话历史导出功能张可见戜腑...")

    def _import_photos(self):
        """从本地导入照片到相册"""
        file_paths = filedialog.askopenfilenames(
            title="选择照片",
            filetypes=[
                ("图片文件", "*.png *.jpg *.jpeg *.webp *.gif"),
                ("所有文件", "*.*"),
            ],
        )
        if not file_paths:
            return

        photos = list(self.config_manager.get("assistant_photos", []))
        existing_paths = {p.get("path") for p in photos if p.get("path")}

        added = 0
        for idx, photo_path in enumerate(file_paths):
            if not photo_path or photo_path in existing_paths:
                continue
            name = os.path.splitext(os.path.basename(photo_path))[0]
            photos.append({
                "id": f"{datetime.now().timestamp()}_{idx}",
                "state": "custom",
                "state_name": "自定义",
                "timestamp": datetime.now().isoformat(),
                "path": photo_path,
                "caption": name,
                "source": "import",
            })
            added += 1

        if added:
            self.config_manager.set("assistant_photos", photos)
            self.config_manager.save()
            self._photos_updated = True
            if hasattr(self, "photo_count_var"):
                self.photo_count_var.set(f"相册照片: {len(photos)} 张")
            messagebox.showinfo("导入完成", f"已导入 {added} 张照片")
        else:
            messagebox.showinfo("提示", "未发现可导入的照片（可能已存在）：")

    def _save(self):
        """保存设置"""
        try:
            interval = int(self.v_int.get())
        except (ValueError, TypeError):
            interval = 10
        try:
            reverse_width = int(self.v_reverse_w.get())
        except (ValueError, TypeError):
            reverse_width = 0
        try:
            reverse_height = int(self.v_reverse_h.get())
        except (ValueError, TypeError):
            reverse_height = 0

        self.result = {
            "enable_idle_chat": self.v_enable.get(),
            "idle_interval": interval,
            "alpha": self.v_alpha.get(),
            "start_expanded": self.v_start_expanded.get(),
            "avatar_size": self.v_size.get(),
            "reverse_width": reverse_width,
            "reverse_height": reverse_height,
            "hotkey": self.v_hotkey.get(),
            "clipboard_notify_enabled": self.v_clipboard.get(),
            "photos_updated": self._photos_updated,
        }
        self.destroy()

    def _save_reverse_window_size(self):
        """保存当前窗口尺寸为推理默认值"""
        parent = self.master
        if not parent or not hasattr(parent, "_save_reverse_window_size"):
            messagebox.showinfo("提示", "当前无法获取助手窗口尺寸。")
            return
        parent._save_reverse_window_size()
        try:
            width = int(self.config_manager.get("assistant_reverse_width", 0))
            height = int(self.config_manager.get("assistant_reverse_height", 0))
        except Exception:
            return
        if width > 0:
            self.v_reverse_w.set(str(width))
        if height > 0:
            self.v_reverse_h.set(str(height))


class AlbumDialog(tk.Toplevel):
    """相册对话框"""

    def __init__(self, parent, photos, config_manager, state_emojis=None):
        super().__init__(parent)
        from ..constants import ASSISTANT_NAME
        self.title(f"{ASSISTANT_NAME} 的相册")
        self.geometry("820x620")
        self.photos = copy.deepcopy(photos)
        self.config_manager = config_manager
        self.state_emojis = state_emojis or STATE_EMOJIS
        self.result = None
        self.current_page = 0
        self.photos_per_page = 12
        self.filtered_photos = self.photos
        self._setup_ui()
        self._load_page()
        self.transient(parent)
        self.grab_set()

    def _setup_ui(self):
        # 顶部统计栏
        top_frame = ttk.Frame(self)
        top_frame.pack(fill=tk.X, padx=10, pady=5)

        self.stats_label = ttk.Label(
            top_frame,
            text=f"共 {len(self.photos)} 张照片",
            font=("Microsoft YaHei", 11, "bold")
        )
        self.stats_label.pack(side=tk.LEFT)

        # 筛选
        filter_frame = ttk.Frame(top_frame)
        filter_frame.pack(side=tk.RIGHT)

        ttk.Label(filter_frame, text="筛选:").pack(side=tk.LEFT)
        self.filter_var = tk.StringVar(value="全部")
        filter_combo = ttk.Combobox(
            filter_frame, textvariable=self.filter_var,
            values=["全部", "基础状态", "情绪表情", "节日", "季节", "服装", "场景", "自定义"],
            width=10, state="readonly"
        )
        filter_combo.pack(side=tk.LEFT, padx=5)
        filter_combo.bind("<<ComboboxSelected>>", lambda e: self._filter_photos())

        # 照片网格
        self.content_frame = ttk.Frame(self)
        self.content_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        self.canvas = tk.Canvas(self.content_frame, highlightthickness=0)
        scrollbar = ttk.Scrollbar(self.content_frame, orient=tk.VERTICAL, command=self.canvas.yview)
        self.scrollable_frame = ttk.Frame(self.canvas)

        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )

        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=scrollbar.set)

        # 局部滚轮绑定
        def _bind_mousewheel(event):
            self.canvas.bind_all("<MouseWheel>",
                                  lambda e: self.canvas.yview_scroll(int(-1 * (e.delta / 120)), "units"))

        def _unbind_mousewheel(event):
            self.canvas.unbind_all("<MouseWheel>")

        self.canvas.bind("<Enter>", _bind_mousewheel)
        self.canvas.bind("<Leave>", _unbind_mousewheel)

        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # 底部分嗛〉
        bottom_frame = ttk.Frame(self)
        bottom_frame.pack(fill=tk.X, padx=10, pady=10)

        page_frame = ttk.Frame(bottom_frame)
        page_frame.pack(side=tk.LEFT)

        ttk.Button(page_frame, text=f"{get_icon('chevron_left', '◀')} 上一页", command=self._prev_page).pack(side=tk.LEFT, padx=2)
        self.page_label = ttk.Label(page_frame, text="第 1 页")
        self.page_label.pack(side=tk.LEFT, padx=10)
        ttk.Button(page_frame, text=f"下一页 {get_icon('chevron_right', '▶')}", command=self._next_page).pack(side=tk.LEFT, padx=2)

        action_frame = ttk.Frame(bottom_frame)
        action_frame.pack(side=tk.RIGHT)

        ttk.Button(action_frame, text=f"{get_icon('delete', '🗑️')} 删除选中", command=self._delete_selected).pack(side=tk.LEFT, padx=5)
        ttk.Button(action_frame, text=f"{get_icon('checkmark_circle', '✨')} 关闭", command=self._close).pack(side=tk.LEFT, padx=5)

        self.photo_images = []
        self.selected_photos = set()

    def _filter_photos(self):
        """筛选照片"""
        filter_type = self.filter_var.get()
        if filter_type == "全部":
            self.filtered_photos = self.photos
        else:
            # 根据状态类型筛选
            type_states = {
                "基础状态": ["idle", "thinking", "success", "error"],
                "情绪表情": ["happy", "sad", "excited", "shy", "angry", "surprised", "curious", "love", "worried"],
                "节日": ["spring_festival", "lantern", "dragon_boat", "qixi", "mid_autumn", "christmas", "halloween"],
                "季节": ["spring", "summer", "autumn", "winter"],
                "服装": ["sportswear", "maid", "swimsuit", "casual", "formal", "pajamas", "uniform", "kimono"],
                "场景": ["cooking", "gaming", "music", "shopping", "travel", "beach", "mountain", "cafe"],
                "自定义": ["custom"],
            }
            states = type_states.get(filter_type, [])
            self.filtered_photos = [p for p in self.photos if p.get("state") in states]

        self.current_page = 0
        self._load_page()

    def _load_page(self):
        """加载当前页"""
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()
        self.photo_images.clear()

        start_idx = self.current_page * self.photos_per_page
        end_idx = min(start_idx + self.photos_per_page, len(self.filtered_photos))

        total_pages = max(1, (len(self.filtered_photos) + self.photos_per_page - 1) // self.photos_per_page)
        self.page_label.configure(text=f"第 {self.current_page + 1}/{total_pages} 页")

        row, col = 0, 0
        for i in range(start_idx, end_idx):
            photo = self.filtered_photos[i]
            self._create_photo_card(photo, row, col)
            col += 1
            if col >= 4:
                col = 0
                row += 1

        if len(self.filtered_photos) == 0:
            ttk.Label(self.scrollable_frame, text="相册空空如也~\n快去拍摄一些立绘吧惂：",
                      font=("Microsoft YaHei", 14)).grid(row=0, column=0, columnspan=4, pady=50)

    def _create_photo_card(self, photo, row, col):
        """创建照片卡片"""
        card = ttk.Frame(self.scrollable_frame, relief="solid", borderwidth=1)
        card.grid(row=row, column=col, padx=8, pady=8, sticky="nsew")

        thumb_label = ttk.Label(card)
        thumb_label.pack(padx=5, pady=5)

        try:
            path = photo.get("path", "")
            if path and os.path.exists(path):
                img = Image.open(path)
                img.thumbnail((140, 140), Image.Resampling.LANCZOS)
                photo_img = ImageTk.PhotoImage(img)
                thumb_label.configure(image=photo_img)
                self.photo_images.append(photo_img)
            else:
                thumb_label.configure(text="[图片丢失]")
        except Exception:
            thumb_label.configure(text="[无法加载]")

        state_name = photo.get("state_name", photo.get("state", "未知"))
        emoji = STATE_EMOJIS.get(photo.get("state", ""), "🌸摲")
        ttk.Label(card, text=f"{emoji} {state_name}",
                  font=("Microsoft YaHei", 9, "bold")).pack()

        try:
            timestamp = datetime.fromisoformat(photo.get("timestamp", ""))
            time_str = timestamp.strftime("%Y-%m-%d")
        except:
            time_str = "未知时间"
        ttk.Label(card, text=time_str, font=("Microsoft YaHei", 8)).pack()

        # 选择妗
        var = tk.BooleanVar()
        cb = ttk.Checkbutton(card, variable=var, text="选中")
        cb.pack()
        cb.var = var
        cb.photo_id = photo.get("id")

    def _prev_page(self):
        if self.current_page > 0:
            self.current_page -= 1
            self._load_page()

    def _next_page(self):
        total_pages = max(1, (len(self.filtered_photos) + self.photos_per_page - 1) // self.photos_per_page)
        if self.current_page < total_pages - 1:
            self.current_page += 1
            self._load_page()

    def _delete_selected(self):
        """删除选中的照片"""
        selected_ids = []
        for widget in self.scrollable_frame.winfo_children():
            for child in widget.winfo_children():
                if isinstance(child, ttk.Checkbutton) and hasattr(child, 'var'):
                    if child.var.get():
                        selected_ids.append(child.photo_id)

        if not selected_ids:
            messagebox.showinfo("提示", "璇峰厛选择瑕佸垹闄ょ殑照片")
            return

        if messagebox.askyesno("确认删除", f"确定要删除 {len(selected_ids)} 张照片囧悧："):
            self.photos = [p for p in self.photos if p.get("id") not in selected_ids]
            self.filtered_photos = [p for p in self.filtered_photos if p.get("id") not in selected_ids]
            self._load_page()
            self.stats_label.configure(text=f"共 {len(self.photos)} 张照片")

    def _close(self):
        """关闭"""
        self.result = self.photos
        self.destroy()


class QuickInputDialog(tk.Toplevel):
    """快速输入对话框 - 用于快速添加角色、场景等"""

    def __init__(self, parent, title: str = "快速输入", prompt: str = "璇疯緭鍏:",
                 fields: List[Dict[str, str]] = None, initial_values: Dict[str, str] = None):
        """
        分濆嬪寲快速输入对话框

        Args:
            parent: 鐖剁獥可见
            title: 对话框标题
            prompt: 提示文字
            fields: 字段列表 [{"name": "field_name", "label": "显示标签", "required": True}]
            initial_values: 分濆嬪 {"field_name": "value"}
        """
        super().__init__(parent)
        self.title(title)
        self.result = None
        self.entries = {}

        # 默认ゅ瓧娈
        if fields is None:
            fields = [{"name": "value", "label": prompt, "required": True}]

        self.fields = fields
        self.initial_values = initial_values or {}

        self._setup_ui()

        # 居中显示
        self.update_idletasks()
        width = self.winfo_width()
        height = self.winfo_height()
        x = (self.winfo_screenwidth() // 2) - (width // 2)
        y = (self.winfo_screenheight() // 2) - (height // 2)
        self.geometry(f"+{x}+{y}")

        self.transient(parent)
        self.grab_set()

        # 缁戝畾快捷键
        self.bind("<Return>", lambda e: self._confirm())
        self.bind("<Escape>", lambda e: self._cancel())

        # 焦点到第一个输入框
        if self.entries:
            first_entry = list(self.entries.values())[0]
            first_entry.focus_set()

    def _setup_ui(self):
        """设置UI"""
        main_frame = ttk.Frame(self, padding=15)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # 创建输入字段
        for field in self.fields:
            field_name = field.get("name", "value")
            label_text = field.get("label", "杈撳叆:")
            required = field.get("required", False)
            field_type = field.get("type", "entry")  # entry, text, combo

            # 标签
            label = ttk.Label(main_frame, text=label_text + (" *" if required else ""))
            label.pack(anchor=tk.W, pady=(5, 2))

            if field_type == "text":
                # 多行文本
                text_frame = ttk.Frame(main_frame)
                text_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 5))

                text = tk.Text(text_frame, height=4, width=40, font=("Microsoft YaHei", 10))
                scrollbar = ttk.Scrollbar(text_frame, orient=tk.VERTICAL, command=text.yview)
                text.configure(yscrollcommand=scrollbar.set)

                text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
                scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

                # 设置分濆嬪
                if field_name in self.initial_values:
                    text.insert("1.0", self.initial_values[field_name])

                self.entries[field_name] = text

            elif field_type == "combo":
                # 下拉选择
                options = field.get("options", [])
                combo = ttk.Combobox(main_frame, values=options, state="readonly", width=37)
                combo.pack(fill=tk.X, pady=(0, 5))

                # 设置分濆嬪
                if field_name in self.initial_values:
                    combo.set(self.initial_values[field_name])
                elif options:
                    combo.current(0)

                self.entries[field_name] = combo

            else:
                # 单行输入
                entry = ttk.Entry(main_frame, width=40, font=("Microsoft YaHei", 10))
                entry.pack(fill=tk.X, pady=(0, 5))

                # 设置分濆嬪
                if field_name in self.initial_values:
                    entry.insert(0, self.initial_values[field_name])

                self.entries[field_name] = entry

        # 按钮鍖
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=tk.X, pady=(15, 0))

        ttk.Button(btn_frame, text=f"{get_icon('dismiss', '✨')} 取消", command=self._cancel).pack(side=tk.RIGHT, padx=(5, 0))
        ttk.Button(btn_frame, text=f"{get_icon('checkmark_circle', '✨')} 确定", command=self._confirm).pack(side=tk.RIGHT)


    def _get_value(self, widget) -> str:
        """鑾峰彇鎺т欢鍊"""
        if isinstance(widget, tk.Text):
            return widget.get("1.0", tk.END).strip()
        elif isinstance(widget, ttk.Combobox):
            return widget.get()
        else:
            return widget.get().strip()

    def _confirm(self):
        """确认"""
        # 验证必填字段
        for field in self.fields:
            field_name = field.get("name", "value")
            required = field.get("required", False)

            if required:
                value = self._get_value(self.entries.get(field_name))
                if not value:
                    label = field.get("label", "璇ュ瓧娈")
                    messagebox.showwarning("提示", f"{label} 不能为空")
                    self.entries[field_name].focus_set()
                    return

        # 鏀堕泦结果
        self.result = {}
        for field_name, widget in self.entries.items():
            self.result[field_name] = self._get_value(widget)

        # 如果只有一个字段且不为value：则直接返回值
        if len(self.result) == 1 and "value" in self.result:
            self.result = self.result["value"]

        self.destroy()

    def _cancel(self):
        """取消"""
        self.result = None
        self.destroy()


class QuickCharacterDialog(QuickInputDialog):
    """快速添加角色对话框"""

    def __init__(self, parent):
        fields = [
            {"name": "name", "label": "角色名称", "required": True},
            {"name": "description", "label": "角色描述", "type": "text", "required": False},
            {"name": "role", "label": "角色类型", "type": "combo",
             "options": ["主角", "配角", "反派", "路人", "其他"]}
        ]
        super().__init__(parent, title="快速添加角色", fields=fields)


class QuickSceneDialog(QuickInputDialog):
    """快速添加场景对话框"""

    def __init__(self, parent, locations: List[str] = None):
        locations = locations or ["室内", "室外", "街道", "家中", "学校", "办公室", "其他"]
        fields = [
            {"name": "name", "label": "场景否嶇О", "required": True},
            {"name": "location", "label": "地点", "type": "combo", "options": locations},
            {"name": "time", "label": "时间", "type": "combo",
             "options": ["鐧藉ぉ", "夜晚", "榛庢槑", "榛勬槒", "不限"]},
            {"name": "description", "label": "场景描述", "type": "text", "required": False}
        ]
        super().__init__(parent, title="快速添加场景", fields=fields)


class QuickIdeaDialog(QuickInputDialog):
    """快速添加灵感对话框"""

    def __init__(self, parent, categories: List[str] = None):
        categories = categories or ["剧情", "角色", "设定", "对白", "场景", "其他"]
        fields = [
            {"name": "title", "label": "鐏垫劅标题", "required": True},
            {"name": "category", "label": "分嗙被", "type": "combo", "options": categories},
            {"name": "content", "label": "鐏垫劅内容", "type": "text", "required": False}
        ]
        super().__init__(parent, title="快速记录灵感", fields=fields)


class QuickResearchDialog(QuickInputDialog):
    """快速添加研究笔记对话框"""

    def __init__(self, parent, categories: List[str] = None):
        categories = categories or ["背景", "人物", "历史", "技术", "文化", "其他"]
        fields = [
            {"name": "title", "label": "笔记标题", "required": True},
            {"name": "category", "label": "分嗙被", "type": "combo", "options": categories},
            {"name": "content", "label": "笔记内容", "type": "text", "required": False},
            {"name": "source", "label": "鏉ユ簮/可见傝"}
        ]
        super().__init__(parent, title="快速添加研究笔记", fields=fields)


class WeatherSettingsDialog(tk.Toplevel):
    """天气设置对话妗"""

    def __init__(self, parent, config_manager=None, weather_service=None):
        super().__init__(parent)
        self.config_manager = config_manager
        self.weather_service = weather_service
        self.result = None
        self._search_results = []

        self.title("天气设置")
        self.geometry("450x500")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        self._setup_ui()
        self._load_current_config()

        # 居中显示
        self.update_idletasks()
        x = parent.winfo_rootx() + (parent.winfo_width() - self.winfo_width()) // 2
        y = parent.winfo_rooty() + (parent.winfo_height() - self.winfo_height()) // 2
        self.geometry(f"+{x}+{y}")

    def _setup_ui(self):
        """设置UI"""
        main_frame = ttk.Frame(self, padding=15)
        main_frame.pack(fill="both", expand=True)

        # 标题
        title_label = ttk.Label(main_frame, text="和风天气 API 设置",
                                font=("", 14, "bold"))
        title_label.pack(pady=(0, 15))

        # 启用开关
        self.enabled_var = tk.BooleanVar(value=False)
        enable_frame = ttk.Frame(main_frame)
        enable_frame.pack(fill="x", pady=5)
        ttk.Checkbutton(enable_frame, text="启用天气同步",
                        variable=self.enabled_var).pack(side="left")

        # API Key
        key_frame = ttk.LabelFrame(main_frame, text="API 瀵嗛挜", padding=10)
        key_frame.pack(fill="x", pady=10)

        ttk.Label(key_frame, text="和风天气 API Key:").pack(anchor="w")
        self.api_key_var = tk.StringVar()
        self.api_key_entry = ttk.Entry(key_frame, textvariable=self.api_key_var,
                                        width=50, show="*")
        self.api_key_entry.pack(fill="x", pady=5)

        key_info = ttk.Label(key_frame, text="在 dev.qweather.com 注册获取彇鍏嶈垂 API Key",
                             foreground="gray")
        key_info.pack(anchor="w")

        # 城市选择
        location_frame = ttk.LabelFrame(main_frame, text="城市设置", padding=10)
        location_frame.pack(fill="x", pady=10)

        # 搜索妗
        search_frame = ttk.Frame(location_frame)
        search_frame.pack(fill="x", pady=5)
        ttk.Label(search_frame, text="搜索城市:").pack(side="left")
        self.search_var = tk.StringVar()
        self.search_entry = ttk.Entry(search_frame, textvariable=self.search_var, width=25)
        self.search_entry.pack(side="left", padx=5)
        ttk.Button(search_frame, text="搜索", command=self._search_city).pack(side="left")

        # 搜索结果列表
        self.city_listbox = tk.Listbox(location_frame, height=5)
        self.city_listbox.pack(fill="x", pady=5)
        self.city_listbox.bind("<<ListboxSelect>>", self._on_city_select)

        # 当前选中的城市
        current_frame = ttk.Frame(location_frame)
        current_frame.pack(fill="x", pady=5)
        ttk.Label(current_frame, text="当前城市:").pack(side="left")
        self.location_name_var = tk.StringVar(value="鍖椾含")
        self.location_label = ttk.Label(current_frame,
                                         textvariable=self.location_name_var,
                                         font=("", 10, "bold"))
        self.location_label.pack(side="left", padx=5)

        self.location_id_var = tk.StringVar(value="101010100")

        # 更新设置
        update_frame = ttk.LabelFrame(main_frame, text="更新设置", padding=10)
        update_frame.pack(fill="x", pady=10)

        interval_frame = ttk.Frame(update_frame)
        interval_frame.pack(fill="x")
        ttk.Label(interval_frame, text="更新间隔:").pack(side="left")
        self.interval_var = tk.StringVar(value="30")
        interval_combo = ttk.Combobox(interval_frame, textvariable=self.interval_var,
                                       values=["15", "30", "60", "120"], width=10)
        interval_combo.pack(side="left", padx=5)
        ttk.Label(interval_frame, text="分钟").pack(side="left")

        # 鑱斿姩设置
        link_frame = ttk.LabelFrame(main_frame, text="鑱斿姩设置", padding=10)
        link_frame.pack(fill="x", pady=10)

        self.auto_ambiance_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(link_frame, text="天气联动环境音：（下雨时自动播放雨声）",
                        variable=self.auto_ambiance_var).pack(anchor="w")

        self.show_in_scene_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(link_frame, text="场景生成浣跨敤鐪熷疄天气",
                        variable=self.show_in_scene_var).pack(anchor="w")

        # 按钮
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill="x", pady=15)
        ttk.Button(btn_frame, text="保存", command=self._save).pack(side="right", padx=5)
        ttk.Button(btn_frame, text="取消", command=self.destroy).pack(side="right")
        ttk.Button(btn_frame, text="测试连接", command=self._test_connection).pack(side="left")

    def _load_current_config(self):
        """加载当前配置"""
        if not self.config_manager:
            return

        config = self.config_manager.get_weather_config()
        self.enabled_var.set(config.get("enabled", False))
        self.api_key_var.set(config.get("api_key", ""))
        self.location_id_var.set(config.get("location", "101010100"))
        self.location_name_var.set(config.get("location_name", "鍖椾含"))
        self.auto_ambiance_var.set(config.get("auto_ambiance", True))
        self.show_in_scene_var.set(config.get("show_in_scene", True))

        # 更新间隔：堢掕浆分钟：
        interval_sec = config.get("update_interval", 1800)
        self.interval_var.set(str(interval_sec // 60))

    def _search_city(self):
        """搜索城市"""
        keyword = self.search_var.get().strip()
        if not keyword:
            return

        api_key = self.api_key_var.get().strip()
        if not api_key:
            messagebox.showwarning("提示", "璇峰厛杈撳叆 API Key")
            return

        # 使用天气服务搜索
        try:
            from ..weather_service import WeatherService
            service = WeatherService(api_key, "")
            cities = service.search_city(keyword)

            self.city_listbox.delete(0, tk.END)
            self._search_results = cities

            for city in cities:
                display = f"{city['name']} ({city['adm1']} {city['adm2']})"
                self.city_listbox.insert(tk.END, display)

            if not cities:
                self.city_listbox.insert(tk.END, "未找到匹配的城市")

        except Exception as e:
            messagebox.showerror("搜索失败", str(e))

    def _on_city_select(self, event):
        """选择城市"""
        selection = self.city_listbox.curselection()
        if not selection:
            return

        idx = selection[0]
        if idx < len(self._search_results):
            city = self._search_results[idx]
            self.location_id_var.set(city["id"])
            self.location_name_var.set(city["name"])

    def _test_connection(self):
        """测试API连接"""
        api_key = self.api_key_var.get().strip()
        location = self.location_id_var.get()

        if not api_key:
            messagebox.showwarning("提示", "璇疯緭共 API Key")
            return

        try:
            from ..weather_service import WeatherService
            service = WeatherService(api_key, location)
            service.location_name = self.location_name_var.get()
            weather = service.get_current_weather(force_refresh=True)

            if weather:
                messagebox.showinfo("连接成功",
                    f"城市: {weather.location_name}\n"
                    f"天气: {weather.text}\n"
                    f"温度: {weather.temp}°C\n"
                    f"婀垮害: {weather.humidity}%")
            else:
                messagebox.showerror("连接失败", "无法获取天气数据：请检查 API Key 鍜屽煄甯傝剧疆")

        except Exception as e:
            messagebox.showerror("连接失败", str(e))

    def _save(self):
        """保存配置"""
        if not self.config_manager:
            self.destroy()
            return

        config = {
            "enabled": self.enabled_var.get(),
            "api_key": self.api_key_var.get().strip(),
            "location": self.location_id_var.get(),
            "location_name": self.location_name_var.get(),
            "update_interval": int(self.interval_var.get()) * 60,
            "auto_ambiance": self.auto_ambiance_var.get(),
            "show_in_scene": self.show_in_scene_var.get(),
        }

        self.config_manager.set_weather_config(config)
        self.result = config
        self.destroy()


class SchoolEventDialog(tk.Toplevel):
    """学校事件对话妗"""

    def __init__(self, parent, event, event_manager=None):
        super().__init__(parent)
        self.title(event.title)
        self.geometry("400x500")
        self.event = event
        self.event_manager = event_manager
        self.result_index = -1
        self._setup_ui()
        self.transient(parent)
        self.grab_set()

    def _setup_ui(self):
        # 标题樻爮
        header_frame = ttk.Frame(self)
        header_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Label(header_frame, text=f"🌸彨 {self.event.title}", 
                  font=("Microsoft YaHei", 12, "bold")).pack(side=tk.LEFT, pady=5)
                  
        if self.event_manager:
            ttk.Button(header_frame, text="🌸摉 鍥為【", width=6, 
                       command=self._show_history).pack(side=tk.RIGHT)
        
        # 描述
        desc_frame = ttk.Frame(self)
        desc_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=5)
        
        ttk.Label(desc_frame, text=self.event.description, 
                  font=("Microsoft YaHei", 10), wraplength=350).pack(anchor=tk.N)
                  
        # 选项
        btn_frame = ttk.Frame(self)
        btn_frame.pack(fill=tk.X, padx=20, pady=20)
        
        for idx, choice in enumerate(self.event.choices):
            btn = ttk.Button(
                btn_frame, 
                text=choice.text,
                command=lambda i=idx: self._select(i)
            )
            btn.pack(fill=tk.X, pady=5)
            
        ttk.Button(btn_frame, text="快速界暐", command=self.destroy).pack(pady=10)

    def _select(self, index):
        self.result_index = index
        self.destroy()

    def _show_history(self):
        if self.event_manager:
            EventHistoryDialog(self, self.event_manager.get_event_history())


class EventHistoryDialog(tk.Toplevel):
    """Event history dialog / 事件历史对话框"""

    def __init__(self, parent, history: List[Dict]):
        super().__init__(parent)
        self.title("事件回顾 / Event History")
        self.geometry("500x600")
        self.history = history
        self._setup_ui()
        self.transient(parent)
        self.grab_set()

    def _setup_ui(self):
        ttk.Label(
            self,
            text=f"{get_icon('book', '📖')} 事件回顾 / Event History",
            font=("Microsoft YaHei", 12, "bold"),
        ).pack(pady=10)

        list_frame = ttk.Frame(self)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        canvas = tk.Canvas(list_frame, highlightthickness=0)
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)

        scrollable_frame.bind(
            "<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        def _bind_mousewheel(_event):
            canvas.bind_all(
                "<MouseWheel>",
                lambda e: canvas.yview_scroll(int(-1 * (e.delta / 120)), "units"),
            )

        def _unbind_mousewheel(_event):
            canvas.unbind_all("<MouseWheel>")

        canvas.bind("<Enter>", _bind_mousewheel)
        canvas.bind("<Leave>", _unbind_mousewheel)

        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        if not self.history:
            ttk.Label(
                scrollable_frame,
                text="暂无事件记录... / No event history yet...",
                font=("Microsoft YaHei", 10),
                foreground="gray",
            ).pack(pady=20)
        else:
            for entry in self.history:
                self._create_history_card(scrollable_frame, entry)

        ttk.Button(self, text="关闭 / Close", command=self.destroy).pack(pady=10)

    def _create_history_card(self, parent, entry):
        card = ttk.Frame(parent, relief="solid", borderwidth=1)
        card.pack(fill=tk.X, padx=5, pady=5)

        header = ttk.Frame(card)
        header.pack(fill=tk.X, padx=5, pady=2)

        try:
            ts = datetime.fromisoformat(entry.get("timestamp", ""))
            time_str = ts.strftime("%Y-%m-%d %H:%M")
        except ValueError:
            time_str = entry.get("timestamp", "")

        ttk.Label(
            header,
            text=entry.get("title", "未知事件 / Unknown Event"),
            font=("Microsoft YaHei", 10, "bold"),
        ).pack(side=tk.LEFT)
        ttk.Label(
            header, text=time_str, font=("Microsoft YaHei", 8), foreground="gray"
        ).pack(side=tk.RIGHT)

        content = ttk.Frame(card)
        content.pack(fill=tk.X, padx=10, pady=2)

        ttk.Label(
            content,
            text=f"选择 / Choice: {entry.get('choice_text', '')}",
            font=("Microsoft YaHei", 9),
            foreground="#555",
        ).pack(anchor=tk.W)

        outcome = entry.get("outcome_text", "")
        if len(outcome) > 50:
            outcome = outcome[:50] + "..."

        ttk.Label(
            content,
            text=f"结果 / Outcome: {outcome}",
            font=("Microsoft YaHei", 9),
            wraplength=400,
        ).pack(anchor=tk.W)
