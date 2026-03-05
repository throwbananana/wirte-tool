import json
import logging
from collections import defaultdict
from typing import Dict, List, Any
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class StatsManager:
    """Computes statistics and skill metrics from training history."""
    
    def __init__(self, history_manager):
        self.history_manager = history_manager

    def get_radar_data(self) -> Dict[str, float]:
        """Calculates average scores for 5 dimensions."""
        history = self.history_manager.get_history()
        if not history:
            return {
                "Creativity": 0,
                "Structure": 0, 
                "Vocabulary": 0,
                "Style": 0,
                "Focus": 0
            }
        
        # Mapping logic: Parse AI analysis text or stored scores to populate these
        # Since currently we only store raw AI text in 'analysis_text', we need a way to parse structured scores
        # or we update TrainingController to parse and store scores separately.
        # For now, let's assume 'scores' field exists in history or we parse it.
        # The TrainingHistoryManager.add_session accepts 'scores' dict.
        
        totals = defaultdict(float)
        counts = defaultdict(int)

        for sess in history:
            scores = sess.get("scores", {})
            if not scores: continue
            
            # Map generic Score 1/2/3 to dimensions based on Mode
            mode = sess.get("mode", "keywords")
            s1 = scores.get("score_1") or scores.get("Score 1") or scores.get("评分1") or 0
            s2 = scores.get("score_2") or scores.get("Score 2") or scores.get("评分2") or 0
            s3 = scores.get("score_3") or scores.get("Score 3") or scores.get("评分3") or 0
            
            if mode == "keywords":
                totals["Creativity"] += s1
                totals["Vocabulary"] += s2
                totals["Structure"] += s3
            elif mode == "brainstorm":
                totals["Creativity"] += s1
                totals["Vocabulary"] += s2
                totals["Structure"] += s3
            elif mode == "style":
                totals["Style"] += s1
                totals["Vocabulary"] += s2
                totals["Structure"] += s3
            elif mode == "continuation":
                totals["Structure"] += s1
                totals["Focus"] += s2
                totals["Creativity"] += s3
            else:
                totals["Creativity"] += (s1+s2+s3)/3
                
            counts["Creativity"] += 1 if mode in ["keywords", "continuation", "brainstorm"] else 0.3
            counts["Vocabulary"] += 1 if mode in ["keywords", "style", "brainstorm"] else 0.3
            counts["Structure"] += 1
            counts["Style"] += 1 if mode == "style" else 0.1
            counts["Focus"] += 1 if mode == "continuation" else 0.1

        # Normalize
        radar = {}
        for dim in ["Creativity", "Structure", "Vocabulary", "Style", "Focus"]:
            count = counts[dim]
            if count > 0:
                radar[dim] = round(totals[dim] / count, 1)
            else:
                radar[dim] = 0
        return radar

    def get_heatmap_data(self) -> Dict[str, int]:
        """Returns { 'YYYY-MM-DD': count } for heatmap."""
        history = self.history_manager.get_history()
        data = defaultdict(int)
        for sess in history:
            # timestamp to YYYY-MM-DD
            ts = sess.get("timestamp", 0)
            date_str = datetime.fromtimestamp(ts).strftime("%Y-%m-%d")
            data[date_str] += 1
        return dict(data)

    def get_streak(self) -> int:
        """Calculates current daily streak."""
        heatmap = self.get_heatmap_data()
        if not heatmap: return 0

        active_dates = set()
        for date_str, count in heatmap.items():
            if count <= 0:
                continue
            try:
                active_dates.add(datetime.strptime(date_str, "%Y-%m-%d").date())
            except ValueError:
                continue

        if not active_dates:
            return 0

        streak = 0
        check_date = datetime.now().date()
        while check_date in active_dates:
            streak += 1
            check_date -= timedelta(days=1)
        return streak
