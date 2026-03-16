# Reverse Engineering 修复说明

本包基于 `throwbananana/wirte-tool` 当前 `main` 分支的逆推理相关脚本做了最小可替换修复，重点覆盖以下问题：

1. 时间线合并错误：`truth` / `lie` 同名同时间事件不再被误合并。
2. 时间线导入联动：导入真相事件时会尝试直接关联已有场景，并保留 `chapter_title` 元数据。
3. 谎言 → 真相关联：从“只按名字模糊匹配”改为“名称 + 时间戳 + 章节标题”的加权匹配。
4. 增量缓存误跳过：缓存键已绑定 `analysis_type`、模型与主要推理配置、是否启用长上下文。
5. 停止分析体验：为 AI 请求增加协作式取消轮询，停止后不会继续把迟到结果写回界面。
6. 长上下文势力记忆：关系分析里 `target_type=faction` 会写入 `known_entities`。
7. 时间线自动联动一致性：自动修复联动时改为走 `EditTimelineEventCommand`，避免直接改对象。

## 已修改文件

- `writer_app/core/reverse_engineer.py`
- `writer_app/ui/reverse_engineering.py`
- `tests/test_reverse_engineer_fixes.py`

## 替换方式

把压缩包里的文件覆盖到原仓库对应路径即可。

## 仍未彻底解决的点

- 如果底层 `ai_client.call_lm_studio_with_prompts()` 本身不支持真正中断 HTTP 请求，那么“停止分析”仍然属于**协作式取消**：界面会尽快停，但已发出的底层请求可能还会在后台跑完。
- 关系/势力导入中仍有一部分数据改动不是完整命令化，这次没有继续扩大改动面。
