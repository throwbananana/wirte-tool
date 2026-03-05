# -*- coding: utf-8 -*-
"""
帮助管理器模块
提供集中管理的帮助内容、快捷键说明和上下文敏感帮助
"""

from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field


@dataclass
class HelpTopic:
    """帮助主题"""
    id: str
    title: str
    icon: str
    content: str
    keywords: List[str] = field(default_factory=list)


@dataclass
class ShortcutInfo:
    """快捷键信息"""
    key: str
    description: str
    category: str


class HelpManager:
    """帮助管理器 - 集中管理所有帮助内容"""

    VERSION = "1.0.2"
    APP_NAME = "写作助手 Writer Tool"

    # 应用信息
    APP_INFO = {
        "name": APP_NAME,
        "version": VERSION,
        "description": "一款专为作家设计的桌面写作工具，集成思维导图大纲、剧本写作、AI辅助等功能。",
        "author": "Writer Tool Team",
        "website": "https://github.com/writer-tool",
        "license": "MIT License",
        "copyright": "Copyright (c) 2024-2025",
        "tech_stack": [
            "Python 3.x",
            "Tkinter GUI",
            "SQLite 数据存储",
            "LM Studio / OpenAI API 集成"
        ],
        "features": [
            "思维导图式大纲管理",
            "多视图剧本写作",
            "AI 智能辅助创作",
            "角色关系图谱",
            "时间线管理",
            "证据板 (推理写作)",
            "多格式导出",
            "游戏化激励系统"
        ]
    }

    def __init__(self):
        self._topics: Dict[str, HelpTopic] = {}
        self._shortcuts: List[ShortcutInfo] = []
        self._context_help: Dict[str, str] = {}
        self._init_topics()
        self._init_shortcuts()
        self._init_context_help()

    def _init_topics(self):
        """初始化帮助主题"""
        topics = [
            HelpTopic(
                id="getting_started",
                title="快速入门",
                icon="rocket",
                content="""## 快速入门指南

### 第一步：创建项目
1. 点击菜单 **文件 → 新建项目** (Ctrl+N)
2. 系统会创建一个空白项目，包含基本的大纲结构

### 第二步：编写大纲
1. 切换到 **思维导图/大纲** 标签页
2. 双击节点编辑内容
3. 使用快捷键快速操作：
   - **Tab**: 添加子节点
   - **Enter**: 添加同级节点
   - **Delete**: 删除节点
   - **框选**: 多选节点

### 第三步：创建角色和场景
1. 切换到 **剧本写作** 标签页
2. 在左侧面板添加角色
3. 在中间区域创建和编辑场景

### 第四步：保存项目
- 按 **Ctrl+S** 保存
- 项目文件格式为 `.writerproj`

### 提示
- 使用 **F5** 刷新界面
- 使用 **F2** 打开 AI 助手悬浮窗
- 使用 **Ctrl+Z/Y** 撤销/重做""",
                keywords=["入门", "开始", "新建", "教程", "start", "begin"]
            ),
            HelpTopic(
                id="outline",
                title="思维导图/大纲",
                icon="diagram_tree",
                content="""## 思维导图/大纲功能

### 基本操作
| 操作 | 快捷键 | 说明 |
|------|--------|------|
| 编辑节点 | 双击 / F2 | 修改节点内容 |
| 添加子节点 | Tab | 在当前节点下创建子节点 |
| 添加同级节点 | Enter | 在当前节点后创建同级节点 |
| 删除节点 | Delete | 删除选中的节点 |
| 多选节点 | 框选 / Ctrl+点击 | 同时选中多个节点 |
| 展开/折叠 | 点击 +/- | 展开或折叠子节点 |

### 视图模式
系统提供多种大纲视图：
- **思维导图**: 传统放射状布局
- **树形图**: 垂直/水平树状结构
- **鱼骨图**: 因果分析布局
- **软木板**: 卡片式自由布局
- **表格视图**: 列表式浏览

### AI 辅助功能
- **AI 补全**: 选中节点后点击 AI 按钮自动补充内容
- **生成子节点**: 右键菜单 → AI 生成分支建议
- **大纲诊断**: 使用 AI 分析大纲结构问题

### 标签管理
- 为节点添加颜色标签进行分类
- 使用标签筛选快速定位相关内容""",
                keywords=["大纲", "思维导图", "节点", "outline", "mindmap", "树形"]
            ),
            HelpTopic(
                id="script",
                title="剧本写作",
                icon="document_text",
                content="""## 剧本写作功能

### 界面布局
- **左侧**: 角色列表和场景列表
- **中间**: 场景编辑区
- **右侧**: 世界观百科

### 角色管理
1. 点击 **添加角色** 按钮
2. 填写角色名称、描述、标签
3. 可添加角色头像和性格雷达图
4. 双击角色可编辑详情

### 场景编辑
- 每个场景包含：名称、地点、时间、内容
- 可关联大纲节点和角色
- 支持多种剧本格式语法高亮

### 写作模式
- **专注模式 (F10)**: 减少界面干扰
- **打字机模式 (F9)**: 当前行居中
- **沉浸模式 (F11)**: 全屏无干扰写作

### 聚焦级别
- **行聚焦** (Ctrl+Shift+1): 高亮当前行
- **句子聚焦** (Ctrl+Shift+2): 高亮当前句
- **段落聚焦** (Ctrl+Shift+3): 高亮当前段
- **对话聚焦** (Ctrl+Shift+4): 高亮对话内容

### AI 辅助
- 根据大纲自动生成场景
- 对话润色和风格调整
- 剧情连贯性检查""",
                keywords=["剧本", "写作", "场景", "角色", "script", "scene", "character"]
            ),
            HelpTopic(
                id="ai_features",
                title="AI 功能",
                icon="sparkle",
                content="""## AI 功能说明

### 配置 AI 服务
1. 打开 **设置 → 通用设置**
2. 配置 API 地址（默认 LM Studio: http://localhost:1234/v1/chat/completions）
3. 设置模型名称和 API Key（如需要）

### 主要 AI 功能

#### 大纲辅助
- **AI 生成思维导图**: 根据主题自动生成大纲结构
- **节点内容补全**: 选中节点后 AI 扩展内容
- **分支建议**: 右键生成可能的发展方向
- **大纲诊断**: 分析结构完整性

#### 剧本辅助
- **场景生成**: 根据大纲生成完整场景
- **对话生成**: 根据角色特点生成对话
- **内容润色**: 改善文字表达
- **风格转换**: 调整写作风格

#### 智能分析
- **角色一致性检查**: 检测角色行为是否前后一致
- **时间线校验**: 检查事件顺序是否合理
- **逻辑漏洞检测**: 发现剧情中的逻辑问题

### 悬浮助手 (F2)
- 随时呼出的 AI 对话窗口
- 可发送当前编辑内容获取建议
- 支持上下文对话

### 注意事项
- AI 功能需要本地 LM Studio 或在线 API
- 生成内容仅供参考，请人工审核
- 大量生成可能需要较长时间""",
                keywords=["AI", "人工智能", "LM Studio", "生成", "智能", "助手"]
            ),
            HelpTopic(
                id="timeline",
                title="时间线与证据板",
                icon="timeline",
                content="""## 时间线功能

### 基本时间线
- 按时间顺序展示场景和事件
- 支持拖拽调整顺序
- 可视化故事节奏

### 双时间线 (悬疑写作)
适用于推理/悬疑小说：
- **真相时间线**: 事件真实发生顺序
- **叙事时间线**: 读者了解的顺序

### 人物事件表
- 追踪每个角色的行动轨迹
- 检查角色不在场证明
- 发现时间线冲突

## 证据板

### 功能说明
专为推理写作设计：
- 创建线索/证据卡片
- 建立线索之间的关联
- 可视化推理链条

### 操作方法
1. 双击空白处添加证据
2. 拖拽连线建立关联
3. 右键编辑证据详情
4. 使用颜色区分证据类型

### 与时间线联动
- 证据可关联到时间线事件
- 自动检测时间逻辑冲突""",
                keywords=["时间线", "证据", "推理", "悬疑", "timeline", "evidence"]
            ),
            HelpTopic(
                id="relationship",
                title="角色关系图",
                icon="people_connection",
                content="""## 角色关系图

### 功能说明
可视化展示角色之间的关系网络。

### 基本操作
1. 角色会自动从剧本中加载
2. 拖拽调整角色位置
3. 点击两个角色之间的连线编辑关系
4. 右键菜单添加/删除关系

### 关系类型
可自定义关系类型和颜色：
- 家庭关系（父母、兄弟姐妹等）
- 社会关系（朋友、同事、对手等）
- 情感关系（恋人、暗恋等）

### 视图选项
- 调整节点大小
- 显示/隐藏关系标签
- 布局自动优化

### 导出
- 可导出为图片
- 可复制关系描述文本""",
                keywords=["关系", "角色", "人物", "关系图", "relationship"]
            ),
            HelpTopic(
                id="export",
                title="导出功能",
                icon="save",
                content="""## 导出功能

### 支持的格式

| 格式 | 说明 | 用途 |
|------|------|------|
| Markdown (.md) | 通用文本格式 | 博客、笔记 |
| HTML | 网页格式 | 预览、分享 |
| Word (.docx) | Office 文档 | 投稿、编辑 |
| PDF | 便携文档 | 打印、存档 |
| Fountain | 编剧格式 | 专业剧本 |
| Final Draft (.fdx) | 行业标准 | 影视制作 |
| Ren'Py | 视觉小说引擎 | 游戏开发 |
| CSV | 表格数据 | 数据分析 |

### 导出操作
1. 菜单 **文件 → 导出**
2. 选择目标格式
3. 选择保存位置
4. 确认导出选项

### 导出内容
- **完整项目**: 包含大纲、剧本、角色等全部内容
- **仅剧本**: 只导出场景文本
- **角色台词**: 导出指定角色的所有台词

### 注意事项
- Word 导出需要 python-docx 库
- PDF 导出需要 reportlab 库
- 部分格式可能不支持所有样式""",
                keywords=["导出", "export", "markdown", "word", "pdf", "html"]
            ),
            HelpTopic(
                id="gamification",
                title="游戏化激励",
                icon="trophy",
                content="""## 游戏化激励系统

### 经验值 (XP)
通过写作活动获得经验值：
- 每写 100 字获得 10 XP
- 完成场景获得 50 XP
- 达成写作目标获得额外奖励

### 等级系统
- 积累 XP 提升等级
- 等级显示在界面右上角
- 更高等级解锁成就

### 成就系统
点击 **生涯 → 我的成就** 查看：
- 写作里程碑成就
- 功能探索成就
- 坚持写作成就

### 番茄钟
内置番茄工作法计时器：
- 25 分钟工作 + 5 分钟休息
- 点击计时器区域操作
- 完成番茄获得 XP

### 写作冲刺
限时写作挑战：
- 设定时间和字数目标
- 专注模式下进行
- 完成获得额外奖励

### 每日目标
- 设定每日字数目标
- 进度条显示完成情况
- 达成目标获得成就""",
                keywords=["游戏", "成就", "等级", "XP", "番茄钟", "目标"]
            ),
            HelpTopic(
                id="settings",
                title="设置与配置",
                icon="settings",
                content="""## 设置与配置

### 通用设置
菜单 **设置 → 通用设置** 打开：

#### AI 配置
- API 地址: LM Studio 或 OpenAI 兼容 API
- 模型名称: 使用的模型标识
- API Key: 认证密钥（如需要）

#### 界面设置
- 主题切换: 明亮/暗色模式
- 自定义主题色
- 背景图片设置

#### 编辑器设置
- 字体和字号
- 行间距
- 自动保存间隔

### 项目设置
菜单 **文件 → 项目设置**：
- 项目类型（小说、剧本等）
- 项目长度（短篇、中篇、长篇）
- 启用的工具模块

### 配置文件位置
`%USERPROFILE%\\.writer_tool\\config.json`

### 数据目录
`writer_data/` 包含：
- 自动备份
- 日志文件
- 环境音文件 (sounds/)
- 自定义资源""",
                keywords=["设置", "配置", "主题", "settings", "config"]
            ),
            HelpTopic(
                id="troubleshooting",
                title="常见问题",
                icon="question_circle",
                content="""## 常见问题解答

### AI 功能无法使用
**问题**: 点击 AI 按钮无反应或报错
**解决**:
1. 确认 LM Studio 已启动并加载模型
2. 检查设置中 API 地址是否正确
3. 查看日志文件排查错误

### 界面显示异常
**问题**: 字体显示为方块或乱码
**解决**:
1. 安装中文字体（如思源黑体）
2. 重启应用程序

### 无法保存项目
**问题**: 保存时提示错误
**解决**:
1. 检查目标路径是否有写入权限
2. 确认磁盘空间充足
3. 尝试另存为其他位置

### 撤销不生效
**问题**: Ctrl+Z 无法撤销操作
**解决**:
1. 确认焦点在正确的编辑区域
2. 部分操作可能不支持撤销
3. 尝试使用 **编辑 → 撤销** 菜单

### 导出失败
**问题**: 导出某些格式失败
**解决**:
1. Word 导出需要: `pip install python-docx`
2. PDF 导出需要: `pip install reportlab`
3. 检查目标路径权限

### 性能问题
**问题**: 大项目卡顿
**解决**:
1. 减少同时打开的视图数量
2. 关闭不需要的 AI 功能
3. 定期保存并重启应用

### 获取更多帮助
- 查看日志: `writer_data/writer_tool.log`
- 提交问题: GitHub Issues""",
                keywords=["问题", "错误", "帮助", "FAQ", "troubleshoot"]
            ),
        ]

        for topic in topics:
            self._topics[topic.id] = topic

    def _init_shortcuts(self):
        """初始化快捷键列表"""
        self._shortcuts = [
            # 文件操作
            ShortcutInfo("Ctrl+N", "新建项目", "文件"),
            ShortcutInfo("Ctrl+O", "打开项目", "文件"),
            ShortcutInfo("Ctrl+S", "保存项目", "文件"),
            ShortcutInfo("Ctrl+Shift+S", "另存为", "文件"),

            # 编辑操作
            ShortcutInfo("Ctrl+Z", "撤销", "编辑"),
            ShortcutInfo("Ctrl+Y", "重做", "编辑"),
            ShortcutInfo("Ctrl+F", "查找", "编辑"),
            ShortcutInfo("Ctrl+H", "替换", "编辑"),
            ShortcutInfo("Ctrl+A", "全选", "编辑"),
            ShortcutInfo("Ctrl+C", "复制", "编辑"),
            ShortcutInfo("Ctrl+V", "粘贴", "编辑"),
            ShortcutInfo("Ctrl+X", "剪切", "编辑"),

            # 大纲操作
            ShortcutInfo("Tab", "添加子节点", "大纲"),
            ShortcutInfo("Enter", "添加同级节点", "大纲"),
            ShortcutInfo("Delete", "删除节点", "大纲"),
            ShortcutInfo("F2", "编辑节点", "大纲"),
            ShortcutInfo("Ctrl+点击", "多选节点", "大纲"),
            ShortcutInfo("框选", "区域多选", "大纲"),

            # 帮助
            ShortcutInfo("F1", "打开帮助", "帮助"),
            ShortcutInfo("Ctrl+/", "快捷键速查", "帮助"),

            # 视图操作
            ShortcutInfo("F5", "刷新界面", "视图"),
            ShortcutInfo("F2", "AI 助手悬浮窗", "视图"),
            ShortcutInfo("F9", "打字机模式", "视图"),
            ShortcutInfo("F10", "专注模式", "视图"),
            ShortcutInfo("F11", "沉浸模式", "视图"),
            ShortcutInfo("Escape", "退出当前模式", "视图"),
            ShortcutInfo("Ctrl+Tab", "下一个标签页", "视图"),
            ShortcutInfo("Ctrl+Shift+Tab", "上一个标签页", "视图"),
            ShortcutInfo("Alt+1~9", "切换到指定标签页", "视图"),

            # 专注模式
            ShortcutInfo("Ctrl+Shift+1", "行聚焦", "专注"),
            ShortcutInfo("Ctrl+Shift+2", "句子聚焦", "专注"),
            ShortcutInfo("Ctrl+Shift+3", "段落聚焦", "专注"),
            ShortcutInfo("Ctrl+Shift+4", "对话聚焦", "专注"),
            ShortcutInfo("Ctrl+Shift+F", "切换聚焦级别", "专注"),
        ]

    def _init_context_help(self):
        """初始化上下文帮助"""
        self._context_help = {
            "outline": "思维导图/大纲: 双击编辑 | Tab添加子节点 | Enter添加同级 | Delete删除 | 框选多选",
            "script": "剧本写作: 左侧管理角色和场景 | 中间编辑内容 | 右侧查看世界观百科",
            "timeline": "时间线: 拖拽调整顺序 | 双击编辑事件 | 右键添加新事件",
            "kanban": "看板: 拖拽移动场景卡片 | 双击编辑 | 自定义列状态",
            "relationship": "关系图: 拖拽调整位置 | 点击连线编辑关系 | 右键添加关系",
            "evidence": "证据板: 双击添加证据 | 拖拽连线关联 | 右键编辑详情",
            "calendar": "日历视图: 点击日期查看事件 | 拖拽移动事件",
            "analytics": "数据分析: 查看写作统计 | 分析角色出场 | 词频分析",
            "wiki": "世界观百科: 管理设定资料 | 分类整理 | 快速引用",
            "training": "写作训练: AI 辅助练习 | 挑战模式 | 记录进步",
            "dual_timeline": "双时间线: 上方真相时间线 | 下方叙事时间线 | 拖拽调整事件",
            "char_events": "人物事件: 追踪角色行动 | 检查不在场证明 | 发现时间冲突",
            "swimlanes": "泳道视图: 按角色/地点分组 | 拖拽调整 | 可视化故事线",
            "flowchart": "流程图: 场景流转可视化 | 拖拽编辑 | 分支管理",
            "research": "研究面板: 记录参考资料 | 分类整理 | 快速查阅",
            "ideas": "灵感收集: 随时记录想法 | 标签分类 | 转化为内容",
            "assets": "资产管理: 管理角色立绘 | 背景图片 | 音效资源",
            "iceberg": "世界观冰山: 显性/隐性设定 | 层级展示 | 深度构建",
            "factions": "势力矩阵: 势力关系 | 阵营分布 | 冲突可视化",
            "story_curve": "故事曲线: 张力变化 | 情感节奏 | 节点编辑",
            "beat_sheet": "节拍表: 故事节拍 | 结构模板 | 节奏把控",
        }

    def _init_module_help(self):
        """初始化模块详细帮助"""
        self._module_help = {
            "outline": {
                "title": "思维导图/大纲",
                "icon": "diagram",
                "quick_tips": [
                    "双击节点编辑内容",
                    "Tab 添加子节点",
                    "Enter 添加同级节点",
                    "Delete 删除节点",
                    "框选或 Ctrl+点击 多选",
                    "右键菜单查看更多操作",
                ],
                "features": [
                    ("视图切换", "点击工具栏按钮切换不同的大纲视图"),
                    ("AI 补全", "选中节点后点击 AI 按钮自动扩展"),
                    ("标签管理", "为节点添加颜色标签分类"),
                    ("导出大纲", "导出为 Markdown 或其他格式"),
                ],
                "topic_id": "outline"
            },
            "script": {
                "title": "剧本写作",
                "icon": "document",
                "quick_tips": [
                    "左侧面板管理角色和场景",
                    "中间区域编辑场景内容",
                    "F9 打字机模式 / F10 专注模式",
                    "F11 沉浸模式（全屏写作）",
                    "Ctrl+Shift+1~4 切换聚焦级别",
                ],
                "features": [
                    ("角色管理", "添加、编辑角色及其属性"),
                    ("场景编辑", "创建和组织故事场景"),
                    ("世界观百科", "右侧查看和管理设定"),
                    ("AI 辅助", "生成对话、润色内容"),
                ],
                "topic_id": "script"
            },
            "timeline": {
                "title": "时间线",
                "icon": "timeline",
                "quick_tips": [
                    "拖拽调整事件顺序",
                    "双击编辑事件详情",
                    "右键添加新事件",
                    "缩放查看不同时间范围",
                ],
                "features": [
                    ("事件管理", "添加、编辑、删除事件"),
                    ("时间轴缩放", "调整显示的时间范围"),
                    ("关联场景", "将事件与场景关联"),
                ],
                "topic_id": "timeline"
            },
            "kanban": {
                "title": "看板",
                "icon": "board",
                "quick_tips": [
                    "拖拽卡片在列之间移动",
                    "双击卡片编辑内容",
                    "自定义列名和颜色",
                    "使用标签筛选卡片",
                ],
                "features": [
                    ("状态管理", "通过列表示场景状态"),
                    ("拖拽排序", "直观调整场景顺序"),
                    ("颜色标记", "为卡片添加颜色标识"),
                ],
                "topic_id": "script"
            },
            "relationship": {
                "title": "角色关系图",
                "icon": "people",
                "quick_tips": [
                    "拖拽调整角色位置",
                    "点击连线编辑关系",
                    "右键添加/删除关系",
                    "双击角色查看详情",
                ],
                "features": [
                    ("关系可视化", "直观展示人物关系网络"),
                    ("关系编辑", "定义关系类型和描述"),
                    ("布局优化", "自动或手动调整布局"),
                    ("导出图片", "导出关系图为图片"),
                ],
                "topic_id": "relationship"
            },
            "evidence": {
                "title": "证据板",
                "icon": "clue",
                "quick_tips": [
                    "双击空白处添加证据",
                    "拖拽连线关联证据",
                    "右键编辑证据详情",
                    "颜色区分证据类型",
                ],
                "features": [
                    ("线索管理", "创建和组织推理线索"),
                    ("关联可视化", "展示线索之间的联系"),
                    ("时间线关联", "与时间线事件联动"),
                ],
                "topic_id": "timeline"
            },
            "dual_timeline": {
                "title": "双时间线",
                "icon": "dual_timeline",
                "quick_tips": [
                    "上方是真相时间线（事实顺序）",
                    "下方是叙事时间线（读者视角）",
                    "拖拽调整事件顺序",
                    "双击编辑事件内容",
                ],
                "features": [
                    ("真相时间线", "事件实际发生的顺序"),
                    ("叙事时间线", "读者了解信息的顺序"),
                    ("对比分析", "发现叙事与真相的差异"),
                ],
                "topic_id": "timeline"
            },
            "calendar": {
                "title": "日历视图",
                "icon": "calendar",
                "quick_tips": [
                    "点击日期查看当天事件",
                    "拖拽事件到其他日期",
                    "双击创建新事件",
                ],
                "features": [
                    ("月视图", "按月查看事件分布"),
                    ("事件标记", "在日历上标记重要事件"),
                    ("快速导航", "快速跳转到指定日期"),
                ],
                "topic_id": "timeline"
            },
            "analytics": {
                "title": "数据分析",
                "icon": "chart",
                "quick_tips": [
                    "查看写作字数统计",
                    "分析角色出场频率",
                    "查看词频分布",
                ],
                "features": [
                    ("字数统计", "查看总字数和分布"),
                    ("角色分析", "分析角色出场情况"),
                    ("词频分析", "查看高频词汇"),
                    ("进度追踪", "监控写作进度"),
                ],
                "topic_id": "settings"
            },
            "wiki": {
                "title": "世界观百科",
                "icon": "book",
                "quick_tips": [
                    "分类管理设定资料",
                    "支持富文本编辑",
                    "可在剧本中快速引用",
                ],
                "features": [
                    ("分类管理", "按类型组织设定"),
                    ("快速搜索", "搜索设定内容"),
                    ("关联引用", "在剧本中引用设定"),
                ],
                "topic_id": "script"
            },
            "training": {
                "title": "写作训练",
                "icon": "training",
                "quick_tips": [
                    "选择训练主题开始练习",
                    "AI 提供写作建议",
                    "记录训练历史和进步",
                ],
                "features": [
                    ("AI 辅助训练", "根据提示进行写作练习"),
                    ("挑战模式", "限时写作挑战"),
                    ("进步追踪", "记录训练成果"),
                ],
                "topic_id": "ai_features"
            },
            "research": {
                "title": "研究面板",
                "icon": "research",
                "quick_tips": [
                    "记录参考资料和笔记",
                    "按标签分类整理",
                    "支持链接和图片",
                ],
                "features": [
                    ("资料收集", "保存研究资料"),
                    ("分类整理", "按主题组织"),
                    ("快速查阅", "写作时快速参考"),
                ],
                "topic_id": "script"
            },
            "ideas": {
                "title": "灵感收集",
                "icon": "lightbulb",
                "quick_tips": [
                    "随时记录灵感和想法",
                    "使用标签分类",
                    "可转化为大纲或场景",
                ],
                "features": [
                    ("快速记录", "随时捕捉灵感"),
                    ("标签管理", "分类和筛选想法"),
                    ("内容转化", "将想法融入作品"),
                ],
                "topic_id": "getting_started"
            },
            "assets": {
                "title": "资产管理",
                "icon": "image",
                "quick_tips": [
                    "管理角色立绘和头像",
                    "组织背景图片素材",
                    "预览和编辑资产",
                ],
                "features": [
                    ("立绘管理", "管理角色视觉素材"),
                    ("背景素材", "组织场景背景图"),
                    ("资产预览", "快速预览素材"),
                ],
                "topic_id": "export"
            },
        }

    def get_module_help(self, module_id: str) -> Optional[dict]:
        """获取模块详细帮助"""
        if not hasattr(self, '_module_help'):
            self._init_module_help()
        return self._module_help.get(module_id)

    def get_all_module_help(self) -> Dict[str, dict]:
        """获取所有模块帮助"""
        if not hasattr(self, '_module_help'):
            self._init_module_help()
        return self._module_help.copy()

    def get_topic(self, topic_id: str) -> Optional[HelpTopic]:
        """获取帮助主题"""
        return self._topics.get(topic_id)

    def get_all_topics(self) -> List[HelpTopic]:
        """获取所有帮助主题"""
        return list(self._topics.values())

    def search_topics(self, query: str) -> List[HelpTopic]:
        """搜索帮助主题"""
        query = query.lower()
        results = []
        for topic in self._topics.values():
            if (query in topic.title.lower() or
                query in topic.content.lower() or
                any(query in kw.lower() for kw in topic.keywords)):
                results.append(topic)
        return results

    def get_shortcuts(self, category: Optional[str] = None) -> List[ShortcutInfo]:
        """获取快捷键列表"""
        if category:
            return [s for s in self._shortcuts if s.category == category]
        return self._shortcuts

    def get_shortcut_categories(self) -> List[str]:
        """获取快捷键分类列表"""
        return list(set(s.category for s in self._shortcuts))

    def get_context_help(self, context: str) -> str:
        """获取上下文帮助"""
        return self._context_help.get(context, "")

    def get_app_info(self) -> dict:
        """获取应用信息"""
        return self.APP_INFO.copy()

    def format_shortcuts_text(self) -> str:
        """格式化快捷键为文本"""
        lines = ["## 快捷键速查\n"]
        current_category = ""
        for shortcut in self._shortcuts:
            if shortcut.category != current_category:
                current_category = shortcut.category
                lines.append(f"\n### {current_category}\n")
            lines.append(f"- **{shortcut.key}**: {shortcut.description}")
        return "\n".join(lines)


# 单例模式
_help_manager_instance: Optional[HelpManager] = None

def get_help_manager() -> HelpManager:
    """获取帮助管理器单例"""
    global _help_manager_instance
    if _help_manager_instance is None:
        _help_manager_instance = HelpManager()
    return _help_manager_instance
