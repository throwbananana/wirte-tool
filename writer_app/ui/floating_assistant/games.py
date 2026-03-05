"""
悬浮写作助手 - 小游戏模块
包含猜数字、猜词、快速反应等休闲小游戏
"""
import random
import time
from typing import List, Dict, Optional, Callable, Tuple
from dataclasses import dataclass
from enum import Enum


class GameType(Enum):
    """游戏类型"""
    GUESS_NUMBER = "guess_number"
    WORD_CHAIN = "word_chain"
    ROCK_PAPER_SCISSORS = "rock_paper_scissors"
    WORD_ASSOCIATION = "word_association"
    STORY_CONTINUE = "story_continue"


@dataclass
class GameState:
    """游戏状态"""
    game_type: GameType
    active: bool = False
    score: int = 0
    attempts: int = 0
    max_attempts: int = 0
    data: Dict = None  # 游戏特定数据

    def __post_init__(self):
        if self.data is None:
            self.data = {}


class GuessNumberGame:
    """猜数字游戏"""

    def __init__(self, min_num: int = 1, max_num: int = 100, max_attempts: int = 7):
        self.min_num = min_num
        self.max_num = max_num
        self.max_attempts = max_attempts
        self.target = 0
        self.attempts = 0
        self.history: List[Tuple[int, str]] = []
        self.active = False

    def start(self) -> str:
        """开始游戏"""
        self.target = random.randint(self.min_num, self.max_num)
        self.attempts = 0
        self.history.clear()
        self.active = True

        return (f"🎮 猜数字游戏开始！\n"
                f"我想了一个 {self.min_num}~{self.max_num} 之间的数字\n"
                f"你有 {self.max_attempts} 次机会，来猜猜看！")

    def guess(self, number: int) -> Tuple[bool, str]:
        """
        猜测

        Returns:
            (是否胜利, 提示信息)
        """
        if not self.active:
            return False, "游戏还没开始哦~"

        self.attempts += 1

        if number == self.target:
            self.active = False
            self.history.append((number, "正确"))
            return True, (f"🎉 恭喜你猜对了！答案就是 {self.target}\n"
                          f"你用了 {self.attempts} 次机会！")

        if self.attempts >= self.max_attempts:
            self.active = False
            hint = "大了" if number > self.target else "小了"
            self.history.append((number, hint))
            return False, (f"😢 很遗憾，机会用完了~\n"
                           f"答案是 {self.target}\n"
                           f"下次加油！")

        if number > self.target:
            hint = "大了"
            emoji = "📉"
        else:
            hint = "小了"
            emoji = "📈"

        self.history.append((number, hint))
        remaining = self.max_attempts - self.attempts

        return False, f"{emoji} {number} {hint}！还有 {remaining} 次机会"

    def get_hint(self) -> str:
        """获取提示"""
        if not self.active:
            return "游戏还没开始"

        # 根据历史猜测给出范围提示
        low = self.min_num
        high = self.max_num

        for num, hint in self.history:
            if hint == "大了" and num < high:
                high = num - 1
            elif hint == "小了" and num > low:
                low = num + 1

        return f"💡 提示：答案在 {low}~{high} 之间"


class RockPaperScissorsGame:
    """石头剪刀布"""

    CHOICES = ["石头", "剪刀", "布"]
    CHOICE_EMOJIS = {"石头": "✊", "剪刀": "✌️", "布": "🖐️"}

    def __init__(self):
        self.player_wins = 0
        self.assistant_wins = 0
        self.draws = 0

    def play(self, player_choice: str) -> Tuple[str, str, str]:
        """
        进行一局

        Args:
            player_choice: 玩家选择

        Returns:
            (助手选择, 结果, 描述)
        """
        if player_choice not in self.CHOICES:
            return "", "invalid", "请选择：石头、剪刀、布"

        assistant_choice = random.choice(self.CHOICES)

        # 判断结果
        if player_choice == assistant_choice:
            self.draws += 1
            result = "draw"
            desc = f"{self.CHOICE_EMOJIS[player_choice]} vs {self.CHOICE_EMOJIS[assistant_choice]}\n🤝 平局！"
        elif ((player_choice == "石头" and assistant_choice == "剪刀") or
              (player_choice == "剪刀" and assistant_choice == "布") or
              (player_choice == "布" and assistant_choice == "石头")):
            self.player_wins += 1
            result = "win"
            desc = f"{self.CHOICE_EMOJIS[player_choice]} vs {self.CHOICE_EMOJIS[assistant_choice]}\n🎉 你赢了！"
        else:
            self.assistant_wins += 1
            result = "lose"
            desc = f"{self.CHOICE_EMOJIS[player_choice]} vs {self.CHOICE_EMOJIS[assistant_choice]}\n😊 我赢了~"

        return assistant_choice, result, desc

    def get_score(self) -> str:
        """获取比分"""
        total = self.player_wins + self.assistant_wins + self.draws
        return (f"📊 比分统计（共 {total} 局）\n"
                f"你: {self.player_wins} 胜\n"
                f"我: {self.assistant_wins} 胜\n"
                f"平局: {self.draws}")

    def reset(self):
        """重置比分"""
        self.player_wins = 0
        self.assistant_wins = 0
        self.draws = 0


class WordChainGame:
    """成语接龙"""

    # 常用成语库
    IDIOMS = [
        "一心一意", "意气风发", "发扬光大", "大显身手", "手到擒来",
        "来日方长", "长话短说", "说三道四", "四面八方", "方兴未艾",
        "爱屋及乌", "乌合之众", "众志成城", "城门失火", "火上浇油",
        "油然而生", "生龙活虎", "虎头蛇尾", "尾大不掉", "掉以轻心",
        "心花怒放", "放虎归山", "山清水秀", "秀外慧中", "中流砥柱",
        "柱天踏地", "地大物博", "博学多才", "才华横溢", "溢于言表",
        "表里如一", "一举两得", "得天独厚", "厚德载物", "物是人非",
        "非同小可", "可歌可泣", "泣不成声", "声东击西", "西风残照",
        "照本宣科", "科班出身", "身先士卒", "卒章显志", "志同道合",
        "合二为一", "一帆风顺", "顺水推舟", "舟车劳顿", "顿开茅塞",
    ]

    def __init__(self):
        self.chain: List[str] = []
        self.active = False
        self.player_turn = True
        self.used_idioms: set = set()

    def start(self, first_idiom: str = None) -> str:
        """开始游戏"""
        self.chain.clear()
        self.used_idioms.clear()
        self.active = True
        self.player_turn = True

        if first_idiom:
            if len(first_idiom) != 4:
                return "请输入四字成语哦~"
            self.chain.append(first_idiom)
            self.used_idioms.add(first_idiom)
            self.player_turn = False

            # 助手接龙
            return self._assistant_turn()
        else:
            # 助手先出
            start = random.choice(self.IDIOMS)
            self.chain.append(start)
            self.used_idioms.add(start)
            return f"🎮 成语接龙开始！\n我先出：「{start}」\n请接「{start[-1]}」开头的成语~"

    def play(self, idiom: str) -> Tuple[bool, str]:
        """
        玩家接龙

        Returns:
            (是否有效, 响应消息)
        """
        if not self.active:
            return False, "游戏还没开始，输入「接龙」开始游戏~"

        if len(idiom) != 4:
            return False, "请输入四字成语~"

        if idiom in self.used_idioms:
            return False, f"「{idiom}」已经用过了，换一个吧~"

        # 检查是否能接上
        if self.chain:
            last_char = self.chain[-1][-1]
            if idiom[0] != last_char:
                return False, f"要接「{last_char}」开头的成语哦~"

        self.chain.append(idiom)
        self.used_idioms.add(idiom)
        self.player_turn = False

        # 助手接龙
        return True, self._assistant_turn()

    def _assistant_turn(self) -> str:
        """助手接龙"""
        if not self.chain:
            return ""

        last_char = self.chain[-1][-1]

        # 找能接上的成语
        candidates = [i for i in self.IDIOMS
                      if i[0] == last_char and i not in self.used_idioms]

        if not candidates:
            self.active = False
            return (f"我接不上了...😅\n"
                    f"🎉 恭喜你赢了！\n"
                    f"共接了 {len(self.chain)} 个成语")

        choice = random.choice(candidates)
        self.chain.append(choice)
        self.used_idioms.add(choice)
        self.player_turn = True

        return f"我接：「{choice}」\n请接「{choice[-1]}」开头的成语~"

    def get_chain(self) -> str:
        """获取当前接龙链"""
        if not self.chain:
            return "还没开始接龙~"
        return " → ".join(self.chain)

    def give_up(self) -> str:
        """放弃"""
        self.active = False
        return (f"游戏结束~\n"
                f"共接了 {len(self.chain)} 个成语\n"
                f"接龙链：{self.get_chain()}")


class WordAssociationGame:
    """词语联想游戏"""

    # 联想词库
    WORD_PAIRS = [
        ("太阳", ["月亮", "光", "温暖", "早晨", "东方"]),
        ("大海", ["沙滩", "波浪", "蓝色", "船", "鱼"]),
        ("书本", ["知识", "阅读", "文字", "图书馆", "作家"]),
        ("音乐", ["歌曲", "乐器", "旋律", "节奏", "演奏"]),
        ("春天", ["花", "温暖", "绿色", "鸟", "播种"]),
        ("电脑", ["键盘", "屏幕", "网络", "程序", "科技"]),
        ("美食", ["味道", "厨师", "餐厅", "享受", "烹饪"]),
        ("旅行", ["风景", "行李", "火车", "飞机", "冒险"]),
        ("梦想", ["未来", "努力", "实现", "希望", "追求"]),
        ("友情", ["朋友", "陪伴", "信任", "快乐", "珍贵"]),
    ]

    def __init__(self):
        self.current_word = ""
        self.expected_answers: List[str] = []
        self.score = 0
        self.rounds = 0
        self.active = False

    def start(self) -> str:
        """开始游戏"""
        self.score = 0
        self.rounds = 0
        self.active = True
        return self._next_round()

    def _next_round(self) -> str:
        """下一轮"""
        word, answers = random.choice(self.WORD_PAIRS)
        self.current_word = word
        self.expected_answers = answers
        self.rounds += 1

        return (f"🎮 词语联想 第{self.rounds}轮\n"
                f"看到「{word}」你会想到什么？\n"
                f"（输入一个词语）")

    def guess(self, answer: str) -> Tuple[bool, str]:
        """
        回答

        Returns:
            (是否正确, 响应消息)
        """
        if not self.active:
            return False, "游戏还没开始~"

        answer = answer.strip()

        # 检查答案是否在预期范围内
        is_correct = any(a in answer or answer in a for a in self.expected_answers)

        if is_correct:
            self.score += 1
            result = f"✓ 不错！「{answer}」和「{self.current_word}」确实有关联~\n当前得分: {self.score}"
        else:
            result = f"嗯...「{answer}」似乎关联不太明显\n参考答案: {', '.join(self.expected_answers[:3])}"

        # 继续下一轮或结束
        if self.rounds >= 5:
            self.active = False
            return is_correct, f"{result}\n\n🎮 游戏结束！最终得分: {self.score}/5"

        return is_correct, f"{result}\n\n{self._next_round()}"


class StoryGame:
    """故事接龙游戏"""

    STORY_STARTERS = [
        "那是一个风雨交加的夜晚，",
        "当我推开那扇尘封已久的门，",
        "她从未想过会在这里遇见他，",
        "这封信改变了一切，",
        "时间仿佛在那一刻静止了，",
        "没人相信，但我亲眼所见，",
        "如果能重来一次，",
        "深夜的电话铃声突然响起，",
    ]

    def __init__(self):
        self.story_parts: List[str] = []
        self.active = False
        self.player_turn = True

    def start(self) -> str:
        """开始故事"""
        self.story_parts.clear()
        self.active = True

        starter = random.choice(self.STORY_STARTERS)
        self.story_parts.append(starter)
        self.player_turn = True

        return (f"📖 故事接龙开始！\n\n"
                f"「{starter}」\n\n"
                f"请继续写下去~（20-50字）")

    def continue_story(self, content: str) -> str:
        """继续故事"""
        if not self.active:
            return "故事还没开始，输入「故事」开始创作~"

        if len(content) < 10:
            return "写得太短了，再多写一点~"

        if len(content) > 100:
            content = content[:100] + "..."

        self.story_parts.append(content)
        self.player_turn = False

        # 助手续写
        return self._assistant_continue()

    def _assistant_continue(self) -> str:
        """助手续写"""
        # 简单的续写模板
        continuations = [
            "然而事情并没有那么简单，",
            "正当此时，一个意想不到的人出现了，",
            "回忆涌上心头，",
            "这让所有人都大吃一惊，",
            "沉默片刻后，",
            "命运的齿轮开始转动，",
        ]

        continuation = random.choice(continuations)
        self.story_parts.append(continuation)
        self.player_turn = True

        current_story = "".join(self.story_parts)

        if len(self.story_parts) >= 8:
            self.active = False
            return (f"我接：「{continuation}」\n\n"
                    f"📖 故事结束！完整故事：\n\n{current_story}")

        return f"我接：「{continuation}」\n\n请继续~"

    def get_story(self) -> str:
        """获取当前故事"""
        return "".join(self.story_parts)

    def end_story(self) -> str:
        """结束故事"""
        self.active = False
        return f"📖 故事完成！\n\n{self.get_story()}"


class MiniGameManager:
    """小游戏管理器"""

    def __init__(self):
        self.guess_number = GuessNumberGame()
        self.rps = RockPaperScissorsGame()
        self.word_chain = WordChainGame()
        self.word_association = WordAssociationGame()
        self.story_game = StoryGame()

        self.current_game: Optional[str] = None
        self.total_wins = 0

    def get_available_games(self) -> List[Tuple[str, str]]:
        """获取可用游戏列表"""
        return [
            ("猜数字", "guess_number"),
            ("石头剪刀布", "rps"),
            ("成语接龙", "word_chain"),
            ("词语联想", "word_association"),
            ("故事接龙", "story"),
        ]

    def start_game(self, game_id: str) -> str:
        """开始游戏"""
        self.current_game = game_id

        if game_id == "guess_number":
            return self.guess_number.start()
        elif game_id == "rps":
            return "🎮 石头剪刀布！\n请出：石头、剪刀、布"
        elif game_id == "word_chain":
            return self.word_chain.start()
        elif game_id == "word_association":
            return self.word_association.start()
        elif game_id == "story":
            return self.story_game.start()
        else:
            return "未知游戏"

    def play(self, input_text: str) -> Tuple[bool, str, bool]:
        """
        游戏输入

        Returns:
            (是否有效输入, 响应消息, 是否获胜)
        """
        if not self.current_game:
            return False, "没有进行中的游戏", False

        game = self.current_game
        win = False

        if game == "guess_number":
            try:
                num = int(input_text)
                win, msg = self.guess_number.guess(num)
            except ValueError:
                return False, "请输入数字~", False

        elif game == "rps":
            _, result, msg = self.rps.play(input_text)
            win = result == "win"

        elif game == "word_chain":
            _, msg = self.word_chain.play(input_text)
            win = "恭喜你赢了" in msg

        elif game == "word_association":
            win, msg = self.word_association.guess(input_text)

        elif game == "story":
            msg = self.story_game.continue_story(input_text)
            win = False

        else:
            return False, "未知游戏", False

        if win:
            self.total_wins += 1

        # 检查游戏是否结束
        if not self._is_game_active():
            self.current_game = None

        return True, msg, win

    def _is_game_active(self) -> bool:
        """检查当前游戏是否仍在进行"""
        if not self.current_game:
            return False

        game = self.current_game
        if game == "guess_number":
            return self.guess_number.active
        elif game == "rps":
            return True  # 石头剪刀布始终可以继续
        elif game == "word_chain":
            return self.word_chain.active
        elif game == "word_association":
            return self.word_association.active
        elif game == "story":
            return self.story_game.active
        return False

    def quit_game(self) -> str:
        """退出当前游戏"""
        if not self.current_game:
            return "没有进行中的游戏"

        game = self.current_game
        self.current_game = None

        if game == "word_chain":
            return self.word_chain.give_up()
        elif game == "story":
            return self.story_game.end_story()
        else:
            return "游戏已结束~"
