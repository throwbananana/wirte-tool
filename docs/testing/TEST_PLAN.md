# Writer Tool 测试计划

测试文档已拆成两层：

1. 发布前必须完成的最小闸门
2. 可以继续推进但不会阻塞当前版本的 Beta 验证

## 发布闸门

查看 `docs/testing/RELEASE_BLOCKERS.md`

## Beta 验证

查看 `docs/testing/BETA_VALIDATION.md`

## 专项验证文档

- `docs/testing/TEST_PLAN_CHAR_EVENTS.md`
- `docs/testing/TEST_PLAN_REVERSE_ENGINEER_V2.md`
- `docs/testing/TEST_PLAN_WIKI_V2.md`

## 自动化基线

- 本地：`python -m unittest discover tests`
- CI：`.github/workflows/ci.yml`
