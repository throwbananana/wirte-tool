# `wirte-tool` 训练模块问题审查报告

> 仓库：<https://github.com/throwbananana/wirte-tool>  
> 范围：训练模块相关代码静态审查  
> 主要文件：  
> - `writer_app/controllers/training_controller.py`  
> - `writer_app/core/training.py`  
> - `writer_app/core/training_challenges.py`  
> - `writer_app/core/training_history.py`  
> - `writer_app/ui/training_panel.py`  
>
> 说明：本报告基于静态代码审查整理，未运行完整应用流程。

---

## 一、总体结论

训练模块最大的问题不是单个语法错误，而是：

> **挑战配置、训练模式、Prompt 生成、评分逻辑、UI 展示之间没有完全打通。**

也就是说，产品层面已经设计了较丰富的训练模式和挑战系统，但实现层仍然像一个通用写作练习器，导致以下问题：

- 用户选择的是某个明确挑战，但实际生成的训练要求可能偏离挑战目标。
- 挑战题目和随机训练条件可能互相冲突。
- AI 评分与离线评分标准差异很大。
- UI 展示的数据和核心评分使用的数据口径不一致。
- 高级训练模式没有被每日任务、挑战体系充分利用。

---

## 二、主要问题清单

### 1. 挑战关卡与训练模式错配

`training.py` 中定义了很多细分训练模式，例如：

- `dialogue_subtext`
- `character_voice`
- `emotion_infusion`
- `character_persona`
- `character_arc`
- `show_dont_tell`
- `editing`
- `style`
- `sensory`

但 `training_challenges.py` 中部分挑战没有使用这些更准确的模式。

例如一些“对话训练”类挑战，实际仍然可能配置成 `continuation`。这会导致：

- Prompt 生成按“续写”逻辑处理；
- 评分标准按通用续写或通用创作处理；
- 对话训练本应关注的“潜台词、人物声音、对话张力”没有被准确评估。

#### 影响

用户以为自己在做“对话训练”，但系统可能在按“续写训练”评估。

#### 建议修复

给挑战配置增加更明确的评估模式字段，例如：

```python
{
    "mode": "dialogue_subtext",
    "rubric_mode": "dialogue_subtext",
    "required_topic": "...",
}
```

并避免把高级挑战都退化成 `continuation`。

---

### 2. 挑战固定要求会被随机训练条件冲掉

部分挑战本身有明确要求，例如：

- 指定某种写作风格；
- 禁用某种感官；
- 强制使用某种叙事视角；
- 要求特定主题或技巧。

但在训练生成逻辑中，`style` / `sensory` 等模式可能会继续随机生成约束。

这会导致挑战配置和实际 Prompt 出现冲突。

#### 示例风险

假设挑战要求：

> 使用海明威式冰山风格。

但生成逻辑又随机选择另一种风格，那么最终训练要求可能变成混合甚至互相矛盾。

再比如挑战要求：

> 只使用声音和气味，不允许视觉描写。

但随机感官模式可能重新生成其他感官要求，导致挑战规则被弱化。

#### 影响

挑战不再是一个稳定、可复现的训练目标。

#### 建议修复

挑战模式下应该优先使用 challenge 自身的固定配置，例如：

```python
challenge = {
    "mode": "style",
    "required_style": "hemingway",
    "allow_random_style": False,
}
```

Prompt 生成时：

```python
if is_challenge and challenge.required_style:
    use_required_style()
else:
    random_style()
```

---

### 3. 离线生成路径弱化 challenge/topic 信息

`TrainingManager.get_words()` 主要按 `level` 和 `tag` 获取词语；挑战中的 `topic` 信息没有在所有路径中被稳定使用。

当 AI 可用时，Prompt 可能还能围绕挑战主题生成；但当进入离线 fallback 时，系统可能只生成通用关键词。

#### 影响

挑战主题在离线路径下可能失效。

例如用户选择一个关于“城市孤独感”的挑战，但离线生成出的关键词可能和主题没有明显关系。

#### 建议修复

离线 fallback 也应接收 challenge 信息：

```python
get_words(
    level=level,
    tag=tag,
    topic=challenge.topic,
    required_keywords=challenge.required_keywords,
)
```

如果本地词库无法支持主题，应在 UI 或结果中明确提示：

> 当前为离线通用练习，主题约束可能不完整。

---

### 4. AI 评分强依赖返回 JSON 格式，失败时容易误判为低分

AI 评分通常要求模型返回 JSON，例如：

```json
{
  "score_1": 8,
  "score_2": 7,
  "score_3": 8,
  "total": 23,
  "feedback": "..."
}
```

但模型输出并不总是稳定 JSON。

如果解析失败，系统可能得不到有效 `total`，最终挑战完成判断可能失败。

#### 影响

用户作品可能写得不错，但因为 AI 返回格式不规范，被系统当作低分或零分处理。

尤其是挑战完成条件依赖：

```python
total >= min_score
```

时，解析失败会直接影响用户是否通关。

#### 建议修复

评分流程应增加：

1. JSON schema 校验；
2. 自动修复或重试；
3. 解析失败时不应默认为 0 分；
4. UI 应提示“评分失败，请重试”。

示例：

```python
try:
    result = parse_score_json(response)
    validate_score_schema(result)
except ScoreParseError:
    return {
        "status": "score_failed",
        "message": "评分结果解析失败，请重试。",
        "raw_response": response,
    }
```

---

### 5. 离线评分过于通用，无法准确评价高级训练目标

离线评分主要基于启发式指标，例如：

- 字数；
- 词汇多样性；
- 句子长度；
- 结构完整性。

这些指标适合做基础写作质量估算，但不适合判断：

- 是否体现潜台词；
- 是否符合特定人物口吻；
- 是否完成角色弧光；
- 是否真正做到了“展示而非说明”；
- 是否体现某种指定文风。

#### 影响

AI 评分和离线评分的结果可能差异很大。

用户在离线状态下得到的反馈，不一定能反映挑战目标完成情况。

#### 建议修复

为不同模式设计独立 rubric。

例如 `dialogue_subtext`：

```python
rubric = {
    "subtext": 10,
    "character_voice": 10,
    "conflict_tension": 10,
}
```

`show_dont_tell`：

```python
rubric = {
    "concrete_detail": 10,
    "sensory_action": 10,
    "avoid_direct_explanation": 10,
}
```

离线模式至少应根据 mode 使用不同规则，而不是所有训练统一套一组基础指标。

---

### 6. 日常任务没有覆盖完整训练模式

`MODES` 中定义了不少训练模式，但 daily quest 只覆盖了部分基础模式，例如：

- `keywords`
- `brainstorm`
- `style`
- `sensory`
- `show_dont_tell`
- `editing`

一些更高级的模式没有进入每日任务系统，例如：

- `dialogue_subtext`
- `character_voice`
- `emotion_infusion`
- `character_persona`
- `character_arc`

#### 影响

系统看起来训练类型很多，但用户日常实际接触到的训练类型偏少。

长期使用时训练内容容易重复，难以形成完整成长路径。

#### 建议修复

将 daily quest 改成按训练阶段分层抽取：

```python
daily_pool = {
    "beginner": ["keywords", "sensory", "show_dont_tell"],
    "intermediate": ["style", "editing", "dialogue_subtext"],
    "advanced": ["character_voice", "character_arc", "emotion_infusion"],
}
```

---

### 7. UI 字数统计与核心评分口径不一致

UI 面板中可能直接使用：

```python
len(content)
```

来统计“字数”。

但核心评分逻辑中使用的是类似 `TextMetrics.count_words(content)` 的统计方式。

#### 影响

用户看到的字数和评分系统实际使用的文本量可能不一致。

尤其是中文场景下，`len(content)` 会把：

- 标点；
- 空格；
- 换行；
- 英文字符；

都简单计入长度。

这不一定等同于训练目标中的“字数”。

#### 建议修复

UI 和评分统一使用同一个统计函数：

```python
word_count = TextMetrics.count_words(content)
```

并在 UI 中明确显示：

- 字数；
- 字符数；
- 目标完成度。

---

### 8. 训练历史保留策略可能影响长期统计

训练历史模块默认只保留有限数量的记录。

这可能不是 bug，但会影响：

- 长期趋势分析；
- 连续训练统计；
- 用户成长曲线；
- 挑战复盘。

#### 影响

如果历史记录被截断，系统无法可靠生成长期训练分析。

#### 建议修复

区分两类数据：

1. 详细训练记录：可以限制条数；
2. 聚合统计数据：应长期保存。

例如：

```python
history_records = last_200_sessions
aggregate_stats = {
    "total_sessions": 1234,
    "mode_stats": {...},
    "weekly_scores": {...},
}
```

---

## 三、建议的修复优先级

### P0：必须优先修

#### 1. 修复挑战模式与评分模式错配

问题核心：

```text
挑战目标 ≠ 训练模式 ≠ 评分标准
```

建议新增字段：

```python
mode
rubric_mode
required_topic
required_style
sensory_constraint
```

并在 Prompt 和评分阶段统一使用。

---

#### 2. 挑战模式下禁止随机条件覆盖固定要求

挑战配置应该是最高优先级。

推荐逻辑：

```python
if is_challenge:
    use_challenge_constraints()
else:
    use_random_training_constraints()
```

---

#### 3. AI 评分解析失败不能按 0 分处理

解析失败应该是评分失败，不是作品失败。

推荐状态：

```python
{
    "status": "score_failed",
    "retryable": True,
}
```

---

## 四、P1：建议尽快修

### 1. 离线 fallback 支持 topic 和 challenge 信息

避免离线状态下挑战主题完全丢失。

### 2. 为不同 mode 设计独立评分 rubric

不要让所有训练都使用同一套通用文本指标。

### 3. UI 统计口径统一

避免用户看到的字数和系统实际评分使用的字数不同。

---

## 五、P2：后续优化

### 1. 扩展 daily quest 覆盖范围

把高级训练模式纳入每日任务。

### 2. 改善训练历史存储结构

保留长期聚合统计，详细记录可截断。

### 3. 增加训练模式测试用例

建议至少覆盖：

- 每种 mode 是否生成对应 prompt；
- 每个 challenge 是否使用正确 mode；
- challenge 固定约束是否不会被随机覆盖；
- AI 评分 JSON 解析失败是否安全处理；
- 离线 fallback 是否保留 topic 信息；
- UI 字数统计是否与核心统计一致。

---

## 六、建议测试用例

### 1. Challenge mode 映射测试

```python
def test_dialogue_challenge_uses_dialogue_mode():
    challenge = get_challenge("dialogue_subtext")
    assert challenge["mode"] == "dialogue_subtext"
```

---

### 2. 固定风格不被随机覆盖

```python
def test_challenge_required_style_not_overridden():
    challenge = {
        "mode": "style",
        "required_style": "hemingway",
    }

    prompt = generate_prompt(challenge=challenge, is_challenge=True)

    assert "hemingway" in prompt.lower()
    assert not contains_random_style(prompt)
```

---

### 3. AI 评分解析失败不返回 0 分

```python
def test_score_parse_failure_is_retryable():
    response = "这是一段非 JSON 文本"

    result = parse_ai_score(response)

    assert result["status"] == "score_failed"
    assert result["retryable"] is True
```

---

### 4. UI 和核心统计一致

```python
def test_ui_word_count_matches_core_metrics():
    content = "他推开门，雨声落在身后。"

    ui_count = get_ui_word_count(content)
    core_count = TextMetrics.count_words(content)

    assert ui_count == core_count
```

---

## 七、推荐重构方向

建议将训练模块拆成四层：

```text
Challenge Definition
        ↓
Prompt Builder
        ↓
Scoring Rubric
        ↓
UI Display / History
```

每一层都显式接收同一个 `TrainingSessionConfig`：

```python
@dataclass
class TrainingSessionConfig:
    mode: str
    level: int
    topic: str | None
    challenge_id: str | None
    required_style: str | None
    sensory_constraint: dict | None
    rubric_mode: str
    min_score: int | None
```

这样可以避免当前的问题：

- challenge 写了一套；
- prompt 生成随机一套；
- scoring 又按另一套；
- UI 展示再按自己的口径。

---

## 八、最终结论

训练模块目前的问题可以概括为：

> **它已经有“训练系统”的产品设计，但实现上还没有形成严格一致的训练协议。**

最需要修的是：

1. 挑战目标和训练模式统一；
2. Prompt 生成不能随机覆盖挑战要求；
3. 评分 rubric 必须和 mode/challenge 对齐；
4. AI 评分失败要有可靠降级逻辑；
5. UI 与核心统计使用同一套指标。

修完这些后，训练模块会从“随机写作练习器”更接近真正的“分层写作训练系统”。
