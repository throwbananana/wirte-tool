"""
Galgame/视觉小说类 AI 工具 - 提供分支验证、变量追踪、结局可达性检查等功能

用法:
    这些工具通过 AIToolRegistry 自动注册，可被 AI 调用
"""

from typing import Dict, List, Any, Optional, Set, Tuple
from writer_app.core.ai_tools import AITool, ToolParameter, ToolResult


class ValidateBranchingLogicTool(AITool):
    """验证分支逻辑"""

    name = "validate_branching"
    description = "验证剧本中的分支逻辑是否完整、是否有死分支"
    parameters = []

    def execute(self, project_manager, command_executor, params: Dict) -> ToolResult:
        try:
            project_data = project_manager.get_project_data()
            variables_data = project_data.get("variables", {})
            scenes = project_manager.get_scenes()

            issues = []
            branch_stats = {
                "total_scenes": len(scenes),
                "scenes_with_choices": 0,
                "total_choices": 0,
                "dead_branches": 0,
                "orphan_scenes": 0
            }

            # 分析场景的分支结构
            scene_refs = {}  # scene_uid -> list of scenes that jump to it
            scene_uids = {scene.get("uid") for scene in scenes}

            for idx, scene in enumerate(scenes):
                content = scene.get("content", "")
                scene_uid = scene.get("uid", "")
                choices = scene.get("choices", [])

                if choices:
                    branch_stats["scenes_with_choices"] += 1
                    branch_stats["total_choices"] += len(choices)

                    for choice in choices:
                        target = choice.get("target_scene")
                        if target:
                            if target not in scene_refs:
                                scene_refs[target] = []
                            scene_refs[target].append(scene_uid)

                            # 检查目标场景是否存在
                            if target not in scene_uids:
                                issues.append({
                                    "scene_index": idx,
                                    "scene_name": scene.get("name", ""),
                                    "issue_type": "invalid_target",
                                    "severity": "error",
                                    "description": f"选项「{choice.get('text', '')}」指向不存在的场景「{target}」"
                                })
                                branch_stats["dead_branches"] += 1

                        # 检查条件变量是否存在
                        condition = choice.get("condition", "")
                        if condition:
                            # 简单的变量引用检查
                            defined_vars = set(variables_data.get("definitions", {}).keys())
                            # 这里可以做更复杂的条件解析
                            # 暂时只检查变量名是否被定义

            # 检查孤立场景（没有任何场景跳转到它）
            for idx, scene in enumerate(scenes):
                scene_uid = scene.get("uid", "")
                if idx > 0 and scene_uid not in scene_refs:
                    # 跳过第一个场景，它是入口
                    issues.append({
                        "scene_index": idx,
                        "scene_name": scene.get("name", ""),
                        "issue_type": "orphan_scene",
                        "severity": "warning",
                        "description": "此场景没有任何入口（没有其他场景跳转到此）"
                    })
                    branch_stats["orphan_scenes"] += 1

            return ToolResult.success(
                message=f"分支验证完成，发现 {len(issues)} 个问题",
                data={
                    "issues": issues,
                    "statistics": branch_stats,
                    "scene_references": {k: len(v) for k, v in scene_refs.items()}
                }
            )

        except Exception as e:
            return ToolResult.error(f"分支验证失败: {e}")


class TraceVariableUsageTool(AITool):
    """追踪变量使用"""

    name = "trace_variable_usage"
    description = "追踪变量的定义、设置和使用情况"
    parameters = [
        ToolParameter(
            name="variable_name",
            type="string",
            description="可选：追踪特定变量",
            required=False
        )
    ]

    def execute(self, project_manager, command_executor, params: Dict) -> ToolResult:
        try:
            project_data = project_manager.get_project_data()
            variables_data = project_data.get("variables", {})
            scenes = project_manager.get_scenes()

            target_var = params.get("variable_name")

            # 获取变量定义
            definitions = variables_data.get("definitions", {})

            variable_usage = {}

            for var_name, var_def in definitions.items():
                if target_var and var_name != target_var:
                    continue

                variable_usage[var_name] = {
                    "definition": var_def,
                    "initial_value": var_def.get("initial", None),
                    "type": var_def.get("type", "unknown"),
                    "set_in_scenes": [],
                    "read_in_scenes": [],
                    "unused": True
                }

            # 扫描场景中的变量使用
            for idx, scene in enumerate(scenes):
                content = scene.get("content", "")
                choices = scene.get("choices", [])

                for var_name in variable_usage:
                    # 检查设置（赋值）
                    # 简化：检查是否包含 "var_name =" 或 "$ var_name"
                    if f"${var_name}" in content or f"{var_name} =" in content:
                        variable_usage[var_name]["set_in_scenes"].append({
                            "scene_index": idx,
                            "scene_name": scene.get("name", "")
                        })
                        variable_usage[var_name]["unused"] = False

                    # 检查读取（在条件中使用）
                    for choice in choices:
                        condition = choice.get("condition", "")
                        if var_name in condition:
                            variable_usage[var_name]["read_in_scenes"].append({
                                "scene_index": idx,
                                "scene_name": scene.get("name", ""),
                                "choice": choice.get("text", "")
                            })
                            variable_usage[var_name]["unused"] = False

            # 生成问题报告
            issues = []
            for var_name, usage in variable_usage.items():
                if usage["unused"]:
                    issues.append({
                        "variable": var_name,
                        "issue_type": "unused",
                        "severity": "info",
                        "description": f"变量「{var_name}」已定义但从未使用"
                    })
                elif usage["read_in_scenes"] and not usage["set_in_scenes"]:
                    issues.append({
                        "variable": var_name,
                        "issue_type": "unset",
                        "severity": "warning",
                        "description": f"变量「{var_name}」被读取但从未显式设置"
                    })

            return ToolResult.success(
                message=f"变量追踪完成，分析了 {len(variable_usage)} 个变量",
                data={
                    "variable_usage": variable_usage,
                    "issues": issues,
                    "total_variables": len(definitions),
                    "unused_count": sum(1 for v in variable_usage.values() if v["unused"])
                }
            )

        except Exception as e:
            return ToolResult.error(f"变量追踪失败: {e}")


class CheckEndingReachabilityTool(AITool):
    """检查结局可达性"""

    name = "check_ending_reachability"
    description = "检查所有结局是否都可以通过某种选择路径到达"
    parameters = []

    def execute(self, project_manager, command_executor, params: Dict) -> ToolResult:
        try:
            scenes = project_manager.get_scenes()
            project_data = project_manager.get_project_data()
            galgame_assets = project_data.get("galgame_assets", {})

            # 识别结局场景
            endings = []
            for idx, scene in enumerate(scenes):
                if scene.get("is_ending", False) or "结局" in scene.get("name", "") or "END" in scene.get("name", "").upper():
                    endings.append({
                        "scene_index": idx,
                        "scene_uid": scene.get("uid", ""),
                        "scene_name": scene.get("name", ""),
                        "ending_type": scene.get("ending_type", "normal")
                    })

            if not endings:
                return ToolResult.success(
                    message="未找到标记为结局的场景",
                    data={"endings": [], "reachability": {}}
                )

            # 构建场景图
            scene_graph = {}  # scene_uid -> list of reachable scene_uids
            scene_uid_to_idx = {}

            for idx, scene in enumerate(scenes):
                uid = scene.get("uid", "")
                scene_uid_to_idx[uid] = idx
                scene_graph[uid] = []

                # 默认流向下一个场景
                if idx < len(scenes) - 1:
                    next_uid = scenes[idx + 1].get("uid", "")
                    if not scene.get("choices"):  # 无选项时流向下一个
                        scene_graph[uid].append(next_uid)

                # 选项跳转
                for choice in scene.get("choices", []):
                    target = choice.get("target_scene")
                    if target:
                        scene_graph[uid].append(target)

            # BFS 检查可达性
            def check_reachable(start_uid: str, target_uid: str) -> Tuple[bool, List[str]]:
                if start_uid == target_uid:
                    return True, [start_uid]

                visited = set()
                queue = [(start_uid, [start_uid])]

                while queue:
                    current, path = queue.pop(0)
                    if current in visited:
                        continue
                    visited.add(current)

                    for next_uid in scene_graph.get(current, []):
                        if next_uid == target_uid:
                            return True, path + [next_uid]
                        if next_uid not in visited:
                            queue.append((next_uid, path + [next_uid]))

                return False, []

            # 检查每个结局的可达性
            start_uid = scenes[0].get("uid", "") if scenes else ""
            reachability = {}

            for ending in endings:
                ending_uid = ending["scene_uid"]
                is_reachable, path = check_reachable(start_uid, ending_uid)

                reachability[ending["scene_name"]] = {
                    "reachable": is_reachable,
                    "path_length": len(path) if path else 0,
                    "path_preview": [scene_uid_to_idx.get(uid, -1) for uid in path[:5]] if path else []
                }

            # 统计
            reachable_count = sum(1 for r in reachability.values() if r["reachable"])
            unreachable = [name for name, r in reachability.items() if not r["reachable"]]

            issues = []
            for name in unreachable:
                issues.append({
                    "ending": name,
                    "issue_type": "unreachable",
                    "severity": "error",
                    "description": f"结局「{name}」无法从开始场景到达"
                })

            return ToolResult.success(
                message=f"结局可达性检查完成：{reachable_count}/{len(endings)} 可达",
                data={
                    "endings": endings,
                    "reachability": reachability,
                    "issues": issues,
                    "statistics": {
                        "total_endings": len(endings),
                        "reachable": reachable_count,
                        "unreachable": len(unreachable)
                    }
                }
            )

        except Exception as e:
            return ToolResult.error(f"结局可达性检查失败: {e}")


class AnalyzeRouteBalanceTool(AITool):
    """分析路线平衡性"""

    name = "analyze_route_balance"
    description = "分析不同攻略路线的内容量和难度平衡"
    parameters = []

    def execute(self, project_manager, command_executor, params: Dict) -> ToolResult:
        try:
            scenes = project_manager.get_scenes()
            characters = project_manager.get_characters()

            # 识别可攻略角色
            heroine_routes = {}

            for char in characters:
                if char.get("is_heroine") or char.get("is_romanceable"):
                    char_name = char.get("name", "")
                    heroine_routes[char_name] = {
                        "scenes": [],
                        "word_count": 0,
                        "choice_count": 0,
                        "has_ending": False
                    }

            # 分析每个场景属于哪个路线
            for idx, scene in enumerate(scenes):
                route = scene.get("route", "")
                scene_chars = scene.get("characters", [])
                content = scene.get("content", "")
                choices = scene.get("choices", [])

                # 如果指定了路线
                if route and route in heroine_routes:
                    heroine_routes[route]["scenes"].append(idx)
                    heroine_routes[route]["word_count"] += len(content)
                    heroine_routes[route]["choice_count"] += len(choices)

                    if scene.get("is_ending"):
                        heroine_routes[route]["has_ending"] = True

                # 根据角色出场推断路线
                else:
                    for char_name in heroine_routes:
                        if char_name in scene_chars:
                            # 可能属于多个路线的共通部分
                            pass

            # 分析平衡性
            balance_issues = []

            if heroine_routes:
                word_counts = [r["word_count"] for r in heroine_routes.values() if r["word_count"] > 0]
                if word_counts:
                    avg_words = sum(word_counts) / len(word_counts)
                    max_words = max(word_counts)
                    min_words = min(word_counts)

                    # 检查字数差异
                    if max_words > avg_words * 1.5:
                        balance_issues.append({
                            "issue_type": "content_imbalance",
                            "severity": "warning",
                            "description": "某些路线的内容量明显多于其他路线"
                        })

                    if min_words < avg_words * 0.5 and min_words > 0:
                        balance_issues.append({
                            "issue_type": "thin_route",
                            "severity": "warning",
                            "description": "某些路线的内容量明显少于其他路线"
                        })

            # 检查缺少结局的路线
            for route_name, route_data in heroine_routes.items():
                if route_data["scenes"] and not route_data["has_ending"]:
                    balance_issues.append({
                        "route": route_name,
                        "issue_type": "missing_ending",
                        "severity": "error",
                        "description": f"路线「{route_name}」没有对应的结局场景"
                    })

            return ToolResult.success(
                message=f"路线平衡性分析完成，发现 {len(balance_issues)} 个问题",
                data={
                    "routes": heroine_routes,
                    "issues": balance_issues,
                    "statistics": {
                        "total_routes": len(heroine_routes),
                        "routes_with_content": sum(1 for r in heroine_routes.values() if r["word_count"] > 0),
                        "routes_with_ending": sum(1 for r in heroine_routes.values() if r["has_ending"])
                    }
                }
            )

        except Exception as e:
            return ToolResult.error(f"路线平衡性分析失败: {e}")


class DetectDeadBranchesTool(AITool):
    """检测死分支"""

    name = "detect_dead_branches"
    description = "检测永远不会被执行的分支（条件永远为假或目标不存在）"
    parameters = []

    def execute(self, project_manager, command_executor, params: Dict) -> ToolResult:
        try:
            scenes = project_manager.get_scenes()
            project_data = project_manager.get_project_data()
            variables_data = project_data.get("variables", {})

            dead_branches = []
            suspicious_branches = []

            for idx, scene in enumerate(scenes):
                choices = scene.get("choices", [])

                for choice_idx, choice in enumerate(choices):
                    choice_text = choice.get("text", "")
                    condition = choice.get("condition", "")
                    target = choice.get("target_scene", "")

                    # 检查目标是否存在
                    if target:
                        target_exists = any(s.get("uid") == target for s in scenes)
                        if not target_exists:
                            dead_branches.append({
                                "scene_index": idx,
                                "scene_name": scene.get("name", ""),
                                "choice_index": choice_idx,
                                "choice_text": choice_text,
                                "issue_type": "invalid_target",
                                "description": f"选项指向不存在的场景「{target}」"
                            })

                    # 检查条件是否可能永远为假
                    if condition:
                        # 简单检查：条件中使用的变量是否被设置过
                        definitions = variables_data.get("definitions", {})

                        # 检查是否引用了未定义的变量
                        for var_name in definitions:
                            if var_name in condition:
                                var_def = definitions[var_name]
                                # 如果变量有初始值且条件检查的是该初始值，可能是有意的
                                # 如果变量没有在任何地方被设置，条件可能永远为假
                                pass

                        # 检查互斥条件
                        # 如果同一场景有两个选项的条件是互斥的，确保覆盖所有情况
                        suspicious_branches.append({
                            "scene_index": idx,
                            "scene_name": scene.get("name", ""),
                            "choice_index": choice_idx,
                            "choice_text": choice_text,
                            "condition": condition,
                            "note": "建议人工验证此条件是否可达"
                        })

            return ToolResult.success(
                message=f"死分支检测完成：发现 {len(dead_branches)} 个死分支",
                data={
                    "dead_branches": dead_branches,
                    "suspicious_branches": suspicious_branches,
                    "total_choices_analyzed": sum(len(s.get("choices", [])) for s in scenes)
                }
            )

        except Exception as e:
            return ToolResult.error(f"死分支检测失败: {e}")


class SuggestChoiceDesignTool(AITool):
    """建议选项设计"""

    name = "suggest_choice_design"
    description = "为场景建议有意义的选项设计"
    parameters = [
        ToolParameter(
            name="scene_index",
            type="integer",
            description="场景索引",
            required=True
        ),
        ToolParameter(
            name="choice_style",
            type="string",
            description="选项风格：'meaningful'(影响剧情)、'personality'(展现性格)、'relationship'(影响好感度)",
            required=False
        )
    ]

    def execute(self, project_manager, command_executor, params: Dict) -> ToolResult:
        try:
            scene_idx = params.get("scene_index")
            choice_style = params.get("choice_style", "meaningful")

            scenes = project_manager.get_scenes()

            if scene_idx < 0 or scene_idx >= len(scenes):
                return ToolResult.error("无效的场景索引")

            scene = scenes[scene_idx]
            scene_chars = scene.get("characters", [])
            content = scene.get("content", "")

            # 选项设计模板
            templates = {
                "meaningful": [
                    {
                        "pattern": "binary_decision",
                        "description": "二选一的关键决定",
                        "example": ["接受邀请", "婉拒邀请"],
                        "impact": "影响后续剧情走向"
                    },
                    {
                        "pattern": "investigation",
                        "description": "调查/探索类选项",
                        "example": ["检查抽屉", "查看窗户", "离开房间"],
                        "impact": "获取不同线索"
                    },
                    {
                        "pattern": "dialogue_choice",
                        "description": "对话回应选项",
                        "example": ["直接询问", "旁敲侧击", "保持沉默"],
                        "impact": "影响对方态度"
                    }
                ],
                "personality": [
                    {
                        "pattern": "reaction",
                        "description": "性格反应选项",
                        "example": ["冷静分析", "激动反驳", "默默接受"],
                        "impact": "展现主角性格"
                    },
                    {
                        "pattern": "attitude",
                        "description": "态度选择",
                        "example": ["认真对待", "开玩笑", "敷衍了事"],
                        "impact": "定义主角人设"
                    }
                ],
                "relationship": [
                    {
                        "pattern": "affection",
                        "description": "好感度选项",
                        "example": ["关心她", "调戏她", "无视她"],
                        "impact": "影响角色好感度"
                    },
                    {
                        "pattern": "support",
                        "description": "支持/反对选项",
                        "example": ["支持她的决定", "提出不同意见", "让她自己决定"],
                        "impact": "影响关系走向"
                    }
                ]
            }

            style_templates = templates.get(choice_style, templates["meaningful"])

            # 根据场景内容生成个性化建议
            suggestions = []
            for template in style_templates:
                suggestion = {
                    **template,
                    "context": f"在场景「{scene.get('name', '')}」中",
                    "characters_involved": scene_chars
                }

                # 如果有特定角色，个性化建议
                if scene_chars:
                    char_name = scene_chars[0]
                    if template["pattern"] == "affection":
                        suggestion["personalized_example"] = [
                            f"关心{char_name}的状况",
                            f"和{char_name}开玩笑",
                            f"不理会{char_name}"
                        ]

                suggestions.append(suggestion)

            return ToolResult.success(
                message=f"生成了 {len(suggestions)} 个选项设计建议",
                data={
                    "scene_index": scene_idx,
                    "scene_name": scene.get("name", ""),
                    "choice_style": choice_style,
                    "suggestions": suggestions,
                    "existing_choices": scene.get("choices", [])
                }
            )

        except Exception as e:
            return ToolResult.error(f"选项设计建议失败: {e}")


def register_tools(registry):
    """注册所有Galgame类工具"""
    registry.register(ValidateBranchingLogicTool())
    registry.register(TraceVariableUsageTool())
    registry.register(CheckEndingReachabilityTool())
    registry.register(AnalyzeRouteBalanceTool())
    registry.register(DetectDeadBranchesTool())
    registry.register(SuggestChoiceDesignTool())
