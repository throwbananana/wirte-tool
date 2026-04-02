# Test Plan: Reverse Engineering Expansion

## 1. Dual Timeline Extraction
- **Objective:** Verify AI correctly extracts `truth` vs `lie` events and timestamps.
- **Input:** A text snippet with a character lying about their alibi.
    - Example: "It was 10:00 PM. I was at the bar." (Lie) vs Narrator: "At 10:00 PM, he was actually at the crime scene." (Truth)
- **Expected Result:**
    - AI returns JSON with two events.
    - One `type="lie"` at 10:00 PM.
    - One `type="truth"` at 10:00 PM.
    - UI displays these in "Dual Timeline" tab.
    - "Apply" button correctly inserts them into `ProjectManager.project_data["timelines"]`.

## 2. Relationships & Factions
- **Objective:** Verify "Faction" target type is detected and handled.
- **Input:** Text mentioning "Alice is a member of the Shadow Guild."
- **Expected Result:**
    - AI returns relationship: `source="Alice"`, `target="Shadow Guild"`, `target_type="faction"`.
    - UI shows "Faction" column.
    - "Apply" button:
        - Creates "Shadow Guild" in `factions` list if not exists.
        - Creates a link in `relationships` with orange color (or distinct visual).

## 3. Style Preset
- **Objective:** Verify style analysis can be saved as a preset.
- **Input:** Sample text with distinct style (e.g. Noir).
- **Expected Result:**
    - UI shows style analysis.
    - "Apply" button saves the text to `project_data["meta"]["ai_context"]["style_preset"]`.
    - User receives confirmation "Style Saved".

## 4. UI Layout & Stability
- **Objective:** Ensure new tabs and controls render correctly.
- **Check:**
    - "Extract Dual Timeline" checkbox exists.
    - "Timeline" tab exists in result preview.
    - Tables render with correct columns.
