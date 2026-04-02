# Test Plan: Character Event Table & Reverse Inference

## 1. Character Event Table UI
- [ ] Open app, verify new tab "人物事件" (Character Events) exists.
- [ ] Verify layout: Left list (Characters), Right table (Events).
- [ ] Select a character from the list.
- [ ] Click "添加事件" (Add Event):
    - Enter Time: "Year 2023"
    - Enter Content: "Met Alice"
    - Select Type: "转折点"
    - Save.
- [ ] Verify event appears in the table.
- [ ] Select the event, click "编辑" (Edit). Modify content. Save. Verify update.
- [ ] Select the event, click "删除" (Delete). Verify removal.

## 2. Reverse Engineering Integration
- [ ] Go to "反推导学习" (Reverse Engineering) tab.
- [ ] Load a sample text (or snippet).
- [ ] Check "提取大纲 (Outline)" and "提取角色 (Characters)".
- [ ] Start Analysis.
- [ ] Click "应用选定结果" (Apply Results).
- [ ] **Expectation:** Dialog asks "Mount events to Character Timeline?".
- [ ] Click "Yes".
- [ ] Go to "人物事件" tab.
- [ ] Select a character mentioned in the analysis.
- [ ] **Expectation:** Events from the analysis (Outline) should appear in their event list.

## 3. Data Persistence
- [ ] Save Project.
- [ ] Reload Project.
- [ ] Verify Character Events persist.
