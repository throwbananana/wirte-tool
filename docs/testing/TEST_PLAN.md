# Writer Tool v4.1 - Feature Tests

This document tracks the verification of the newly implemented features.

## 1. Drag and Drop Reordering (Mind Map)
- [ ] **Reparent:** Drag Node A onto Node B -> A becomes child of B.
- [ ] **Insert Before:** Drag Node A to top edge of Node B -> A becomes sibling before B.
- [ ] **Insert After:** Drag Node A to bottom edge of Node B -> A becomes sibling after B.
- [ ] **Undo/Redo:** Ctrl+Z undoes the move, Ctrl+Y redoes it.

## 2. Multimedia Support
- [ ] **Character Image:** Edit Character -> Browse Image -> Save. Re-open to verify persistence.
- [ ] **Scene Image:** Edit Scene -> Browse Image -> Save. Re-open to verify persistence.

## 3. Relationship Map
- [ ] **Tab:** "人物关系图" tab exists.
- [ ] **Auto-population:** Characters appear as nodes.
- [ ] **Layout:** Nodes can be dragged and stay there (refresh persists layout in memory).
- [ ] **Linking:** Right-click Node A -> "Connect to..." -> Click Node B -> Input Label -> Link appears.
- [ ] **Image Display:** Character nodes show the image selected in Step 2.

## 4. Project Chat (RAG)
- [ ] **Tab:** "项目对话" tab exists.
- [ ] **Context:** Send "What are the characters?" -> AI answers based on project data.
- [ ] **History:** Messages persist in the session.

## 5. Ren'Py Export
- [ ] **Menu:** File -> Export to Ren'Py Project.
- [ ] **Output:** Folder created with `game/script.rpy` and `game/images/`.
- [ ] **Content:** `script.rpy` contains character definitions and scene labels.
- [ ] **Images:** Selected images are copied to `game/images/`.
