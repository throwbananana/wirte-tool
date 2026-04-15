# Release Blockers

以下项目在创建正式 release 之前必须完成。

- [ ] 主应用可启动：`python start_app.py`
- [ ] 工具中心可启动：`python start_tools.py`
- [ ] 资产编辑器可启动：`python start_asset_editor.py`
- [ ] 事件分析器可启动：`python analyze_events.py`
- [ ] 新建、保存、重新打开项目主路径可用
- [ ] 核心导出链路完成一次手工验证
- [ ] `python -m unittest discover tests` 全部通过
- [ ] `pip install .` 可完成，包入口可解析
- [ ] README、CHANGELOG、RELEASE_CHECKLIST 与当前版本状态一致
