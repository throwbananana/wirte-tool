"""
悬浮助手 - 叙事引擎管理器 (Narrative Chain Manager)
负责管理多阶段、有状态的叙事事件链
"""
import time
import random
from typing import Dict, Optional, Any, Callable
from .narrative_definitions import NARRATIVE_CHAINS
from .states import AssistantState

class NarrativeManager:
    def __init__(self, assistant, pet_system):
        self.assistant = assistant
        self.pet_system = pet_system
        self.active_chains: Dict[str, Dict] = {} 
        self._load_state()

    def _load_state(self):
        saved_state = self.pet_system.data.event_state.get("narrative_chains", {})
        self.active_chains = saved_state

    def _save_state(self):
        if "narrative_chains" not in self.pet_system.data.event_state:
            self.pet_system.data.event_state["narrative_chains"] = {}
        self.pet_system.data.event_state["narrative_chains"] = self.active_chains
        self.pet_system.save()

    def check_triggers(self, context: Dict[str, Any]) -> Optional[Dict]:
        current_time = time.time()

        # 1. 检查正在进行的链
        for chain_id, state in list(self.active_chains.items()):
            next_check = state.get("next_check", 0)
            if current_time >= next_check:
                return self._execute_step(chain_id, state["current_step"])

        # 2. 检查新链触发
        sorted_chains = sorted(NARRATIVE_CHAINS.items(), key=lambda x: x[1].get("priority", 0), reverse=True)
        
        for chain_id, chain_def in sorted_chains:
            if chain_id in self.active_chains:
                continue
            
            last_run = self.pet_system.data.event_state.get(f"narrative_cooldown_{chain_id}", 0)
            cooldown = chain_def.get("cooldown", 0)
            if current_time - last_run < cooldown:
                continue

            start_step = chain_def["steps"].get("start") or chain_def["steps"].get("step_1")
            if not start_step:
                continue
                
            condition = start_step.get("trigger_condition")
            req_activity = start_step.get("req_activity")
            
            if self._evaluate_condition(condition, context):
                # 检查活动要求
                if req_activity == "typing" and not context.get("is_typing"):
                    continue
                    
                return self._start_chain(chain_id, start_step)

        return None

    def _evaluate_condition(self, condition: str, context: Dict) -> bool:
        if not condition: return False
        if condition == "startup" and context.get("startup"): return True
            
        if condition.startswith("time_range:"):
            try:
                range_str = condition.split(":")[1]
                start_s, end_s = range_str.split("-")
                now_s = context.get("time_str", "00:00")
                if start_s > end_s: return now_s >= start_s or now_s <= end_s
                else: return start_s <= now_s <= end_s
            except: return False
                
        if condition.startswith("analysis:"):
            key = condition.split(":")[1]
            return context.get("analysis_results", {}).get(key, False)

        if condition.startswith("behavior:"):
            target_behavior = condition.split(":")[1]
            return context.get("behavior") == target_behavior

        if condition.startswith("project_type:"):
            target = condition.split(":")[1]
            return context.get("project_type") == target

        return False

    def start_chain(self, chain_id: str) -> Optional[Dict]:
        """Manually start a narrative chain"""
        if chain_id not in NARRATIVE_CHAINS:
            return None
            
        # Check cooldown? Maybe skip for forced events
        chain_def = NARRATIVE_CHAINS[chain_id]
        start_step_id = "start" if "start" in chain_def["steps"] else "step_1"
        start_step = chain_def["steps"].get(start_step_id)
        
        if not start_step:
            return None
            
        # Force start ignores conditions but respects delay
        return self._start_chain(chain_id, start_step)

    def _start_chain(self, chain_id: str, step_data: Dict) -> Optional[Dict]:
        step_id = "start" if "start" in NARRATIVE_CHAINS[chain_id]["steps"] else "step_1"
        delay = step_data.get("delay", 0)
        
        if delay > 0:
            # 有延迟，只记录状态，不立即触发
            self.active_chains[chain_id] = {
                "current_step": step_id,
                "next_check": time.time() + delay
            }
            self._save_state()
            return None
        else:
            # 立即触发
            self.active_chains[chain_id] = {
                "current_step": step_id,
                "next_check": 0
            }
            self._save_state()
            return self._format_event_output(chain_id, step_data)

    def _execute_step(self, chain_id: str, step_id: str) -> Dict:
        chain_def = NARRATIVE_CHAINS.get(chain_id)
        if not chain_def: return None
        step_data = chain_def["steps"].get(step_id)
        if not step_data: return None
        return self._format_event_output(chain_id, step_data)

    def _format_event_output(self, chain_id: str, step_data: Dict) -> Dict:
        return {
            "type": "narrative",
            "chain_id": chain_id,
            "message": step_data.get("dialogue", "..."),
            "mood": step_data.get("mood", AssistantState.IDLE),
            "options": step_data.get("options", []),
            "rewards": step_data.get("rewards", {}),
            "sound": step_data.get("sound"),
            "action": step_data.get("action"),
            "diary_id": step_data.get("diary_id")
        }

    def handle_option_selection(self, chain_id: str, option_index: int):
        if chain_id not in self.active_chains: return
        chain_def = NARRATIVE_CHAINS.get(chain_id)
        current_step_id = self.active_chains[chain_id]["current_step"]
        step_data = chain_def["steps"].get(current_step_id)
        
        if not step_data or "options" not in step_data: return
        if option_index >= len(step_data["options"]): return
            
        selected = step_data["options"][option_index]
        if selected.get("action"): self._execute_action(selected.get("action"))
        if selected.get("mood_reaction"): self.assistant.set_state(selected.get("mood_reaction"), duration=2000)
            
        self._advance_to_step(chain_id, selected.get("next_step"), step_data)

    def handle_no_option_step(self, chain_id: str):
        """处理无选项步骤的自动推进"""
        if chain_id not in self.active_chains: return
        chain_def = NARRATIVE_CHAINS.get(chain_id)
        current_step_id = self.active_chains[chain_id]["current_step"]
        step_data = chain_def["steps"].get(current_step_id)
        
        if not step_data: return
        
        # 自动推进到 next_step 或结束
        self._advance_to_step(chain_id, step_data.get("next_step"), step_data)

    def _advance_to_step(self, chain_id: str, next_step_id: str, current_step_data: Dict):
        """推进步骤逻辑"""
        chain_def = NARRATIVE_CHAINS.get(chain_id)
        
        if next_step_id:
            next_step_data = chain_def["steps"].get(next_step_id)
            if next_step_data:
                # 计算延迟
                delay = current_step_data.get("delay_next", 0)
                if not delay:
                    delay = next_step_data.get("delay", 0)
                
                if delay > 0:
                    self.active_chains[chain_id]["current_step"] = next_step_id
                    self.active_chains[chain_id]["next_check"] = time.time() + delay
                    self.assistant._append_message("system", f"（助手将在 {int(delay/60) + 1} 分钟后回访）")
                else:
                    self.active_chains[chain_id]["current_step"] = next_step_id
                    self.active_chains[chain_id]["next_check"] = 0
                    # 立即执行？由下一次 check_triggers 触发
                    

            else:
                self._finish_chain(chain_id)
        elif current_step_data.get("finish_chain"):
            self._finish_chain(chain_id)
        else:
            # 既没有后续也没 finish，默认为结束
            self._finish_chain(chain_id)
            
        self._save_state()

    def _finish_chain(self, chain_id):
        if chain_id in self.active_chains:
            del self.active_chains[chain_id]
            self.pet_system.data.event_state[f"narrative_cooldown_{chain_id}"] = time.time()
            self._save_state()

    def _execute_action(self, action: str):
        if action == "open_goal_dialog": pass
        elif action.startswith("open_tool:"):
            tool_id = action.split(":")[1]
            if hasattr(self.assistant, "_use_tool"):
                self.assistant.after(500, lambda: self.assistant._use_tool(tool_id))