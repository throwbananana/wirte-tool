"""
悬疑/推理类 AI 工具 - 提供时间线分析、逻辑漏洞检测、红鲱鱼生成等功能

用法:
    这些工具通过 AIToolRegistry 自动注册，可被 AI 调用
"""

from typing import Dict, List, Any, Optional
from writer_app.core.ai_tools import AITool, ToolParameter, ToolResult


class AnalyzeTimelineGapsTool(AITool):
    """分析时间线中的空白和矛盾"""

    name = "analyze_timeline_gaps"
    description = "分析故事时间线，识别时间空白、矛盾和不一致之处"
    parameters = [
        ToolParameter(
            name="focus_character",
            type="string",
            description="可选：聚焦特定角色的时间线",
            required=False
        )
    ]

    def execute(self, project_manager, command_executor, params: Dict) -> ToolResult:
        try:
            scenes = project_manager.get_scenes()
            if not scenes:
                return ToolResult.error("没有场景可分析")

            focus_char = params.get("focus_character")

            timeline_issues = []
            prev_scene = None

            for idx, scene in enumerate(scenes):
                scene_time = scene.get("time", "")
                scene_chars = scene.get("characters", [])

                # 检查时间设置
                if not scene_time:
                    timeline_issues.append({
                        "scene_index": idx,
                        "scene_name": scene.get("name", ""),
                        "issue_type": "missing_time",
                        "severity": "warning",
                        "description": "场景缺少时间设置"
                    })

                # 检查角色连续性
                if focus_char and prev_scene:
                    prev_chars = prev_scene.get("characters", [])
                    if focus_char in prev_chars and focus_char not in scene_chars:
                        # 角色在前一场景出现但当前场景不在
                        timeline_issues.append({
                            "scene_index": idx,
                            "scene_name": scene.get("name", ""),
                            "issue_type": "character_gap",
                            "severity": "info",
                            "description": f"角色「{focus_char}」在场景 {idx} 和 {idx+1} 之间存在行踪空白"
                        })

                prev_scene = scene

            # 检查真相时间线与叙事时间线（如果有）
            timelines = project_manager.get_project_data().get("timelines", {})
            truth_events = timelines.get("truth_events", [])
            lie_events = timelines.get("lie_events", [])

            if truth_events and lie_events:
                # 检查叙事时间线是否遗漏真相事件
                truth_times = {e.get("time") for e in truth_events if e.get("time")}
                lie_times = {e.get("time") for e in lie_events if e.get("time")}

                unnarrated = truth_times - lie_times
                if unnarrated:
                    timeline_issues.append({
                        "scene_index": -1,
                        "scene_name": "全局",
                        "issue_type": "unnarrated_truth",
                        "severity": "info",
                        "description": f"有 {len(unnarrated)} 个真相时间点未在叙事中展现"
                    })

            return ToolResult.success(
                message=f"时间线分析完成，发现 {len(timeline_issues)} 个问题",
                data={
                    "total_scenes": len(scenes),
                    "issues": timeline_issues,
                    "has_dual_timeline": bool(truth_events and lie_events)
                }
            )

        except Exception as e:
            return ToolResult.error(f"时间线分析失败: {e}")


class DetectPlotHolesTool(AITool):
    """检测情节漏洞"""

    name = "detect_plot_holes"
    description = "检测故事中的逻辑漏洞、未解释的线索、不一致的细节"
    parameters = []

    def execute(self, project_manager, command_executor, params: Dict) -> ToolResult:
        try:
            scenes = project_manager.get_scenes()
            characters = project_manager.get_characters()
            world_entries = project_manager.get_project_data().get("world", {}).get("entries", [])

            plot_holes = []

            # 1. 检查角色知识状态
            char_knowledge = {}  # {char_name: set of known facts}

            for char in characters:
                char_name = char.get("name", "")
                char_knowledge[char_name] = set()

            # 追踪角色在场景中获取的信息
            for idx, scene in enumerate(scenes):
                scene_chars = scene.get("characters", [])
                content = scene.get("content", "")

                # 简单检测：角色引用了他们不应该知道的信息
                # （这是一个简化版本，实际需要更复杂的分析）

            # 2. 检查未闭合的线索
            timelines = project_manager.get_project_data().get("timelines", {})
            evidence_data = project_manager.get_project_data().get("relationships", {})
            evidence_nodes = evidence_data.get("nodes", [])

            # 检查证据是否都有解释
            for evidence in evidence_nodes:
                if evidence.get("type") == "evidence":
                    evidence_name = evidence.get("name", "")
                    is_resolved = evidence.get("is_resolved", False)
                    if not is_resolved:
                        plot_holes.append({
                            "type": "unresolved_evidence",
                            "severity": "warning",
                            "description": f"证据「{evidence_name}」尚未解释或闭合"
                        })

            # 3. 检查动机-机会-手段
            # 简化版：检查是否有定义嫌疑人及其三要素
            for char in characters:
                is_suspect = char.get("is_suspect", False)
                if is_suspect:
                    motive = char.get("motive", "")
                    opportunity = char.get("opportunity", "")
                    means = char.get("means", "")

                    missing = []
                    if not motive:
                        missing.append("动机")
                    if not opportunity:
                        missing.append("机会")
                    if not means:
                        missing.append("手段")

                    if missing:
                        plot_holes.append({
                            "type": "incomplete_suspect",
                            "severity": "warning",
                            "character": char.get("name", ""),
                            "description": f"嫌疑人「{char.get('name', '')}」缺少：{', '.join(missing)}"
                        })

            return ToolResult.success(
                message=f"情节漏洞检测完成，发现 {len(plot_holes)} 个潜在问题",
                data={
                    "plot_holes": plot_holes,
                    "total_scenes": len(scenes),
                    "total_characters": len(characters)
                }
            )

        except Exception as e:
            return ToolResult.error(f"情节漏洞检测失败: {e}")


class GenerateRedHerringTool(AITool):
    """生成红鲱鱼（误导线索）建议"""

    name = "generate_red_herring"
    description = "基于现有情节，生成可用的红鲱鱼（误导线索）建议"
    parameters = [
        ToolParameter(
            name="target_character",
            type="string",
            description="可选：希望嫁祸的目标角色",
            required=False
        ),
        ToolParameter(
            name="scene_index",
            type="integer",
            description="可选：在哪个场景附近插入",
            required=False
        )
    ]

    def execute(self, project_manager, command_executor, params: Dict) -> ToolResult:
        try:
            characters = project_manager.get_characters()
            scenes = project_manager.get_scenes()

            target = params.get("target_character")
            scene_idx = params.get("scene_index")

            suggestions = []

            # 基于现有角色生成误导建议
            for char in characters:
                char_name = char.get("name", "")
                if target and char_name != target:
                    continue

                # 检查角色是否已是嫌疑人
                is_suspect = char.get("is_suspect", False)

                if not is_suspect:
                    suggestions.append({
                        "character": char_name,
                        "type": "false_suspect",
                        "suggestion": f"可以为「{char_name}」添加可疑行为，如：秘密会面、神秘电话、异常行踪",
                        "implementation": "在相关场景中添加暗示性描写，但确保最终能解释清白"
                    })

            # 基于场景生成误导建议
            if scene_idx is not None and 0 <= scene_idx < len(scenes):
                scene = scenes[scene_idx]
                suggestions.append({
                    "scene_index": scene_idx,
                    "type": "false_clue",
                    "suggestion": f"在场景「{scene.get('name', '')}」中添加误导性物证",
                    "examples": ["故意留下的指纹", "伪造的不在场证明", "误导性的目击证词"]
                })

            # 通用红鲱鱼模板
            templates = [
                {
                    "type": "timing_misdirection",
                    "description": "时间误导",
                    "suggestion": "利用时间差制造误导，如：错误估计的死亡时间"
                },
                {
                    "type": "identity_confusion",
                    "description": "身份混淆",
                    "suggestion": "利用外貌相似、双胞胎、伪装等制造身份误导"
                },
                {
                    "type": "motive_misdirection",
                    "description": "动机误导",
                    "suggestion": "暴露虚假的动机，隐藏真实动机"
                }
            ]

            return ToolResult.success(
                message=f"生成了 {len(suggestions)} 个红鲱鱼建议",
                data={
                    "character_based": [s for s in suggestions if "character" in s],
                    "scene_based": [s for s in suggestions if "scene_index" in s],
                    "templates": templates
                }
            )

        except Exception as e:
            return ToolResult.error(f"生成红鲱鱼失败: {e}")


class ValidateAlibiTool(AITool):
    """验证不在场证明"""

    name = "validate_alibi"
    description = "验证角色的不在场证明是否存在漏洞"
    parameters = [
        ToolParameter(
            name="character_name",
            type="string",
            description="要验证的角色名称",
            required=True
        )
    ]

    def execute(self, project_manager, command_executor, params: Dict) -> ToolResult:
        try:
            char_name = params.get("character_name")
            if not char_name:
                return ToolResult.error("必须指定角色名称")

            scenes = project_manager.get_scenes()
            characters = project_manager.get_characters()

            # 找到目标角色
            target_char = None
            for char in characters:
                if char.get("name") == char_name:
                    target_char = char
                    break

            if not target_char:
                return ToolResult.error(f"未找到角色「{char_name}」")

            # 分析角色的场景出现情况
            appearances = []
            gaps = []
            prev_scene_idx = -1

            for idx, scene in enumerate(scenes):
                scene_chars = scene.get("characters", [])
                if char_name in scene_chars:
                    appearances.append({
                        "scene_index": idx,
                        "scene_name": scene.get("name", ""),
                        "time": scene.get("time", ""),
                        "location": scene.get("location", "")
                    })

                    # 检查是否有时间空白
                    if prev_scene_idx >= 0 and idx - prev_scene_idx > 1:
                        gap_scenes = []
                        for gap_idx in range(prev_scene_idx + 1, idx):
                            gap_scenes.append({
                                "scene_index": gap_idx,
                                "scene_name": scenes[gap_idx].get("name", ""),
                                "time": scenes[gap_idx].get("time", "")
                            })
                        gaps.append({
                            "from_scene": prev_scene_idx,
                            "to_scene": idx,
                            "gap_scenes": gap_scenes,
                            "issue": f"角色在场景 {prev_scene_idx+1} 和 {idx+1} 之间行踪不明"
                        })

                    prev_scene_idx = idx

            # 检查不在场证明漏洞
            alibi_issues = []

            # 检查关键时间点
            if gaps:
                for gap in gaps:
                    alibi_issues.append({
                        "type": "timeline_gap",
                        "severity": "warning",
                        "description": gap["issue"],
                        "gap_scenes": gap["gap_scenes"]
                    })

            # 检查证人
            alibi_witnesses = target_char.get("alibi_witnesses", [])
            if not alibi_witnesses:
                alibi_issues.append({
                    "type": "no_witness",
                    "severity": "info",
                    "description": "角色没有定义不在场证明证人"
                })

            return ToolResult.success(
                message=f"不在场证明验证完成，发现 {len(alibi_issues)} 个潜在问题",
                data={
                    "character": char_name,
                    "appearances": appearances,
                    "gaps": gaps,
                    "issues": alibi_issues,
                    "total_scenes": len(scenes),
                    "appearance_count": len(appearances)
                }
            )

        except Exception as e:
            return ToolResult.error(f"不在场证明验证失败: {e}")


class CheckCluePlacementTool(AITool):
    """检查线索布置"""

    name = "check_clue_placement"
    description = "检查线索的布置是否合理，是否过早泄露，是否有足够的伏笔"
    parameters = []

    def execute(self, project_manager, command_executor, params: Dict) -> ToolResult:
        try:
            scenes = project_manager.get_scenes()
            evidence_data = project_manager.get_project_data().get("relationships", {})
            evidence_nodes = [n for n in evidence_data.get("nodes", []) if n.get("type") == "evidence"]

            clue_analysis = []

            for evidence in evidence_nodes:
                evidence_name = evidence.get("name", "")
                first_mention = None
                mentions = []

                # 搜索场景中的线索提及
                for idx, scene in enumerate(scenes):
                    content = scene.get("content", "")
                    if evidence_name in content:
                        if first_mention is None:
                            first_mention = idx
                        mentions.append({
                            "scene_index": idx,
                            "scene_name": scene.get("name", "")
                        })

                clue_analysis.append({
                    "clue_name": evidence_name,
                    "first_mention_scene": first_mention,
                    "total_mentions": len(mentions),
                    "mentions": mentions,
                    "is_resolved": evidence.get("is_resolved", False)
                })

            # 生成建议
            suggestions = []

            for clue in clue_analysis:
                if clue["total_mentions"] == 0:
                    suggestions.append({
                        "clue": clue["clue_name"],
                        "issue": "线索从未在场景中提及",
                        "severity": "warning"
                    })
                elif clue["total_mentions"] == 1:
                    suggestions.append({
                        "clue": clue["clue_name"],
                        "issue": "线索只提及一次，建议增加伏笔",
                        "severity": "info"
                    })

                if clue["first_mention_scene"] == 0:
                    suggestions.append({
                        "clue": clue["clue_name"],
                        "issue": "线索在第一个场景就出现，可能过早",
                        "severity": "info"
                    })

            return ToolResult.success(
                message=f"线索布置检查完成，分析了 {len(clue_analysis)} 个线索",
                data={
                    "clue_analysis": clue_analysis,
                    "suggestions": suggestions,
                    "total_clues": len(evidence_nodes),
                    "total_scenes": len(scenes)
                }
            )

        except Exception as e:
            return ToolResult.error(f"线索布置检查失败: {e}")


class MapInformationFlowTool(AITool):
    """绘制信息流图"""

    name = "map_information_flow"
    description = "分析并绘制故事中信息的流动方向，追踪哪些角色知道什么信息"
    parameters = []

    def execute(self, project_manager, command_executor, params: Dict) -> ToolResult:
        try:
            scenes = project_manager.get_scenes()
            characters = project_manager.get_characters()

            # 初始化角色知识状态
            char_knowledge = {}
            for char in characters:
                char_name = char.get("name", "")
                char_knowledge[char_name] = {
                    "scenes_present": [],
                    "potential_knowledge": [],
                    "knowledge_sources": []
                }

            # 追踪每个场景的信息流
            scene_info_flow = []

            for idx, scene in enumerate(scenes):
                scene_chars = scene.get("characters", [])
                scene_name = scene.get("name", "")

                # 记录在场角色
                for char_name in scene_chars:
                    if char_name in char_knowledge:
                        char_knowledge[char_name]["scenes_present"].append(idx)
                        char_knowledge[char_name]["potential_knowledge"].append(
                            f"场景 {idx+1}: {scene_name} 中的事件"
                        )

                # 记录场景信息流
                scene_info_flow.append({
                    "scene_index": idx,
                    "scene_name": scene_name,
                    "characters_present": scene_chars,
                    "info_shared_with": scene_chars  # 简化：在场即知道
                })

            # 分析信息不对称
            asymmetries = []
            all_scenes = set(range(len(scenes)))

            for char_name, knowledge in char_knowledge.items():
                present_scenes = set(knowledge["scenes_present"])
                absent_scenes = all_scenes - present_scenes

                if absent_scenes:
                    asymmetries.append({
                        "character": char_name,
                        "absent_from_scenes": list(absent_scenes),
                        "unknown_events_count": len(absent_scenes),
                        "percentage_known": len(present_scenes) / len(scenes) * 100 if scenes else 0
                    })

            return ToolResult.success(
                message=f"信息流分析完成，追踪了 {len(characters)} 个角色",
                data={
                    "character_knowledge": char_knowledge,
                    "scene_info_flow": scene_info_flow,
                    "information_asymmetries": asymmetries,
                    "total_scenes": len(scenes),
                    "total_characters": len(characters)
                }
            )

        except Exception as e:
            return ToolResult.error(f"信息流分析失败: {e}")


def register_tools(registry):
    """注册所有悬疑类工具"""
    registry.register(AnalyzeTimelineGapsTool())
    registry.register(DetectPlotHolesTool())
    registry.register(GenerateRedHerringTool())
    registry.register(ValidateAlibiTool())
    registry.register(CheckCluePlacementTool())
    registry.register(MapInformationFlowTool())
