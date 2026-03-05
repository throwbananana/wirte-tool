# Writer Tool - 功能补全与完善实施计划

基于代码库现状分析，本项目在“导出功能”、“沉浸体验”和“数据关联”方面有较大的提升空间。以下是针对未完成模块的详细技术实施方案。

## 1. 导出模块增强 (Exporter Module)

目前仅支持基础文本和网页导出。为了满足专业编剧和统筹管理的需求，需要增加 CSV/Excel 数据表格导出和分角色台词本。

### 1.1 项目数据表格导出 (CSV/Excel)
**目标**: 将大纲和场景列表导出为表格，方便使用 Excel 进行场次管理和进度统筹。
**文件**: `writer_app/core/exporter.py`
**实现逻辑**:
- 使用 Python 标准库 `csv`。
- **导出内容**:
    - **场景表**: 序号, 场景名, 地点, 时间, 字数, 登场角色, 备注。
    - **角色表**: 姓名, 标签, 登场场次统计, 首次登场。
    - **大纲表**: 节点层级, 标题, 内容摘要, 关联场景数。

### 1.2 分角色台词本 (Character Sides)
**目标**: 导出特定角色的专属剧本，仅包含该角色的台词及其上下文（前一句/后一句提示），用于演员背词或配音。
**文件**: `writer_app/core/exporter.py`
**实现逻辑**:
- 遍历所有场景内容。
- 解析标准剧本格式（`Name: Dialogue` 或 `【Name】 Dialogue`）。
- 提取目标角色的台词块。
- 保留“提示词”（Cue）——即上一句其他人的台词作为衔接。
- 生成格式：
    > **SCENE 1 - CAFE**
    >
    > (Bob says: ...how are you?)
    > **ALICE**: I'm fine, thanks.
    > (Bob says: Good.)

## 2. 沉浸与生产力 (Zen & Productivity)

### 2.1 氛围白噪音 (Ambiance Player)
**目标**: 实装 Zen Mode 中的背景白噪音功能。
**文件**: `writer_app/main.py` (或新建 `writer_app/core/audio.py`)
**技术选型**: 
- 推荐使用 `pygame` (需添加到 requirements.txt)，因为它支持混音（同时播放雨声+打字音效）。
- 备选方案: `winsound` (仅限 Windows, 单音轨)。
**实现逻辑**:
- `toggle(sound_type)`: 切换声音文件（雨声、咖啡馆、图书馆）。
- `set_volume(0.0-1.0)`: 音量控制。
- 资源文件需放置在 `writer_data/sounds/` 下。

### 2.2 写作冲刺 (Word Sprints)
**目标**: 区别于番茄钟，这是一个强调“短时间高产出”的游戏化模式。
**文件**: 新建 `writer_app/ui/sprint_dialog.py`
**UI设计**:
- 输入时长（如 15分钟）。
- 显示倒计时和实时字数增长。
- 结束时弹出结算界面：“本次冲刺 15 分钟，完成 500 字，效率 2000字/小时！获得 50 经验值！”
- 屏蔽其他干扰（强制置顶或全屏）。

## 3. 深度关联分析 (Relationship Analysis)

### 3.1 关系-场景反向查询
**目标**: 在人物关系图中，点击“连线”不仅仅是看属性，还能直接跳转到这两个人**同时出现**的场景。
**文件**: 
- `writer_app/core/models.py`: 增加 `get_scenes_with_character_pair(char_a, char_b)` 方法。
- `writer_app/ui/relationship_map.py`: 更新 `LinkDialog` 或右键菜单。
**实现逻辑**:
- 遍历场景，检查 `scene.characters` 列表是否同时包含 A 和 B。
- 返回场景列表供用户跳转。

---

## 优先级建议

1.  **Phase 1 (高价值/低风险)**: 实现 **CSV导出** 和 **分角色台词本**。这纯粹是逻辑扩展，不涉及UI大改。
2.  **Phase 2 (交互增强)**: 实现 **关系-场景反向查询**。这能极大增强现有关系图的实用性。
3.  **Phase 3 (依赖引入)**: 引入 `pygame` 并实现 **氛围音效** 和 **写作冲刺**。

是否开始执行 Phase 1？
