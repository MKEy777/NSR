---
name: claude-md-self-update
description: 每次项目文件变更后必须同步更新 CLAUDE.md
metadata:
  type: feedback
---

在 NSR 项目中，任何文件创建、删除、重命名操作完成后，必须同步更新 `CLAUDE.md` 中的「项目结构」文件清单，确保 CLAUDE.md 始终反映项目当前的实际文件状态。

另外，`大修意见_中英对照.md` 是用户阅读用的，Claude 工作时只需看英文版 `大修意见.md`。

**Why:** 用户要求自动化——不要等用户提醒才更新 CLAUDE.md，而是作为文件操作的收尾步骤主动完成。
**How to apply:** 每次 Write/Edit/Delete 文件后，Read CLAUDE.md 的项目结构部分，如有变化则 Edit 同步。
