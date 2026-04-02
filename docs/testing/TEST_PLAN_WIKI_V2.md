# Test Plan: Wiki Expansion V2

## 1. Automatic Synchronization (Sync)
- **Objective:** Verify Wiki entries are auto-created/updated/deleted when Characters are modified.
- **Steps:**
    1. **Create Character:**
        - Go to Script -> Characters.
        - Add new character "WikiSyncTest".
        - Go to Wiki tab.
        - **Expect:** New entry "WikiSyncTest" exists in "人物" category.
    2. **Rename Character:**
        - Go to Script -> Characters.
        - Edit "WikiSyncTest" -> rename to "WikiSyncRenamed".
        - Go to Wiki tab.
        - **Expect:** Entry is now "WikiSyncRenamed".
    3. **Delete Character:**
        - Go to Script -> Characters.
        - Delete "WikiSyncRenamed".
        - Go to Wiki tab.
        - **Expect:** Entry is renamed to "WikiSyncRenamed [已删除]" (or deleted if we chose that path, but code does rename).

## 2. Hyperlinked Keywords
- **Objective:** Verify text in Wiki editor automatically links to other existing entries.
- **Prerequisites:**
    - Entry A: "Ancient Sword"
    - Entry B: "Hero"
- **Steps:**
    1. Select "Hero".
    2. Type in content: "The Hero wields the Ancient Sword in battle."
    3. **Expect:** "Ancient Sword" automatically turns blue and underlined.
    4. Click on "Ancient Sword".
    5. **Expect:** Selection jumps to "Ancient Sword" entry.

## 3. Conflict Check
- **Objective:** Verify consistency checker runs.
- **Steps:**
    - Click "设定冲突检查".
    - **Expect:** AI analyzes and returns report (if API configured).
