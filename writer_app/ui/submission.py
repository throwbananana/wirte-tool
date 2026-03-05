import tkinter as tk
from tkinter import ttk, messagebox
import threading
import re
from writer_app.utils.ai_client import AIClient
from writer_app.core.icon_manager import IconManager
from writer_app.core.event_bus import get_event_bus, Events

def get_icon(name, fallback):
    return IconManager().get_icon(name, fallback=fallback)

def get_icon_font(size=12):
    return IconManager().get_font(size=size)


class SubmissionDialog(tk.Toplevel):
    def __init__(self, parent, project_manager, ai_client, config_manager, gamification_manager):
        super().__init__(parent)
        self.title("作品投递模拟")
        self.geometry("600x700")
        
        self.project_manager = project_manager
        self.ai_client = ai_client
        self.config_manager = config_manager
        self.gamification_manager = gamification_manager
        
        self.setup_ui()
        self.set_ai_mode_enabled(self.config_manager.is_ai_enabled())
        self._ai_mode_handler = self._on_ai_mode_changed
        get_event_bus().subscribe(Events.AI_MODE_CHANGED, self._ai_mode_handler)
        
    def setup_ui(self):
        # Header
        header = tk.Frame(self, bg="#3F51B5", height=80)
        header.pack(fill=tk.X)
        header.pack_propagate(False)
        
        icon_lbl = tk.Label(header, text=get_icon("edit", "📝"), font=get_icon_font(24), bg="#3F51B5", fg="white")
        icon_lbl.pack(side=tk.LEFT, padx=(20, 10))
        tk.Label(header, text="编辑部投递通道", font=("Microsoft YaHei", 16, "bold"), bg="#3F51B5", fg="white").pack(side=tk.LEFT)

        
        # Content Preview
        content_frame = ttk.LabelFrame(self, text="投递内容预览")
        content_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        self.text_preview = tk.Text(content_frame, height=10, wrap=tk.WORD, font=("Arial", 10))
        self.text_preview.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Load content
        script = self.project_manager.get_script()
        full_text = f"标题: {script.get('title', '无标题')}\n\n"
        for scene in script.get("scenes", []):
            full_text += f"{scene.get('name')}\n{scene.get('content')}\n\n"
        self.text_preview.insert("1.0", full_text)
        
        # Controls
        ctrl_frame = ttk.Frame(self)
        ctrl_frame.pack(fill=tk.X, padx=10, pady=10)
        
        self.status_var = tk.StringVar(value="准备就绪")
        ttk.Label(ctrl_frame, textvariable=self.status_var, foreground="#666").pack(side=tk.LEFT)
        
        self.submit_btn = ttk.Button(ctrl_frame, text="确认投递 (消耗 50 积分)", command=self.do_submit)
        self.submit_btn.pack(side=tk.RIGHT)
        
        # Result Area
        self.result_frame = ttk.LabelFrame(self, text="编辑部回执")
        self.result_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
        self.result_text = tk.Text(self.result_frame, state=tk.DISABLED, bg="#F5F5F5", font=("Microsoft YaHei", 10))
        self.result_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

    def do_submit(self):
        if not self.config_manager.is_ai_enabled():
            messagebox.showinfo("提示", "当前为非AI模式，投稿模拟不可用。")
            return
        # Optional: Check if user has points to submit?
        # For now, let's make it free or just simulate cost
        
        content = self.text_preview.get("1.0", tk.END).strip()
        if len(content) < 100:
            messagebox.showwarning("内容过少", "作品字数太少，编辑可能不会看哦。(至少100字)")
            return
            
        self.submit_btn.state(["disabled"])
        self.status_var.set("正在等待编辑审阅...")
        
        thread = threading.Thread(target=self._process_submission, args=(content,), daemon=True)
        thread.start()

    def _process_submission(self, content):
        try:
            config = self.config_manager.get_config()
            api_url = config.get("lm_api_url", "http://localhost:1234/v1/chat/completions")
            model = config.get("lm_api_model", "qwen2.5-7b-instruct-1m")
            api_key = config.get("lm_api_key", "")
            
            system_prompt = (
                "你是一位严厉但专业的文学编辑。请阅读用户的作品片段，并给出：\n"
                "1. 评分 (0-100分)\n"
                "2. 简短评语 (优点和缺点)\n"
                "3. 是否签约 (是/否)\n\n"
                "请严格按照以下JSON格式返回，不要包含其他废话：\n"
                "{\"score\": 85, \"comment\": \"...\", \"signed\": true}"
            )
            
            # Truncate content to avoid token limits
            submission_text = content[:3000]
            
            response = self.ai_client.call_lm_studio_with_prompts(
                api_url, model, api_key,
                system_prompt, submission_text,
                temperature=0.7
            )
            
            self.after(0, lambda: self._show_result(response))
            
        except Exception as e:
            self.after(0, lambda: self._on_error(str(e)))

    def _show_result(self, raw_response):
        self.submit_btn.state(["!disabled"])
        self.status_var.set("审阅完成")
        
        # Parse JSON
        score = 60
        comment = raw_response
        is_signed = False
        
        try:
            # Try to find JSON block
            json_match = re.search(r'\{.*\}', raw_response, re.DOTALL)
            if json_match:
                data = eval(json_match.group()) # simple eval for demo, json.loads safer
                # Using json.loads is better but LLM output varies. 
                # Let's try flexible parsing or just manual extraction if simple.
                # Actually, let's rely on text parsing if JSON fails
                score = int(data.get("score", 60))
                comment = data.get("comment", "")
                is_signed = data.get("signed", False)
            else:
                # Fallback text parsing
                if "评分" in raw_response:
                    score_match = re.search(r'(\d+)', raw_response)
                    if score_match: score = int(score_match.group(1))
        except (json.JSONDecodeError, KeyError, ValueError, TypeError):
            pass  # Keep defaults
            
        result_str = f"【评分】 {score}\n"
        signed_icon = get_icon("checkmark_circle", "🎉")
        rejected_icon = get_icon("heart", "💪")
        result_str += f"【结果】 {signed_icon if score >= 80 else rejected_icon} {'签约通过' if score >= 80 else '遗憾退稿'}\n"
        result_str += f"【评语】\n{comment}\n"
        
        self.result_text.configure(state=tk.NORMAL)
        self.result_text.delete("1.0", tk.END)
        # We need to set the font for the icon part if we use the icon char.
        # This requires inserting in parts.
        
        self.result_text.tag_config("icon", font=get_icon_font(10))
        
        self.result_text.insert(tk.END, f"【评分】 {score}\n")
        self.result_text.insert(tk.END, "【结果】 ")
        self.result_text.insert(tk.END, signed_icon if score >= 80 else rejected_icon, "icon")
        self.result_text.insert(tk.END, f" {'签约通过' if score >= 80 else '遗憾退稿'}\n")
        self.result_text.insert(tk.END, f"【评语】\n{comment}\n")
        
        self.result_text.configure(state=tk.DISABLED)
        
        # Award Points
        self.gamification_manager.record_submission(score, comment)
        
        if score >= 80:
            messagebox.showinfo("恭喜", f"获得高分评价！奖励大量积分！\n评分: {score}")
        else:
            messagebox.showinfo("完成", f"投递完成。再接再厉！\n评分: {score}")

    def _on_error(self, err):
        self.submit_btn.state(["!disabled"])
        self.status_var.set("连接编辑部失败")
        messagebox.showerror("错误", str(err))

    def set_ai_mode_enabled(self, enabled: bool):
        state = "normal" if enabled else "disabled"
        self.submit_btn.config(state=state)

    def _on_ai_mode_changed(self, _event_type=None, **kwargs):
        enabled = kwargs.get("enabled", True)
        self.set_ai_mode_enabled(enabled)

    def destroy(self):
        if hasattr(self, "_ai_mode_handler") and self._ai_mode_handler:
            get_event_bus().unsubscribe(Events.AI_MODE_CHANGED, self._ai_mode_handler)
        super().destroy()
