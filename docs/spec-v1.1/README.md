# Engineering Specification v1.1（纲要参考包）

本包是蓝图对话产出的**纲要参考**。自 2026-07-26 起，权威基线如下：

- **Project Constitution** → `../constitution.md`（本包的 00-project-constitution 已被取代并移除）
- **ADR** → `../adr/`（本包 ADR-001~009 已扩写并重编号为 ADR-015~022；
  其 ADR-008 Scene DSL 已由本仓库 ADR-014 覆盖）
- 其余文档（product/system architecture、domain、api、runtime、agents、
  ai-system、content、engineering、roadmap）保留在此作为背景参考；
  与本仓库 contracts/schemas 冲突时，以仓库内 schema 文件为准。

注意：本包多数文档为 4–20 行纲要，不足以单独作为开发规范；
具体开发以 constitution + ADR + schemas + 测试为准。
