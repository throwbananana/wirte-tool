import unittest
from unittest.mock import MagicMock
from writer_app.core.reverse_engineer import ReverseEngineeringManager, AnalysisContext

class TestReverseEngineeringManager(unittest.TestCase):
    def setUp(self):
        self.mock_ai_client = MagicMock()
        self.manager = ReverseEngineeringManager(self.mock_ai_client)

    def test_split_text(self):
        text = "Para 1\n\nPara 2\n\nPara 3"
        chunks = self.manager.split_text(text, chunk_size=10)
        self.assertTrue(len(chunks) >= 2)
        self.assertIn("Para 1", chunks[0])

    def test_merge_results_characters_accumulates_description(self):
        """测试角色合并时描述会累加（多视角）"""
        batch1 = [{"name": "Alice", "role": "Protag", "description": "Short desc"}]
        batch2 = [{"name": "Alice", "role": "Protag", "description": "Longer description with more details"}]

        merged = self.manager.merge_results([batch1, batch2], "characters")
        self.assertEqual(len(merged), 1)
        self.assertEqual(merged[0]["name"], "Alice")
        # 新行为：描述累加而非替换
        self.assertIn("Short desc", merged[0]["description"])
        self.assertIn("Longer description with more details", merged[0]["description"])

    def test_merge_results_characters_dedup_same_description(self):
        """测试相同描述不会重复累加"""
        batch1 = [{"name": "Alice", "description": "Same description"}]
        batch2 = [{"name": "Alice", "description": "Same description"}]

        merged = self.manager.merge_results([batch1, batch2], "characters")
        self.assertEqual(len(merged), 1)
        # 相同描述不应重复
        self.assertEqual(merged[0]["description"].count("Same description"), 1)

    def test_merge_results_relationships_preserves_direction(self):
        """测试关系合并保留方向性（A→B 和 B→A 是不同关系）"""
        batch1 = [{"source": "Alice", "target": "Bob", "label": "Friends", "target_type": "character"}]
        batch2 = [{"source": "Bob", "target": "Alice", "label": "Friends", "target_type": "character"}]

        merged = self.manager.merge_results([batch1, batch2], "relationships")
        # 新行为：方向不同视为不同关系
        self.assertEqual(len(merged), 2)

    def test_merge_results_relationships_same_direction(self):
        """测试相同方向的关系会合并"""
        batch1 = [{"source": "Alice", "target": "Bob", "label": "Friends", "target_type": "character"}]
        batch2 = [{"source": "Alice", "target": "Bob", "label": "Allies", "target_type": "character"}]

        merged = self.manager.merge_results([batch1, batch2], "relationships")
        self.assertEqual(len(merged), 1)
        # 标签应该合并
        self.assertIn("Friends", merged[0]["label"])
        self.assertIn("Allies", merged[0]["label"])

    def test_merge_results_tags(self):
        """测试标签合并去重"""
        batch1 = [{"name": "Alice", "tags": ["hero", "protagonist"]}]
        batch2 = [{"name": "Alice", "tags": ["hero", "leader"]}]

        merged = self.manager.merge_results([batch1, batch2], "characters")
        self.assertEqual(len(merged), 1)
        tags = merged[0]["tags"]
        self.assertIn("hero", tags)
        self.assertIn("protagonist", tags)
        self.assertIn("leader", tags)
        # hero 不应重复
        self.assertEqual(tags.count("hero"), 1)

    def test_chapter_detection_txt(self):
        """测试TXT章节检测"""
        # 注意：每个章节内容需要超过50个字符才不会被过滤（用100+字符确保安全）
        text = """这是序章的内容。故事发生在一个遥远的国度，那里有高山流水，有繁华都市。主角小明是一个普通的少年，却有着不平凡的命运。他的故事从这里开始。

第一章 开始
这是第一章的内容。小明踏上了冒险的旅程，遇到了许多志同道合的伙伴。他们一起面对各种挑战，逐渐成长为真正的英雄。这是一段令人难忘的经历。

第二章 发展
这是第二章的内容。故事在这里逐渐发展，冲突开始显现。敌人的阴谋逐渐浮出水面，小明必须做出艰难的选择。命运的齿轮开始转动。
"""
        chapters = self.manager._split_txt_into_chapters(text)
        self.assertEqual(len(chapters), 3)
        self.assertEqual(chapters[0]["title"], "序章")
        self.assertEqual(chapters[1]["title"], "第一章 开始")
        self.assertEqual(chapters[2]["title"], "第二章 发展")

    def test_incremental_analysis(self):
        """测试增量分析功能"""
        units = [
            {"title": "Chapter 1", "content": "Content A"},
            {"title": "Chapter 2", "content": "Content B"}
        ]

        # 首次应该都是新的
        new_units, skipped = self.manager.get_incremental_units(units, "characters")
        self.assertEqual(len(new_units), 2)
        self.assertEqual(len(skipped), 0)

        # 标记第一个为已分析
        self.manager.mark_analyzed(new_units[0]["_hash"], "characters")

        # 再次检查，第一个应该被跳过
        units2 = [
            {"title": "Chapter 1", "content": "Content A"},
            {"title": "Chapter 2", "content": "Content B"}
        ]
        new_units2, skipped2 = self.manager.get_incremental_units(units2, "characters")
        self.assertEqual(len(new_units2), 1)
        self.assertEqual(len(skipped2), 1)
        self.assertEqual(new_units2[0]["title"], "Chapter 2")

    def test_analysis_state_export_import(self):
        """测试分析状态导出和导入"""
        # 添加一些分析记录
        self.manager.mark_analyzed("hash1", "characters")
        self.manager.mark_analyzed("hash2", "characters")
        self.manager.mark_analyzed("hash3", "outline")

        # 导出
        state = self.manager.export_analysis_state()
        self.assertIn("analyzed_hashes", state)
        self.assertEqual(len(state["analyzed_hashes"]["characters"]), 2)
        self.assertEqual(len(state["analyzed_hashes"]["outline"]), 1)

        # 创建新实例并导入
        new_manager = ReverseEngineeringManager(self.mock_ai_client)
        new_manager.import_analysis_state(state)

        progress = new_manager.get_analysis_progress()
        self.assertEqual(progress["characters"], 2)
        self.assertEqual(progress["outline"], 1)

class TestAnalysisContext(unittest.TestCase):
    """测试长上下文功能"""

    def test_add_characters(self):
        """测试添加角色到上下文"""
        ctx = AnalysisContext()
        ctx.add_characters(["Alice", "Bob"])
        ctx.add_characters(["Alice", "Charlie"])  # Alice 重复

        self.assertEqual(len(ctx.known_characters), 3)
        self.assertIn("Alice", ctx.known_characters)
        self.assertIn("Bob", ctx.known_characters)
        self.assertIn("Charlie", ctx.known_characters)

    def test_add_entities(self):
        """测试添加设定到上下文"""
        ctx = AnalysisContext()
        ctx.add_entities(["魔法学院", "龙之谷"])
        ctx.add_entities(["魔法学院", "精灵森林"])  # 魔法学院重复

        self.assertEqual(len(ctx.known_entities), 3)

    def test_add_chapter_summary(self):
        """测试添加章节摘要"""
        ctx = AnalysisContext()
        ctx.add_chapter_summary("第一章", "主角踏上冒险之旅")
        ctx.add_chapter_summary("第二章", "遇到了神秘的导师")

        self.assertEqual(len(ctx.chapter_summaries), 2)
        self.assertIn("第一章", ctx.rolling_summary)
        self.assertIn("第二章", ctx.rolling_summary)

    def test_rolling_summary_max_chapters(self):
        """测试滚动摘要只保留最近N个章节"""
        ctx = AnalysisContext()
        ctx.max_chapters_in_summary = 3

        for i in range(6):
            ctx.add_chapter_summary(f"第{i+1}章", f"内容{i+1}")

        # 应该只保留最后3个章节
        self.assertEqual(len(ctx.chapter_summaries), 3)
        self.assertIn("第4章", ctx.rolling_summary)
        self.assertIn("第5章", ctx.rolling_summary)
        self.assertIn("第6章", ctx.rolling_summary)
        self.assertNotIn("第1章", ctx.rolling_summary)

    def test_get_context_prompt_characters(self):
        """测试生成角色分析的上下文提示"""
        ctx = AnalysisContext()
        ctx.add_characters(["小明", "小红"])
        ctx.add_chapter_summary("序章", "故事开始")

        prompt = ctx.get_context_prompt("characters")

        self.assertIn("【已知角色】", prompt)
        self.assertIn("小明", prompt)
        self.assertIn("小红", prompt)
        self.assertIn("【前情提要】", prompt)

    def test_get_context_prompt_wiki(self):
        """测试生成设定分析的上下文提示"""
        ctx = AnalysisContext()
        ctx.add_entities(["魔法学院"])

        prompt = ctx.get_context_prompt("wiki")

        self.assertIn("【已知设定】", prompt)
        self.assertIn("魔法学院", prompt)

    def test_get_context_prompt_style_no_context(self):
        """测试文笔分析不需要上下文"""
        ctx = AnalysisContext()
        ctx.add_characters(["小明"])

        prompt = ctx.get_context_prompt("style")

        # style 分析应该返回空字符串
        self.assertEqual(prompt, "")

    def test_context_export_import(self):
        """测试上下文导出和导入"""
        ctx = AnalysisContext()
        ctx.add_characters(["Alice", "Bob"])
        ctx.add_entities(["魔法学院"])
        ctx.add_chapter_summary("第一章", "故事开始")

        # 导出
        data = ctx.to_dict()

        # 导入到新实例
        ctx2 = AnalysisContext.from_dict(data)

        self.assertEqual(ctx2.known_characters, ctx.known_characters)
        self.assertEqual(ctx2.known_entities, ctx.known_entities)
        self.assertEqual(ctx2.rolling_summary, ctx.rolling_summary)
        self.assertEqual(len(ctx2.chapter_summaries), 1)


class TestReverseEngineeringManagerWithContext(unittest.TestCase):
    """测试带上下文的分析功能"""

    def setUp(self):
        self.mock_ai_client = MagicMock()
        self.manager = ReverseEngineeringManager(self.mock_ai_client)

    def test_create_analysis_context(self):
        """测试创建分析上下文"""
        ctx = self.manager.create_analysis_context()
        self.assertIsInstance(ctx, AnalysisContext)
        self.assertEqual(len(ctx.known_characters), 0)

    def test_update_context_from_results_characters(self):
        """测试从分析结果更新上下文 - 角色"""
        ctx = AnalysisContext()
        results = {
            "characters": [
                [{"name": "Alice", "role": "主角"}],
                [{"name": "Bob", "role": "配角"}]
            ]
        }

        self.manager.update_context_from_results(ctx, results, "第一章", "主角Alice登场")

        self.assertIn("Alice", ctx.known_characters)
        self.assertIn("Bob", ctx.known_characters)
        self.assertIn("第一章", ctx.rolling_summary)

    def test_update_context_from_results_wiki(self):
        """测试从分析结果更新上下文 - 设定"""
        ctx = AnalysisContext()
        results = {
            "wiki": [
                [{"name": "魔法学院", "category": "地点"}]
            ]
        }

        self.manager.update_context_from_results(ctx, results, "第一章")

        self.assertIn("魔法学院", ctx.known_entities)

    def test_update_context_from_outline_characters(self):
        """测试从大纲结果提取角色"""
        ctx = AnalysisContext()
        results = {
            "outline": [
                [{"name": "相遇", "content": "...", "characters": ["小明", "小红"]}]
            ]
        }

        self.manager.update_context_from_results(ctx, results, "第一章")

        self.assertIn("小明", ctx.known_characters)
        self.assertIn("小红", ctx.known_characters)

    def test_export_import_context(self):
        """测试上下文导出导入接口"""
        ctx = self.manager.create_analysis_context()
        ctx.add_characters(["Test"])

        data = self.manager.export_context(ctx)
        ctx2 = self.manager.import_context(data)

        self.assertIn("Test", ctx2.known_characters)


if __name__ == '__main__':
    unittest.main()
