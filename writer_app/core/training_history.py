import json
import logging
from pathlib import Path
from typing import List, Dict, Any
import time
import uuid

from writer_app.core.training import DEFAULT_HISTORY_LIMIT

logger = logging.getLogger(__name__)

HISTORY_SCHEMA_VERSION = 2


class TrainingHistoryManager:
    """管理训练会话的存储和检索。"""

    def __init__(self, data_dir: Path):
        self.history_file = data_dir / "training_history.json"
        self._history: List[Dict[str, Any]] = []
        self.load()

    def load(self):
        if self.history_file.exists():
            try:
                with open(self.history_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                if isinstance(data, dict) and "sessions" in data:
                    self._history = data.get("sessions", [])
                elif isinstance(data, list):
                    self._history = data
                else:
                    self._history = []
                self._history = [self._normalize_session(s) for s in self._history if isinstance(s, dict)]
            except Exception as e:
                logger.error(f"加载训练历史失败: {e}")
                self._history = []
        else:
            self._history = []

    def save(self):
        try:
            with open(self.history_file, 'w', encoding='utf-8') as f:
                json.dump(self._history, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"保存训练历史失败: {e}")

    def _normalize_scores(self, scores: Dict) -> Dict:
        if not isinstance(scores, dict):
            return {}

        def get_int(*keys):
            for key in keys:
                if key in scores:
                    try:
                        return int(scores[key])
                    except (TypeError, ValueError):
                        continue
            return None

        score_1 = get_int("score_1", "Score 1", "评分1", "评分 1")
        score_2 = get_int("score_2", "Score 2", "评分2", "评分 2")
        score_3 = get_int("score_3", "Score 3", "评分3", "评分 3")
        total = get_int("total", "Total Score", "总分", "总分数")

        if total is None and all(isinstance(v, int) for v in [score_1, score_2, score_3]):
            total = score_1 + score_2 + score_3

        labels = {}
        if isinstance(scores.get("labels"), dict):
            labels.update(scores.get("labels", {}))
        for idx in (1, 2, 3):
            for key in (f"label_{idx}", f"label{idx}"):
                if key in scores:
                    labels[f"score_{idx}"] = scores.get(key)

        return {
            "score_1": score_1 or 0,
            "score_2": score_2 or 0,
            "score_3": score_3 or 0,
            "total": total or 0,
            "labels": labels
        }

    def _normalize_session(self, session: Dict) -> Dict:
        if "analysis_text" not in session and "analysis" in session:
            session["analysis_text"] = session.get("analysis", "")
        session["scores"] = self._normalize_scores(session.get("scores", {}))
        session["schema_version"] = HISTORY_SCHEMA_VERSION
        return session

    def add_session(self, mode: str, prompt_data: Dict, content: str, analysis: str, scores: Dict = None):
        session = {
            "id": str(uuid.uuid4()),
            "timestamp": time.time(),
            "date_str": time.strftime("%Y-%m-%d %H:%M:%S"),
            "mode": mode,
            "prompt_data": prompt_data,
            "content": content,
            "analysis_text": analysis,
            "scores": self._normalize_scores(scores or {}),
            "schema_version": HISTORY_SCHEMA_VERSION
        }
        self._history.insert(0, session)  # 最新的在前

        # 限制历史记录大小以防止数据膨胀
        if len(self._history) > DEFAULT_HISTORY_LIMIT:
            self._history = self._history[:DEFAULT_HISTORY_LIMIT]

        self.save()

    def get_history(self) -> List[Dict]:
        return self._history

    def clear_history(self):
        self._history = []
        self.save()

    def get_stats(self) -> Dict:
        if not self._history:
            return {"total_sessions": 0, "avg_score": 0}

        total = len(self._history)
        total_score = 0
        score_count = 0

        for sess in self._history:
            scores = sess.get("scores", {})
            # 尝试获取总分，兼容不同的键名
            s = scores.get("Total Score") or scores.get("total") or scores.get("总分")

            # 处理字符串类型的分数
            if isinstance(s, str):
                try:
                    s = int(s)
                except ValueError:
                    logger.warning(f"无法解析分数值: {s}")
                    continue

            if isinstance(s, (int, float)):
                total_score += s
                score_count += 1

        avg = round(total_score / score_count, 1) if score_count > 0 else 0
        return {
            "total_sessions": total,
            "avg_score": avg
        }
