# `throwbananana/wirte-tool` 项目分析与重构建议汇总

> 目标：把此前对该仓库的所有分析、判断和改造建议，整理为一份可直接阅读、归档和排期的 Markdown 文档。

---

## 1. 项目总体判断

### 1.1 一句话结论

这个项目不是一个“小写作工具”，而是一个 **本地优先、按题材装配、多模块协作的创作工作台**。  
它已经明显超出了“文本编辑器 + 导出”的范围，更接近一个面向小说 / 剧本 / 悬疑 / Galgame 的 **创作 IDE**。

### 1.2 当前成熟度判断

我对它的综合评价是：

- **功能完成度：中高**
- **架构完成度：中**
- **产品化完成度：偏低**

### 1.3 为什么这样判断

好的地方：

- 已经具备完整的桌面应用能力：配置、主题、导出、AI、本地语音、托盘、音效、专注模式、资源管理等。
- 已经出现平台化结构：`core / controllers / ui / utils`。
- 已经引入了模块注册表、事件总线、类型化数据、导出插件系统。
- 已经不是“只有一个主编辑器”的工具，而是题材驱动、可配置的创作工作台。

主要短板：

- `writer_app/main.py` 仍然过重，是典型的 God Object。
- `ProjectManager` 职责过宽，领域边界不清。
- `project_types / module_registry / typed_data` 三处都在参与“启用什么”的定义，存在多真相源问题。
- `exporter.py` 同时维护新旧两套导出组织方式。
- 工程收尾不够：依赖、文档、仓库整理、README、安装说明都偏弱。

---

## 2. 项目在做什么

从现有代码看，它本质上是一个 **Tkinter 桌面写作平台**，不是单一写作器。

### 2.1 主体能力

当前项目已覆盖这些核心方向：

- 大纲 / 思维导图
- 场景写作 / 剧本编辑
- 人物管理 / 人物事件
- 时间轴 / 双轨时间线
- 人物关系图 / 线索墙 / 势力矩阵
- 世界观百科 / 资料搜集 / 灵感箱
- 统计分析 / 看板 / 日历
- AI 辅助创作 / 逻辑检查 / 动机分析 / 张力分析
- TTS 朗读 / 语音相关能力
- 多格式导出（Markdown / PDF / Fountain / FDX / DOCX / Ren'Py 等）
- Galgame 分支变量 / 资源管理 / 流程图
- 独立资源编辑器

### 2.2 产品定位倾向

从模块设计上看，它已经不是面向“泛写作”那么简单，而是更明显地偏向以下细分方向：

- **悬疑 / 推理**
- **恋爱 / 言情**
- **奇幻 / 史诗**
- **科幻 / 阵营冲突**
- **轻小说**
- **Galgame / 视觉小说**

---

## 3. 当前架构结构图

下面是对当前代码结构的抽象图。

```text
start_app.py
└─ WriterTool (writer_app/main.py)
   ├─ 基础设施层
   │  ├─ ConfigManager              配置持久化
   │  ├─ ThemeManager/AppTheme      主题与外观
   │  ├─ EventBus                   事件发布/订阅
   │  ├─ CommandHistory             撤销/重做
   │  ├─ BackupManager              自动备份
   │  ├─ ThreadPool                 AI任务线程池
   │  ├─ TrayManager                系统托盘
   │  ├─ Audio                      环境音/打字音
   │  └─ Logging / Font / Icon      日志、字体、图标
   │
   ├─ 领域层（core）
   │  ├─ ProjectManager             项目总数据模型
   │  ├─ typed_data                 数据模块定义
   │  ├─ project_types              项目类型与题材装配
   │  ├─ module_registry            模块注册信息
   │  ├─ exporter                   导出插件系统
   │  └─ validators / logic check   校验、迁移、逻辑检查
   │
   ├─ AI层
   │  ├─ AIClient                   OpenAI兼容/LM Studio接口
   │  └─ AIController               UI侧AI流程协调
   │
   ├─ 控制器层（controllers）
   │  ├─ ScriptController
   │  ├─ MindMapController
   │  ├─ WikiController
   │  ├─ Timeline/Calendar/Kanban
   │  ├─ Relationship/DualTimeline
   │  ├─ Training/Chat/Research
   │  └─ ... 由 ControllerRegistry 统一注册/刷新
   │
   ├─ 视图层（ui）
   │  ├─ Sidebar + Notebook
   │  ├─ Editor / Dialog / Panel / Canvas
   │  ├─ Evidence Board / Flowchart / StoryCurve
   │  ├─ Floating Assistant
   │  └─ Focus / Zen / Sprint 等体验组件
   │
   └─ 独立子应用
      └─ AssetEditorApp (asset_editor_main.py)
         ├─ GalgameAssetsController
         └─ EventEditorPanel
```

---

## 4. 数据模块视角

项目在数据层已经开始走 **模块化 schema** 的路线。

### 4.1 主要数据模块

按当前代码抽象，大致包含：

- `OUTLINE`
- `SCRIPT`
- `WORLD`
- `RELATIONSHIPS`
- `TAGS`
- `RESEARCH`
- `IDEAS`
- `TIMELINES`
- `FACTIONS`
- `VARIABLES`
- `GALGAME_ASSETS`
- `HEARTBEAT`
- `EVIDENCE`

### 4.2 当前优点

这说明作者已经不满足于“一份自由 JSON”，而是在尝试建立：

- 题材与数据模块解耦
- 模块按需启用
- 模块迁移 / 归档 / 恢复
- 类型化 schema 和默认结构

这是项目后续可扩展性的地基，建议保留并继续强化。

---

## 5. 项目类型系统的意义

当前项目类型系统已经具备“按题材装配工作台”的雏形。

### 5.1 它已经支持什么

内置项目类型包括：

- `General`
- `Suspense`
- `Romance`
- `Epic`
- `SciFi`
- `Poetry`
- `LightNovel`
- `Galgame`
- `Custom`

### 5.2 每种类型都能影响什么

- 推荐模块
- 默认 tab
- wiki 分类
- 资源类型
- 默认大纲视图
- AI 提示倾向

### 5.3 我的判断

这是这个项目最有潜力成为“产品差异化”的部分。  
很多写作工具只做一个统一工作台，而这个项目已经开始做“题材驱动工作台”，这是值得继续押注的方向。

---

## 6. 当前最值得肯定的设计

下面这些设计是我明确建议保留并继续深化的：

### 6.1 类型化项目数据

这是项目未来可扩展的基础，不要回退到随意拼 JSON。

### 6.2 `ControllerRegistry`

它已经开始承担统一注册、按分组刷新、按能力批量调用、统一清理的职责。方向是对的，应该进一步成为 UI 装配核心。

### 6.3 `BaseController.cleanup()`

生命周期追踪、事件解绑、listener 清理、`after()` 安全取消，这些基础设施已经做得不错。

### 6.4 事件总线

`EventBus` 规模已经足够平台化，不应该再退回 controller 之间互相硬调用。

### 6.5 导出插件体系

`ExporterRegistry + ExportFormat` 比零散导出函数更适合长期维护，也更适合继续扩格式。

---

## 7. 当前主要技术债清单

下面是当前最核心的技术债。

### 7.1 `main.py` 仍然是 God Object

它同时处理：

- 启动
- 配置
- 主题
- 菜单
- 快捷键
- 模块装配
- AI 状态
- 事件订阅
- 导出
- 导航
- 关闭流程

这是整个项目维护成本最高的点。

### 7.2 `ProjectManager` 职责过宽

它不只是持久化层，还在承担：

- 大纲导航
- 场景与大纲双向链接
- 角色事件
- wiki 同步
- 势力矩阵
- 变量管理
- 灵感
- 研究资料
- Galgame 资源
- 搜索
- 自动生成关系

领域边界明显过宽。

### 7.3 多真相源问题

目前至少有三处共同参与了“启用什么”的事实定义：

- `project_types.py`
- `module_registry.py`
- `typed_data.py`

这在长期必然导致漂移。

### 7.4 导出层双轨维护

`exporter.py` 一边有插件式导出器，一边保留大体重复的兼容层 `Exporter`。  
这种结构短期兼容，长期维护成本高。

### 7.5 控制器膨胀

`ScriptController` 本身已经是一个“小系统”：

- 角色
- 场景
- 编辑器
- AI
- TTS
- 快照
- Galgame 分支
- 流程图
- 资源预加载
- 时间轴同步

后面其他复杂 controller 也有走向类似问题的风险。

### 7.6 配置对象扁平化过度

`ConfigManager` 里一个大字典混合了：

- AI
- UI
- 窗口
- 悬浮助手
- 专注模式
- 天气
- 托盘
- 项目
- 教程
- 反推导参数

后续迁移和维护会越来越难。

### 7.7 事件规模增长但治理不足

`EventBus` 事件主题很多，说明系统规模上来了。  
但还没看到更高层的事件边界、调试工具、命名规范和订阅约束。

### 7.8 依赖声明与功能实现未完全对齐

导出器里使用的第三方依赖并没有都在依赖清单中得到清楚声明。  
这会导致“功能写了，但用户一用才报缺库”。

### 7.9 文档与代码有脱节迹象

一些计划文档和当前已实现功能不完全一致，说明演进中存在文档滞后。

### 7.10 仓库产品化包装不足

从公开仓库角度看，当前项目没有把它“是什么、适合谁、怎么跑、哪些功能稳定”表达清楚。  
这会降低协作和传播效率。

---

## 8. 重构优先级建议

### P0：必须先做

#### 8.1 拆 `main.py`

目标：把入口从“总控上帝类”拆成：

- `AppShell`
- `Bootstrap`
- `WorkspaceBuilder`

这是收益最大的改造。

#### 8.2 统一模块真相源

把“题材推荐什么”、“模块是什么”、“需要哪些数据模块”明确分工，不要再三处交叉定义。

#### 8.3 拆 `commands.py`

先按领域拆文件，不改行为。  
这一步风险相对可控，但可读性会明显提升。

#### 8.4 修明显 bug

例如 `ScriptController.edit_character()` 里定义了 `command`，执行时却调用 `cmd`，这里属于直接的功能错误。

---

### P1：第二阶段做

#### 8.5 拆 `ProjectManager`

把它变成 façade + 多服务组合，而不是所有领域方法都塞进一个类。

#### 8.6 拆大控制器

先拆 `ScriptController`，以后其他复杂 controller 可沿同样模式处理。

#### 8.7 规范事件系统

至少建立：

- 事件命名规范
- 事件分层
- 发/订边界
- 调试工具

---

### P2：第三阶段做

#### 8.8 收敛导出层

完全转向插件化导出，兼容层只做薄包装。

#### 8.9 重构配置格式

从扁平 key 转为按域分组。

#### 8.10 补 README 与安装矩阵

把项目定位、依赖、可选功能、安装方式、题材模块说明和导出能力讲清楚。

---

## 9. 文件级重构蓝图

下面是更具体的目录与文件级方案。

---

### 9.1 新目录设计

```text
writer_app/
├─ main.py
├─ app/
│  ├─ app_shell.py
│  ├─ bootstrap.py
│  ├─ workspace_builder.py
│  ├─ menu_builder.py
│  └─ shortcut_registry.py
│
├─ core/
│  ├─ config.py
│  ├─ event_bus.py
│  ├─ event_topics.py
│  ├─ event_debug.py
│  │
│  ├─ project_manager.py
│  ├─ project_store.py
│  ├─ outline_service.py
│  ├─ character_service.py
│  ├─ world_service.py
│  ├─ asset_service.py
│  ├─ search_service.py
│  │
│  ├─ project_types.py
│  ├─ module_registry.py
│  ├─ typed_data.py
│  │
│  ├─ commands/
│  │  ├─ __init__.py
│  │  ├─ base.py
│  │  ├─ outline_commands.py
│  │  ├─ script_commands.py
│  │  ├─ wiki_commands.py
│  │  ├─ relationship_commands.py
│  │  ├─ evidence_commands.py
│  │  ├─ timeline_commands.py
│  │  └─ global_commands.py
│  │
│  └─ exporters/
│     ├─ __init__.py
│     ├─ registry.py
│     ├─ base.py
│     ├─ text_exporters.py
│     ├─ office_exporters.py
│     ├─ screenplay_exporters.py
│     └─ game_exporters.py
│
├─ controllers/
│  ├─ base_controller.py
│  ├─ script_controller.py
│  ├─ wiki_controller.py
│  └─ ...
│
├─ panels/
│  └─ script/
│     ├─ character_panel.py
│     ├─ scene_panel.py
│     ├─ editor_panel.py
│     └─ galgame_panel.py
│
├─ ui/
│  └─ ...
└─ utils/
   └─ ...
```

---

## 10. 第一阶段：把入口变成应用壳子

### 10.1 `writer_app/main.py`

最终只保留：

- 创建 Tk 根窗口
- 启动 bootstrap
- 创建 AppShell
- 进入 mainloop

### 10.2 `writer_app/app/bootstrap.py`

职责：

- 初始化配置
- 初始化主题
- 初始化项目管理
- 初始化 AI 客户端
- 初始化托盘 / 音频 / 线程池 / 备份等服务
- 返回 services 容器

### 10.3 `writer_app/app/workspace_builder.py`

职责：

- 根据模块 key 创建 tab frame
- 实例化 controller
- 注册到 `ControllerRegistry`
- 负责工作区重建

### 10.4 `writer_app/app/app_shell.py`

职责：

- 窗口布局
- 状态栏
- 菜单挂载
- 生命周期
- 触发 workspace rebuild

### 10.5 `writer_app/app/menu_builder.py`

职责：

- 构建菜单
- 不直接持有业务状态，只调用 app shell 或 services 的接口

### 10.6 `writer_app/app/shortcut_registry.py`

职责：

- 统一管理快捷键绑定
- 让菜单与快捷键不再混在一起

---

## 11. 第二阶段：统一模块装配链路

### 11.1 目标链路

```text
ProjectType
-> recommended tool keys
-> module registry lookup
-> collect data_modules
-> ensure typed schemas
-> workspace builder mounts controllers
```

### 11.2 各文件职责边界

#### `project_types.py`
只描述：

- 题材元信息
- 推荐模块组合
- 默认 tab
- wiki 分类
- asset types

#### `module_registry.py`
只描述：

- 模块名
- 模块说明
- UI 分组
- order
- data_modules
- ai_hint
- controller/view 工厂信息

#### `typed_data.py`
只描述：

- 数据模块枚举
- 默认 schema
- ensure / archive / restore / migrate

---

## 12. 第三阶段：拆 `ProjectManager`

### 12.1 目标

让 `ProjectManager` 从“大杂烩”变成 façade。

### 12.2 具体拆分

#### `project_store.py`
负责：

- new / load / save
- modified 状态
- current_file
- 基础迁移

#### `outline_service.py`
负责：

- 大纲节点查找
- 父节点查找
- outline path
- 场景与大纲双向链接

#### `character_service.py`
负责：

- 角色查找
- 人物事件
- 场景-角色矩阵
- 角色共现场景查询

#### `world_service.py`
负责：

- wiki 同步
- factions
- variables
- world entries

#### `asset_service.py`
负责：

- Galgame assets CRUD
- 按角色 / 类型过滤资源

#### `search_service.py`
负责：

- 全局搜索
- 自动关系生成等分析性逻辑

### 12.3 迁移策略

第一步不要大量改调用点。  
先让 `ProjectManager` 作为 façade，把旧方法转发到新 service。

---

## 13. 第四阶段：拆命令系统

### 13.1 目标目录

```text
core/commands/
├─ base.py
├─ outline_commands.py
├─ script_commands.py
├─ wiki_commands.py
├─ relationship_commands.py
├─ evidence_commands.py
├─ timeline_commands.py
└─ global_commands.py
```

### 13.2 分类映射

#### `outline_commands.py`
- AddNode
- DeleteNodes
- EditNode
- MoveNode
- flat draft 相关

#### `script_commands.py`
- 角色
- 场景
- POV
- scene content
- character events

#### `wiki_commands.py`
- wiki entry add/edit/delete

#### `relationship_commands.py`
- 关系连线
- relationship events

#### `evidence_commands.py`
- evidence node / link / layout

#### `timeline_commands.py`
- timeline add/edit/delete
- scene 同步到 timeline 逻辑可考虑后续并入

#### `global_commands.py`
- 全局替换
- 灵感转节点等跨域操作

### 13.3 拆分时顺手修的点

- 统一命令变量命名，避免 `command/cmd` 混乱。
- 检查重复 `undo()`、拷贝粘贴残留、深浅拷贝不一致的问题。

---

## 14. 第五阶段：拆 `ScriptController`

### 14.1 为什么先拆它

它已经成为典型膨胀控制器，几乎把一个大型编辑模块应有的所有子系统都塞在一起了。

### 14.2 目标结构

```text
panels/script/
├─ character_panel.py
├─ scene_panel.py
├─ editor_panel.py
└─ galgame_panel.py
```

### 14.3 子面板职责

#### `character_panel.py`
- 角色列表
- 角色详情
- 标签
- 人格雷达图
- AI 性格识别
- 角色出现的场景

#### `scene_panel.py`
- 场景列表
- 场景过滤
- 场景元信息
- 角色多选
- 时间轴同步入口

#### `editor_panel.py`
- ScriptEditor
- 保存
- 快照 / 历史
- AI 续写 / 改写
- TTS
- 逻辑 / 动机 / 张力按钮

#### `galgame_panel.py`
- 分支选项
- 流程图
- 资源预加载
- 场景跳转相关 UI

### 14.4 `ScriptController` 留什么

只保留：

- 当前选中场景索引
- 面板之间的协调
- `refresh()`
- `apply_theme()`
- 对外暴露必要接口

---

## 15. 第六阶段：导出层收口

### 15.1 新目录

```text
core/exporters/
├─ base.py
├─ registry.py
├─ text_exporters.py
├─ office_exporters.py
├─ screenplay_exporters.py
└─ game_exporters.py
```

### 15.2 分类建议

#### `text_exporters.py`
- TXT
- Markdown
- HTML

#### `office_exporters.py`
- CSV
- Excel
- DOCX
- PDF
- EPUB

#### `screenplay_exporters.py`
- Fountain
- FDX
- CharacterSides

#### `game_exporters.py`
- Ren'Py

### 15.3 兼容策略

保留旧 `Exporter`，但只做薄包装转发到 `ExporterRegistry`，不要再保存第二套真实逻辑。

---

## 16. 第七阶段：事件与配置治理

### 16.1 事件系统治理

新建：

- `core/event_topics.py`
- `core/event_debug.py`

建议把事件按域分组：

- `scene.*`
- `character.*`
- `outline.*`
- `wiki.*`
- `relationship.*`
- `timeline.*`
- `ui.*`

同时明确三条约束：

1. UI 不直接改核心数据  
2. 数据变更通过命令对象  
3. 命令执行后发领域事件

### 16.2 配置治理

目标从扁平 key：

```json
{
  "lm_api_url": "...",
  "theme": "...",
  "focus_mode_enabled": true
}
```

逐步迁移到：

```json
{
  "ai": {},
  "ui": {},
  "assistant": {},
  "focus": {},
  "weather": {},
  "project": {}
}
```

第一阶段只做兼容读取，不急着一次迁完。

---

## 17. 推荐提交顺序

### 提交 1：搭骨架，不搬逻辑
新建：

- `app/`
- `core/commands/`
- `core/exporters/`

### 提交 2：抽离入口初始化
从 `main.py` 抽：

- bootstrap
- menu builder
- shortcut registry

### 提交 3：抽离模块装配
从 `main.py` 抽：

- workspace builder

### 提交 4：拆命令文件
只搬代码，不改行为。

### 提交 5：修明显 bug
包括 controller 中的变量名错误等。

### 提交 6：拆大控制器
先拆 `ScriptController`。

### 提交 7：拆 `ProjectManager`
引入 store + services + façade。

### 提交 8：导出层收口
转向插件式导出为主。

### 提交 9：统一模块真相源
理顺 `project_types / module_registry / typed_data`。

### 提交 10：配置和事件治理
进入基础设施清理阶段。

---

## 18. 我最建议先动的 5 个文件

如果只做最值的第一批，我建议优先改：

1. `writer_app/main.py`
2. `writer_app/core/commands.py`
3. `writer_app/core/models.py`
4. `writer_app/controllers/script_controller.py`
5. `writer_app/core/exporter.py`

这五个文件改完，项目的：

- 可维护性
- 模块新增成本
- 调试难度
- 协作成本

都会明显下降。

---

## 19. 风险提示

### 19.1 不建议一口气“大重构”

这项目已经有不少可用功能，正确策略应该是：

- **结构先收口**
- **接口先稳定**
- **行为尽量不变**
- **逐步迁移**

### 19.2 最容易踩雷的地方

- controller 与 UI 状态耦合太深
- 事件链路断裂后刷新异常
- 命令对象 undo/redo 兼容性
- `ProjectManager` 拆分时旧调用点过多
- 导出器兼容层删得太快

### 19.3 最稳妥的方式

每一步都做到：

- **只搬代码，不改行为**
- 先引入新结构
- 再让旧结构调用新结构
- 最后移除旧实现

---

## 20. 最终建议

一句话总结：

> **这个项目不需要推翻重写，而是需要把已经出现的模块化方向真正做完。**

它的方向已经是对的：

- 有模块化数据
- 有控制器注册
- 有事件总线
- 有导出插件
- 有题材化工作台

现在缺的是：

- 入口收口
- 领域拆分
- 配置统一
- 导出收敛
- 文档与工程收尾

所以最优策略不是“换框架重做”，而是：

> **沿着现有路线，把最后 30% 的架构收口做完。**

---

## 21. 建议附录：后续可继续补的文档

后续如果继续完善，我建议再补这几份文档：

- `README.md`：对外介绍、运行方式、功能概览
- `ARCHITECTURE.md`：系统结构图与层次说明
- `MODULES.md`：模块、题材、数据模块对照表
- `EXPORTS.md`：导出能力和依赖说明
- `ROADMAP.md`：阶段计划与优先级
- `MIGRATION_GUIDE.md`：重构迁移指引

---

## 22. 本文用途建议

这份文档适合用于：

- 给自己做后续重构排期
- 给协作者做上手说明
- 作为一次正式重构的设计输入
- 作为 issue / milestone 的拆分依据

---

_整理完成时间：当前会话生成版_
