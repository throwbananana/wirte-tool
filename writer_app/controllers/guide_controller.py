import json
import logging
from pathlib import Path
import tkinter as tk
from tkinter import ttk, messagebox
from typing import Optional

from writer_app.core.project_types import ProjectTypeManager
from writer_app.ui.components.highlight_overlay import HighlightOverlay
from writer_app.ui.components.guide_tooltip import GuideTooltip
from writer_app.core.guide_animation import get_animation_manager
from writer_app.core.guide_checks import (
    check_project_saved,
    check_outline_added,
    check_scene_written,
    check_timeline_added,
    check_dual_timeline_added,
    check_evidence_added,
    check_relationship_linked,
    check_heartbeat_added,
    check_faction_added,
    check_world_entry_added,
    check_iceberg_entry_added,
    check_variable_added,
    check_flowchart_linked,
    check_scene_time_set,
    check_export_done,
)

logger = logging.getLogger(__name__)


class GuideController:
    HIGHLIGHT_RETRY_DELAY_MS = 80
    HIGHLIGHT_RETRY_LIMIT = 12
    GUIDE_DIALOG_RETRY_DELAY_MS = 120
    GUIDE_DIALOG_RETRY_LIMIT = 12

    def __init__(self, app):
        self.app = app
        self._guide_mode_running = False
        self._guide_steps = []
        self._guide_step_index = 0
        self._guide_dialog = None
        self._guide_progress_var = None
        self._guide_title_var = None
        self._guide_body_var = None
        self._guide_test_var = None
        self._guide_status_var = None
        self._guide_flow_var = None
        self._guide_btn_prev = None
        self._guide_btn_next = None
        self._root_escape_bind_id = None

        # Highlight system
        self._highlight_overlay: Optional[HighlightOverlay] = None
        self._guide_tooltip: Optional[GuideTooltip] = None
        self._highlight_enabled = True  # Can be toggled in settings

    @property
    def is_running(self):
        return self._guide_mode_running

    def start_if_needed(self):
        if self._guide_mode_running:
            return
        if not self.app.config_manager.get("guide_mode_enabled", True):
            return

        self._ensure_sample_project_loaded()
        steps = self._build_guide_steps()
        if not steps:
            return

        self._guide_steps = steps
        start_index = int(self.app.config_manager.get("guide_mode_step", 0) or 0)
        if start_index < 0 or start_index >= len(self._guide_steps):
            start_index = 0
        self._guide_step_index = start_index
        self._guide_mode_running = True
        self._bind_escape_shortcut()
        self._open_guide_dialog()
        self._show_guide_step(self._guide_step_index)

    def show_dev_notice_if_needed(self):
        if self.app.config_manager.get("dev_notice_dismissed", False):
            self.start_if_needed()
            return

        dialog = tk.Toplevel(self.app.root)
        dialog.title("开发测试提示")
        dialog.transient(self.app.root)
        dialog.grab_set()
        dialog.resizable(False, False)

        frame = ttk.Frame(dialog, padding=12)
        frame.pack(fill="both", expand=True)

        ttk.Label(
            frame,
            text="当前项目仍处于开发测试阶段，功能与稳定性可能会变化。"
        ).pack(anchor="w")

        never_show_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            frame,
            text="不再提示",
            variable=never_show_var
        ).pack(anchor="w", pady=(8, 0))

        def on_close():
            if never_show_var.get():
                self.app.config_manager.set("dev_notice_dismissed", True)
                self.app.config_manager.save()
            dialog.destroy()
            self.start_if_needed()

        ttk.Button(frame, text="我知道了", command=on_close).pack(anchor="e", pady=(12, 0))
        dialog.protocol("WM_DELETE_WINDOW", on_close)

    def mark_progress(self, check_key: str, details=None) -> None:
        key = self._get_guide_progress_key(check_key)
        self.app.guide_progress.mark_completed(key, details or {})

    def close(self, reset_progress=False):
        if not self._guide_mode_running:
            return
        self._guide_mode_running = False
        if reset_progress:
            self.app.config_manager.set("guide_mode_step", 0)
            self.app.config_manager.save()

        # Clean up highlight resources
        self.cleanup()
        self._unbind_escape_shortcut()

        if getattr(self, "_guide_dialog", None):
            self._guide_dialog.destroy()
            self._guide_dialog = None

    def _get_guide_progress_key(self, check_key: str) -> str:
        type_key = self.app.project_manager.get_project_type()
        return f"{type_key}:{check_key}"

    def _build_guide_steps(self):
        type_key = self.app.project_manager.get_project_type()
        length_key = self.app.project_manager.get_project_length()
        enabled_tools = self.app.project_manager.get_enabled_tools()

        steps = [
            {
                "title": "欢迎进入助理模式",
                "body": "本引导会按默认模式依次介绍功能模块，并给出最小测试建议。",
                "test": "按“下一步”开始。",
                "flow": "将按项目类型引导核心流程与模块联动。",
                "tab_id": None,
                "check_key": "welcome",
            },
            {
                "title": "创建并保存项目",
                "body": "项目的新建/打开/保存/项目设置都在“文件”菜单中。",
                "test": "新建项目并保存到本地一次。",
                "flow": "后续所有模块都基于项目文件与数据。",
                "tab_id": None,
                "check_key": "project_saved",
            },
        ]

        if "outline" in enabled_tools:
            steps.append({
                "title": "建立大纲结构",
                "body": "在思维导图/大纲中新增节点，形成章节结构。",
                "test": "新增至少一个大纲节点。",
                "flow": "流程：大纲 → 场景 → 时间线 → 导出",
                "tab_id": self.app.tabs.get("outline"),
                "check_key": "outline_added",
                "highlight_target": "outline_tab",
                "highlight_animation": "pulse",
            })

        if "script" in enabled_tools:
            steps.append({
                "title": "写作场景内容",
                "body": "在剧本写作中新增场景并填写内容。",
                "test": "新增场景并写入几行内容。",
                "flow": "流程：场景 → 时间线/日历 → 导出",
                "tab_id": self.app.tabs.get("script"),
                "check_key": "scene_written",
                "highlight_target": "script_tab",
                "highlight_animation": "pulse",
            })

        if "timeline" in enabled_tools:
            steps.append({
                "title": "时间线事件",
                "body": "在时间轴中添加事件，确保时间顺序清晰。",
                "test": "新增至少一条时间线事件。",
                "flow": "流程：时间线 ← 场景时间 → 日历/双轨图",
                "tab_id": self.app.tabs.get("timeline"),
                "check_key": "timeline_added",
                "highlight_target": "timeline_tab",
                "highlight_animation": "pulse",
            })

        if "dual_timeline" in enabled_tools:
            steps.append({
                "title": "双轨时间线",
                "body": "推理模式下需要建立真相与叙述的双轨时间线。",
                "test": "新增真相事件与叙述事件。",
                "flow": "流程：双轨时间线 ? 证据板 ? 不在场证明",
                "tab_id": self.app.tabs.get("dual_timeline"),
                "check_key": "dual_timeline_added",
            })

        type_steps = []
        if type_key == "Suspense":
            if "evidence_board" in enabled_tools:
                type_steps.append({
                    "title": "证据板",
                    "body": "整理线索、证据与关系，形成推理链条。",
                    "test": "新增线索或关联。",
                    "flow": "流程：证据板 ? 双轨时间线 ? 不在场证明",
                    "tab_id": self.app.tabs.get("evidence_board"),
                    "check_key": "evidence_added",
                })
            if "alibi" in enabled_tools:
                type_steps.append({
                    "title": "不在场证明",
                    "body": "标注场景时间信息，辅助逻辑核验。",
                    "test": "为至少一个场景填写时间。",
                    "flow": "流程：场景时间 → 双轨时间线 → 推理核验",
                    "tab_id": self.app.tabs.get("alibi"),
                    "check_key": "scene_time_set",
                })
        elif type_key == "Romance":
            if "relationship" in enabled_tools:
                type_steps.append({
                    "title": "人物关系",
                    "body": "建立主角之间的关系动态。",
                    "test": "新增一条人物关系。",
                    "flow": "流程：人物关系 → 心动追踪 → 剧情走向",
                    "tab_id": self.app.tabs.get("relationship"),
                    "check_key": "relationship_linked",
                })
            if "heartbeat" in enabled_tools:
                type_steps.append({
                    "title": "心动追踪",
                    "body": "标注关键情感节点，形成恋爱曲线。",
                    "test": "标记至少一个心动节点。",
                    "flow": "流程：场景 → 心动节点 → 情感曲线",
                    "tab_id": self.app.tabs.get("heartbeat"),
                    "check_key": "heartbeat_added",
                })
        elif type_key == "Epic":
            if "wiki" in enabled_tools:
                type_steps.append({
                    "title": "世界观百科",
                    "body": "为世界观建立基础条目。",
                    "test": "新增一个百科条目。",
                    "flow": "流程：百科 → 冰山层级 → 设定深化",
                    "tab_id": self.app.tabs.get("wiki"),
                    "check_key": "world_entry_added",
                })
            if "iceberg" in enabled_tools:
                type_steps.append({
                    "title": "世界冰山",
                    "body": "扩展世界观层级与隐性设定。",
                    "test": "新增一个冰山层级条目。",
                    "flow": "流程：冰山层级 ← 百科条目",
                    "tab_id": self.app.tabs.get("iceberg"),
                    "check_key": "iceberg_entry_added",
                })
        elif type_key == "SciFi":
            if "faction" in enabled_tools:
                type_steps.append({
                    "title": "势力矩阵",
                    "body": "创建势力条目并设置关系。",
                    "test": "新增一个势力。",
                    "flow": "流程：势力矩阵 ? 人物关系 → 剧情冲突",
                    "tab_id": self.app.tabs.get("faction"),
                    "check_key": "faction_added",
                })
            if "relationship" in enabled_tools:
                type_steps.append({
                    "title": "人物关系",
                    "body": "构建阵营或角色关系网络。",
                    "test": "新增一条人物关系。",
                    "flow": "流程：人物关系 ? 势力矩阵",
                    "tab_id": self.app.tabs.get("relationship"),
                    "check_key": "relationship_linked",
                })
        elif type_key == "LightNovel":
            if "wiki" in enabled_tools:
                type_steps.append({
                    "title": "世界观百科",
                    "body": "整理人物设定或技能条目。",
                    "test": "新增一个百科条目。",
                    "flow": "流程：百科 → 角色/设定 → 场景",
                    "tab_id": self.app.tabs.get("wiki"),
                    "check_key": "world_entry_added",
                })
        elif type_key == "Galgame":
            if "variable" in enabled_tools:
                type_steps.append({
                    "title": "变量管理",
                    "body": "定义分支变量，支持剧情判断。",
                    "test": "新增一个变量。",
                    "flow": "流程：变量 → 条件分支 → 剧情流向",
                    "tab_id": self.app.tabs.get("variable"),
                    "check_key": "variable_added",
                })
            if "flowchart" in enabled_tools:
                type_steps.append({
                    "title": "剧情流向",
                    "body": "建立选项与场景连接，形成分支结构。",
                    "test": "创建并连接两个节点。",
                    "flow": "流程：场景 choices → 分支跳转 → 剧情流向",
                    "tab_id": self.app.tabs.get("flowchart"),
                    "check_key": "flowchart_linked",
                })

        for step in type_steps:
            if step.get("tab_id"):
                steps.append(step)

        steps.append({
            "title": "导出成果",
            "body": "导出功能在“文件 → 导出”菜单中，可导出为支持的格式。",
            "test": "执行一次导出并确认文件生成。",
            "flow": "流程：项目数据 → 导出文件",
            "tab_id": None,
            "check_key": "export_done",
        })

        guide_defs = {
            "outline": ("思维导图/大纲", "用于搭建章节结构与节点层级。", "新增子节点（Tab）或同级节点（Enter）。", "与场景、时间线、剧情结构联动。"),
            "script": ("剧本写作", "用于写作场景与正文内容，支持字数统计与快捷键。", "输入几行文本并观察字数变化。", "内容可同步时间线、日历与关系分析。"),
            "char_events": ("人物事件", "用于记录人物关键事件与关联节点。", "新增一条人物事件记录。", "可作为角色时间线与剧情参考。"),
            "relationship": ("人物关系图", "用于管理角色关系与互动连线。", "添加一条角色关系。", "可与势力/剧情冲突联动。"),
            "evidence_board": ("线索墙", "用于整理悬疑线索与证据关联。", "新增线索卡片并拖动调整。", "与双轨时间线、不在场证明联动。"),
            "timeline": ("时间轴", "用于编排故事事件顺序与时间线。", "添加一个时间轴事件。", "与场景时间字段、日历联动。"),
            "story_curve": ("故事曲线", "用于查看节奏起伏与关键节点。", "移动一个节点位置。", "基于场景与剧情结构统计。"),
            "swimlanes": ("故事泳道", "用于并行线索与多视角叙事。", "切换或新增一条泳道。", "与场景与时间线并行展示。"),
            "dual_timeline": ("表里双轨图", "用于对照表里剧情或两条事件链。", "新增一条表/里事件。", "与证据板/不在场证明配合。"),
            "kanban": ("场次看板", "用于管理场次进度与状态。", "拖动一张卡片到新列。", "与场景进度同步。"),
            "calendar": ("故事日历", "用于按日期查看事件分布。", "切换到任意日期查看。", "依赖场景时间字段。"),
            "wiki": ("世界观百科", "用于整理设定、地点、人物与物品资料。", "新增一个百科条目。", "可扩展到冰山/势力/人物设定。"),
            "research": ("资料搜集", "用于记录引用资料与整理来源。", "新增一条资料记录。", "可作为世界观与剧情参考。"),
            "reverse_engineering": ("反推导学习", "用于学习与拆解剧本结构。", "导入或粘贴一段文本。", "支持结构反推与创作辅助。"),
            "analytics": ("数据统计", "用于查看项目指标与进度统计。", "打开统计面板查看数据。", "基于项目数据汇总。"),
            "heartbeat": ("心动追踪", "用于记录情感进展与关键节点。", "新增一条心动事件。", "来源于场景并形成情感曲线。"),
            "alibi": ("不在场证明", "用于构建逻辑链与时间线核验。", "新增一条不在场证明记录。", "依赖场景时间字段。"),
            "iceberg": ("世界冰山", "用于分层管理世界观设定。", "新增一个冰山层级条目。", "基于百科条目深度扩展。"),
            "faction": ("势力矩阵", "用于管理势力结构与关系。", "新增一个势力关系。", "可与人物关系/冲突联动。"),
            "variable": ("变量管理", "用于管理分支变量与条件。", "新增一个变量并保存。", "影响剧情分支与条件判定。"),
            "flowchart": ("剧情流向", "用于配置剧情分支与流向。", "创建并连接两个节点。", "依赖场景 choices。"),
            "ideas": ("灵感箱", "用于收集与整理灵感条目。", "新增一个灵感。", "可回流到大纲与场景。"),
            "training": ("创意训练", "用于进行创意练习与挑战。", "启动一次训练。", "练习成果可保存到灵感箱。"),
            "chat": ("项目对话", "用于项目内对话与提示。", "打开对话面板并发送一条内容。", "可用于快速询问和信息检索。"),
        }

        tab_ids = self.app.notebook.tabs()
        frame_to_key = {frame: key for key, frame in self.app.tabs.items()}
        for tab_id in tab_ids:
            frame = self.app.root.nametowidget(tab_id)
            tab_key = frame_to_key.get(frame)
            tab_text = self.app.notebook.tab(tab_id, "text").strip() or "模块"
            if tab_key in guide_defs:
                title, body, test, flow = guide_defs[tab_key]
            else:
                title = tab_text
                body = "用于项目管理与创作辅助的功能模块。"
                test = "打开模块并浏览主要功能。"
                flow = "该模块可能与项目数据或其他模块联动。"

            steps.append({
                "title": title,
                "body": body,
                "test": test,
                "flow": flow,
                "tab_id": tab_id,
                "check_key": None,
            })

        steps.append({
            "title": "关闭引导",
            "body": "如需关闭助理模式引导，请前往“设置 → 通用”关闭。",
            "test": "进入设置确认开关位置。",
            "flow": "引导关闭后可随时在设置中重新开启。",
            "tab_id": None,
            "check_key": "close",
        })

        return steps

    def _ensure_sample_project_loaded(self):
        if self.app.project_manager.current_file:
            return
        if not self._is_project_empty():
            return

        sample_path = self.app.data_dir / "1.writerproj"
        if not sample_path.exists():
            sample_path = self.app.data_dir / "sample_project.writerproj"
            if not sample_path.exists():
                self._create_minimal_sample_project(sample_path)

        try:
            if sample_path.exists():
                self.app.project_manager.load_project(str(sample_path))
        except Exception as exc:
            logger.warning("Failed to load sample project: %s", exc)

    def _create_minimal_sample_project(self, sample_path: Path) -> None:
        data = self.app.project_manager._create_empty_project()
        data["meta"]["type"] = "General"
        data["meta"]["length"] = "Short"
        data["outline"]["name"] = "Sample Outline"
        data["outline"]["children"] = [
            {
                "name": "Act 1",
                "content": "Introduce the setting and main conflict.",
                "uid": self.app.project_manager._gen_uid(),
                "children": []
            }
        ]
        data["script"]["title"] = "Sample Script"
        data["script"]["scenes"] = [
            {
                "title": "Scene 1",
                "content": "A short sample scene to start writing.",
                "characters": [],
                "outline_ref": "",
                "uid": self.app.project_manager._gen_uid()
            }
        ]

        try:
            sample_path.parent.mkdir(parents=True, exist_ok=True)
            with open(sample_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=True, indent=2)
        except Exception as exc:
            logger.warning("Failed to create sample project file: %s", exc)

    def _is_project_empty(self) -> bool:
        outline = self.app.project_manager.get_outline() or {}
        if outline.get("children"):
            return False
        script = self.app.project_manager.get_script() or {}
        if script.get("characters") or script.get("scenes"):
            return False
        return True

    def _position_guide_dialog(self, dialog_w: int, dialog_h: int, attempt: int = 0) -> None:
        if not self._guide_dialog or not self._guide_dialog.winfo_exists():
            return
        try:
            # 确保主窗口和对话框都更新
            self.app.root.update_idletasks()
            self._guide_dialog.update_idletasks()

            root_x = self.app.root.winfo_rootx()
            root_y = self.app.root.winfo_rooty()
            root_w = self.app.root.winfo_width()
            root_h = self.app.root.winfo_height()
            screen_w = self.app.root.winfo_screenwidth()
            screen_h = self.app.root.winfo_screenheight()
        except tk.TclError:
            return

        # 如果主窗口尺寸无效，重试
        if root_w <= 1 or root_h <= 1:
            if attempt < self.GUIDE_DIALOG_RETRY_LIMIT:
                self.app.root.after(
                    self.GUIDE_DIALOG_RETRY_DELAY_MS,
                    lambda: self._position_guide_dialog(dialog_w, dialog_h, attempt + 1)
                )
            else:
                # 重试次数用尽，居中显示在屏幕上
                x = (screen_w - dialog_w) // 2
                y = (screen_h - dialog_h) // 2
                self._guide_dialog.geometry(f"{dialog_w}x{dialog_h}+{x}+{y}")
            return

        # 计算居中位置（相对于主窗口）
        x = root_x + (root_w - dialog_w) // 2
        y = root_y + (root_h - dialog_h) // 2

        # 确保不超出屏幕边界
        x = max(10, min(x, screen_w - dialog_w - 10))
        y = max(10, min(y, screen_h - dialog_h - 10))

        self._guide_dialog.geometry(f"{dialog_w}x{dialog_h}+{x}+{y}")

        # 确保对话框可见并置顶
        self._guide_dialog.lift()
        self._guide_dialog.focus_force()

    def _open_guide_dialog(self):
        self._guide_dialog = tk.Toplevel(self.app.root)
        self._guide_dialog.title("助理模式引导")
        self._guide_dialog.minsize(480, 280)
        self._guide_dialog.transient(self.app.root)

        # 设置对话框尺寸
        dialog_w, dialog_h = 520, 320
        self._guide_dialog.geometry(f"{dialog_w}x{dialog_h}")

        # 确保主窗口和对话框都已更新
        self.app.root.update_idletasks()
        self._guide_dialog.update_idletasks()

        # 延迟定位，确保窗口完全初始化
        self.app.root.after(50, lambda: self._position_guide_dialog(dialog_w, dialog_h))

        frame = ttk.Frame(self._guide_dialog, padding=12)
        frame.pack(fill="both", expand=True)

        self._guide_progress_var = tk.StringVar(value="")
        self._guide_title_var = tk.StringVar(value="")
        self._guide_body_var = tk.StringVar(value="")
        self._guide_test_var = tk.StringVar(value="")
        self._guide_status_var = tk.StringVar(value="")
        self._guide_flow_var = tk.StringVar(value="")

        ttk.Label(frame, textvariable=self._guide_progress_var, foreground="gray").pack(anchor="w")
        ttk.Label(frame, textvariable=self._guide_title_var, font=("TkDefaultFont", 12, "bold")).pack(anchor="w", pady=(4, 6))
        ttk.Label(frame, textvariable=self._guide_body_var, wraplength=480, justify=tk.LEFT).pack(anchor="w")
        ttk.Label(frame, textvariable=self._guide_test_var, wraplength=480, justify=tk.LEFT, foreground="gray").pack(anchor="w", pady=(6, 0))
        ttk.Label(frame, textvariable=self._guide_flow_var, wraplength=480, justify=tk.LEFT, foreground="gray").pack(anchor="w", pady=(4, 0))
        ttk.Label(frame, textvariable=self._guide_status_var, wraplength=480, justify=tk.LEFT, foreground="gray").pack(anchor="w", pady=(4, 0))

        btn_frame = ttk.Frame(frame)
        btn_frame.pack(fill="x", pady=(12, 0))
        self._guide_btn_prev = ttk.Button(btn_frame, text="上一步", command=self._guide_prev)
        self._guide_btn_prev.pack(side="left")
        ttk.Button(btn_frame, text="自检", command=self._run_guide_self_check).pack(side="left", padx=(8, 0))
        ttk.Button(btn_frame, text="流程总览", command=self._show_guide_flow_summary).pack(side="left", padx=(8, 0))
        self._guide_btn_next = ttk.Button(btn_frame, text="下一步", command=self._guide_next)
        self._guide_btn_next.pack(side="right")
        ttk.Button(btn_frame, text="暂停引导", command=self._guide_pause).pack(side="right", padx=(0, 8))
        ttk.Button(btn_frame, text="结束引导", command=lambda: self.close(reset_progress=True)).pack(side="right", padx=(0, 8))

        ttk.Label(
            frame,
            text="提示：关闭引导需在设置中手动关闭该开关。",
            foreground="gray"
        ).pack(anchor="w", pady=(10, 0))

        self._guide_dialog.protocol("WM_DELETE_WINDOW", self._guide_pause)
        self._guide_dialog.bind("<Escape>", lambda event: self._guide_exit(), add="+")

    def _show_guide_step(self, index):
        if not self._guide_mode_running:
            return

        self._guide_step_index = max(0, min(index, len(self._guide_steps) - 1))
        step = self._guide_steps[self._guide_step_index]

        # 切换到对应的标签页/模块
        self._switch_to_step_tab(step)

        total = len(self._guide_steps)
        self._guide_progress_var.set(f"步骤 {self._guide_step_index + 1} / {total}")
        self._guide_title_var.set(step.get("title", ""))
        self._guide_body_var.set(step.get("body", ""))
        test_text = step.get("test", "")
        self._guide_test_var.set(f"测试：{test_text}" if test_text else "")
        flow_text = step.get("flow", "")
        self._guide_flow_var.set(f"关系：{flow_text}" if flow_text else "")
        check_key = step.get("check_key")
        ok, message = self._run_guide_check_by_key(check_key, mark_progress=False)
        status_prefix = "状态：已完成" if ok else "状态：未完成"
        self._guide_status_var.set(f"{status_prefix}  {message}")

        if self._guide_step_index == 0:
            self._guide_btn_prev.configure(state=tk.DISABLED)
        else:
            self._guide_btn_prev.configure(state=tk.NORMAL)

        if self._guide_step_index >= total - 1:
            self._guide_btn_next.configure(text="完成")
        else:
            self._guide_btn_next.configure(text="下一步")

        self._persist_guide_step()

        # Show highlight for current step (delayed to allow UI update)
        self.app.root.after(100, lambda: self._show_highlight(step))

    def _switch_to_step_tab(self, step: dict) -> bool:
        """
        切换到步骤对应的标签页/模块

        Args:
            step: 引导步骤字典

        Returns:
            是否成功切换
        """
        tab_id = step.get("tab_id")
        if not tab_id:
            return False

        try:
            # 方法1: 直接使用 tab_id (可能是 Frame 或字符串路径)
            self.app.notebook.select(tab_id)
            self.app.root.update_idletasks()
            logger.debug(f"成功切换到标签页: {step.get('title')}")
            return True
        except tk.TclError as e:
            logger.warning(f"切换标签页失败 (方法1): {e}")

        # 方法2: 尝试通过 check_key 查找对应的 tab
        check_key = step.get("check_key")
        if check_key and check_key in self.app.tabs:
            try:
                tab_frame = self.app.tabs[check_key]
                self.app.notebook.select(tab_frame)
                self.app.root.update_idletasks()
                logger.debug(f"成功切换到标签页 (通过 check_key): {check_key}")
                return True
            except tk.TclError as e:
                logger.warning(f"切换标签页失败 (方法2): {e}")

        # 方法3: 尝试通过标题查找
        title = step.get("title", "")
        if title:
            try:
                for tab_path in self.app.notebook.tabs():
                    tab_text = self.app.notebook.tab(tab_path, "text").strip()
                    if title in tab_text or tab_text in title:
                        self.app.notebook.select(tab_path)
                        self.app.root.update_idletasks()
                        logger.debug(f"成功切换到标签页 (通过标题): {title}")
                        return True
            except tk.TclError as e:
                logger.warning(f"切换标签页失败 (方法3): {e}")

        logger.warning(f"无法切换到步骤对应的标签页: {step.get('title')}")
        return False

    def _persist_guide_step(self):
        self.app.config_manager.set("guide_mode_step", self._guide_step_index)
        self.app.config_manager.save()

    def _guide_pause(self):
        if not self._guide_mode_running:
            return
        self._persist_guide_step()
        self.close()

    def _run_guide_self_check(self):
        if not self._guide_mode_running:
            return

        step = self._guide_steps[self._guide_step_index]
        check_key = step.get("check_key")
        ok, message = self._run_guide_check_by_key(check_key)
        title = "自检通过" if ok else "自检提示"
        messagebox.showinfo(title, message, parent=self._guide_dialog)

    def _guide_next(self):
        if not self._guide_mode_running:
            return
        current_step = self._guide_steps[self._guide_step_index]
        check_key = current_step.get("check_key")
        if check_key:
            ok, message = self._run_guide_check_by_key(check_key, mark_progress=True)
            if not ok:
                if not messagebox.askyesno("未完成步骤", f"{message}\n\n仍要继续下一步吗？", parent=self._guide_dialog):
                    return
        if self._guide_step_index >= len(self._guide_steps) - 1:
            self.close(reset_progress=True)
            return
        self._show_guide_step(self._guide_step_index + 1)

    def _guide_prev(self):
        if not self._guide_mode_running:
            return
        self._show_guide_step(self._guide_step_index - 1)

    def _run_guide_check_by_key(self, check_key, mark_progress=True):
        if not check_key:
            return True, "当前步骤无需自检。"

        progress_key = self._get_guide_progress_key(check_key)

        if check_key == "welcome":
            return True, "引导已启动，可以继续下一步。"
        if check_key == "project_saved":
            ok, message = check_project_saved(self.app)
            if ok and mark_progress:
                self.mark_progress(check_key)
            return ok, message
        if check_key == "outline_added":
            ok, message = check_outline_added(self.app)
            if ok and mark_progress:
                self.mark_progress(check_key)
            return ok, message
        if check_key == "scene_written":
            ok, message = check_scene_written(self.app)
            if ok and mark_progress:
                self.mark_progress(check_key)
            return ok, message
        if check_key == "timeline_added":
            ok, message = check_timeline_added(self.app)
            if ok and mark_progress:
                self.mark_progress(check_key)
            return ok, message
        if check_key == "dual_timeline_added":
            ok, message = check_dual_timeline_added(self.app)
            if ok and mark_progress:
                self.mark_progress(check_key)
            return ok, message
        if check_key == "evidence_added":
            ok, message = check_evidence_added(self.app)
            if ok and mark_progress:
                self.mark_progress(check_key)
            return ok, message
        if check_key == "relationship_linked":
            ok, message = check_relationship_linked(self.app)
            if ok and mark_progress:
                self.mark_progress(check_key)
            return ok, message
        if check_key == "heartbeat_added":
            ok, message = check_heartbeat_added(self.app)
            if ok and mark_progress:
                self.mark_progress(check_key)
            return ok, message
        if check_key == "faction_added":
            ok, message = check_faction_added(self.app)
            if ok and mark_progress:
                self.mark_progress(check_key)
            return ok, message
        if check_key == "world_entry_added":
            ok, message = check_world_entry_added(self.app)
            if ok and mark_progress:
                self.mark_progress(check_key)
            return ok, message
        if check_key == "iceberg_entry_added":
            ok, message = check_iceberg_entry_added(self.app)
            if ok and mark_progress:
                self.mark_progress(check_key)
            return ok, message
        if check_key == "variable_added":
            ok, message = check_variable_added(self.app)
            if ok and mark_progress:
                self.mark_progress(check_key)
            return ok, message
        if check_key == "flowchart_linked":
            ok, message = check_flowchart_linked(self.app)
            if ok and mark_progress:
                self.mark_progress(check_key)
            return ok, message
        if check_key == "scene_time_set":
            ok, message = check_scene_time_set(self.app)
            if ok and mark_progress:
                self.mark_progress(check_key)
            return ok, message
        if check_key == "export_done":
            ok, message = check_export_done(self.app, progress_key)
            if ok and mark_progress:
                self.mark_progress(check_key)
            return ok, message
        if check_key == "close":
            return True, "可在设置中关闭助理模式引导。"

        attr_map = {
            "outline": "mindmap_controller",
            "script": "script_controller",
            "char_events": "char_event_table",
            "relationship": "relationship_controller",
            "evidence_board": "evidence_board",
            "timeline": "timeline_controller",
            "story_curve": "story_curve_controller",
            "swimlanes": "swimlane_view",
            "dual_timeline": "dual_timeline_controller",
            "kanban": "kanban_controller",
            "calendar": "calendar_controller",
            "wiki": "wiki_controller",
            "research": "research_controller",
            "reverse_engineering": "reverse_engineering_view",
            "analytics": "analytics_controller",
            "heartbeat": "heartbeat_controller",
            "alibi": "alibi_controller",
            "iceberg": "iceberg_controller",
            "faction": "faction_controller",
            "variable": "variable_controller",
            "flowchart": "flowchart_controller",
            "ideas": "idea_controller",
            "training": "training_controller",
            "chat": "chat_controller",
        }
        attr_name = attr_map.get(check_key)
        if not attr_name:
            return True, "当前模块已加载，可继续。"

        if hasattr(self.app, attr_name) and getattr(self.app, attr_name, None):
            return True, "模块已加载，可开始测试。"
        return False, "当前模块未启用或尚未加载，请确认项目类型与模块设置。"

    def _get_guide_flow_summary(self) -> str:
        type_key = self.app.project_manager.get_project_type()
        length_key = self.app.project_manager.get_project_length()
        enabled_tools = self.app.project_manager.get_enabled_tools()

        lines = ["核心流程：保存项目 → 大纲 → 场景 → 时间线 → 导出"]

        if "dual_timeline" in enabled_tools:
            lines.append("推理链：双轨时间线 ? 证据板 ? 不在场证明")
        if type_key == "Romance":
            lines.append("恋爱链：人物关系 → 心动追踪 → 情感曲线")
        if type_key == "SciFi":
            lines.append("阵营链：势力矩阵 ? 人物关系 → 冲突推进")
        if type_key == "Epic":
            lines.append("世界链：百科 → 冰山层级 → 设定深化")
        if type_key == "Galgame":
            lines.append("分支链：变量 → 条件分支 → 剧情流向")
        if type_key == "LightNovel":
            lines.append("设定链：百科 → 角色/设定 → 场景")

        return "\n".join(lines)

    def _show_guide_flow_summary(self):
        messagebox.showinfo("流程总览", self._get_guide_flow_summary(), parent=self._guide_dialog)

    # ========== Highlight System Methods ==========

    def _is_widget_ready(self, widget: tk.Widget) -> bool:
        try:
            if not widget.winfo_viewable():
                return False
            widget.update_idletasks()
            return widget.winfo_width() > 1 and widget.winfo_height() > 1
        except tk.TclError:
            return False

    def _get_highlight_target_widget(self, target_name: str) -> Optional[tk.Widget]:
        """
        Resolve a target name to an actual widget reference.

        Args:
            target_name: The name of the target to highlight

        Returns:
            The widget to highlight, or None if not found
        """
        if not target_name:
            return None

        # Map common target names to widget paths
        target_map = {
            # Main UI elements
            "notebook": getattr(self.app, "notebook", None),
            "menu_bar": getattr(self.app, "menu_bar", None),

            # Tab frames
            "outline_tab": self.app.tabs.get("outline"),
            "script_tab": self.app.tabs.get("script"),
            "timeline_tab": self.app.tabs.get("timeline"),
            "relationship_tab": self.app.tabs.get("relationship"),
            "evidence_tab": self.app.tabs.get("evidence_board"),
            "dual_timeline_tab": self.app.tabs.get("dual_timeline"),
            "kanban_tab": self.app.tabs.get("kanban"),
            "wiki_tab": self.app.tabs.get("wiki"),
            "research_tab": self.app.tabs.get("research"),
            "ideas_tab": self.app.tabs.get("ideas"),
            "chat_tab": self.app.tabs.get("chat"),

            # Specific components (if available)
            "mindmap_canvas": getattr(self.app, "mindmap_canvas", None),
            "script_editor": getattr(self.app, "script_editor", None),
            "timeline_canvas": getattr(self.app, "timeline_canvas", None),
        }

        widget = target_map.get(target_name)

        # Try to get from controller if not in map
        if widget is None and hasattr(self.app, f"{target_name}_controller"):
            controller = getattr(self.app, f"{target_name}_controller", None)
            if controller and hasattr(controller, "view"):
                widget = controller.view

        return widget

    def _show_highlight(self, step: dict, attempt: int = 0):
        """
        Show highlight overlay for the current step.

        Args:
            step: The current guide step dictionary
        """
        if not self._highlight_enabled:
            return

        target_name = step.get("highlight_target")
        if not target_name:
            self._hide_highlight()
            return

        widget = self._get_highlight_target_widget(target_name)
        if not widget:
            logger.debug(f"Highlight target not found: {target_name}")
            self._hide_highlight()
            return
        if not self._is_widget_ready(widget):
            self._hide_highlight()
            if attempt < self.HIGHLIGHT_RETRY_LIMIT:
                self.app.root.after(
                    self.HIGHLIGHT_RETRY_DELAY_MS,
                    lambda: self._show_highlight(step, attempt + 1)
                )
            return

        # Initialize highlight overlay if needed
        theme_manager = getattr(self.app, "theme_manager", None)
        if not self._highlight_overlay:
            self._highlight_overlay = HighlightOverlay(self.app.root, theme_manager)
            self._highlight_overlay.bind_escape(self._guide_exit)

        if target_name.endswith("_tab"):
            region_provider = self._make_tab_region_provider(target_name)
            if region_provider:
                region = region_provider()
                if region:
                    x, y, w, h = region
                    self._highlight_overlay.highlight_region(
                        x,
                        y,
                        w,
                        h,
                        animation=step.get("highlight_animation", "pulse"),
                        on_click_outside=self._on_highlight_click_outside,
                        region_provider=region_provider
                    )
                    return

        # Show highlight
        animation = step.get("highlight_animation", "pulse")
        self._highlight_overlay.highlight_widget(
            widget,
            animation=animation,
            on_click_outside=self._on_highlight_click_outside
        )
        self._bring_guide_dialog_to_front()

        # Show tooltip if configured
        tooltip_text = step.get("highlight_tooltip")
        if tooltip_text:
            self._show_guide_tooltip(widget, tooltip_text, step.get("tooltip_position", "bottom"))

    def _hide_highlight(self):
        """Hide the current highlight and tooltip."""
        if self._highlight_overlay:
            self._highlight_overlay.clear()

        if self._guide_tooltip:
            self._guide_tooltip.hide()

    def _show_guide_tooltip(self, widget: tk.Widget, text: str, position: str = "bottom"):
        """
        Show a tooltip near the highlighted widget.

        Args:
            widget: The widget to show tooltip near
            text: The tooltip text
            position: Position relative to widget
        """
        theme_manager = getattr(self.app, "theme_manager", None)

        if self._guide_tooltip:
            self._guide_tooltip.destroy()

        step = self._guide_steps[self._guide_step_index]
        self._guide_tooltip = GuideTooltip(
            self.app.root,
            theme_manager,
            text=text,
            title=step.get("title"),
            target_widget=widget,
            position=position,
            primary_button="下一步",
            on_primary=self._guide_next,
            on_close=self._hide_highlight
        )
        self._guide_tooltip.show()

    def _on_highlight_click_outside(self):
        """Handle click outside the highlighted area."""
        self._hide_highlight()

    def _bring_guide_dialog_to_front(self):
        if not self._guide_dialog:
            return
        try:
            self._guide_dialog.lift()
            self._guide_dialog.attributes("-topmost", True)
            self.app.root.after(200, lambda: self._guide_dialog.attributes("-topmost", False))
        except tk.TclError:
            pass

    def _make_tab_region_provider(self, target_name: str):
        notebook = getattr(self.app, "notebook", None)
        if not notebook or not target_name.endswith("_tab"):
            return None
        tab_key = target_name[:-4]
        tab_frame = self.app.tabs.get(tab_key)
        if not tab_frame:
            return None
        try:
            tab_index = notebook.index(tab_frame)
        except tk.TclError:
            return None

        def _provider():
            try:
                bbox = notebook.bbox(tab_index)
            except tk.TclError:
                return None
            if not bbox:
                return None
            x, y, w, h = bbox
            return (
                notebook.winfo_rootx() + x,
                notebook.winfo_rooty() + y,
                w,
                h
            )

        return _provider

    def _bind_escape_shortcut(self):
        if self._root_escape_bind_id:
            return
        self._root_escape_bind_id = self.app.root.bind(
            "<Escape>",
            lambda event: self._guide_exit(),
            add="+"
        )

    def _unbind_escape_shortcut(self):
        if not self._root_escape_bind_id:
            return
        try:
            self.app.root.unbind("<Escape>", self._root_escape_bind_id)
        except tk.TclError:
            pass
        self._root_escape_bind_id = None

    def _guide_exit(self):
        self.close(reset_progress=True)

    def toggle_highlight(self, enabled: bool = None):
        """
        Toggle the highlight system on/off.

        Args:
            enabled: If None, toggle. Otherwise set to the specified value.
        """
        if enabled is None:
            self._highlight_enabled = not self._highlight_enabled
        else:
            self._highlight_enabled = enabled

        if not self._highlight_enabled:
            self._hide_highlight()

    def cleanup(self):
        """Clean up all highlight resources."""
        self._hide_highlight()

        if self._highlight_overlay:
            self._highlight_overlay.destroy()
            self._highlight_overlay = None

        if self._guide_tooltip:
            self._guide_tooltip.destroy()
            self._guide_tooltip = None
