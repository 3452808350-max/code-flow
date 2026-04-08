# AI Harness Engineering & Context Management MindMap

## 📋 核心问题

```markdown
# 问题链：从 Harness Engineering 到 Context 管理

## 问题1: Harness vs 传统 AI 工程
├── 模型为中心 vs 环境/框架为中心
├── 优化模型能力 vs 约束 Agent 行为
└── 失败模式不同
│   ├── 传统：模型不懂 → 训练/微调
│   └── Harness：Agent 乱操作 → 加护栏

## 问题2: NLAH 第一性原理
├── 为什么 Harness 之前都是代码？
│   └── 因为约束需要确定性执行
│   └── 代码是唯一载体
├── 但这有问题
│   ├── 不可移植（运行时绑定）
│   ├── 不可编辑（需编程知识）
│   ├── 不可比较（代码量大难读）
└── NLAH 的突破
    └── 约束写在自然语言里
    └── 智能运行时（LLM）执行
    └── 从"代码实现"到"语义契约"

## 问题3: Context 管理的三重矛盾
├── 矛盾1：干净 Context vs 全局意识
│   └── Token Budget 有限
│   └── 给多就脏，给少就盲
├── 矛盾2：确定性系统 vs 随机性 AI
│   └── 系统需要可预测行为
│   └── AI 本质是概率机器
└── 矛盾3：约束 vs 变通
    └── 约束保证安全
    └── 过约束窒息能力

## 问题4: 筛选标准的本质
├── "什么是真正需要的？"是主观判断
├── 标准太硬 → 系统僵化
└── 标准太软 → 系统失控

## 问题5: 分层管理 vs 扁平 Context
├── 系统分层管理信息
├── AI context 是扁平的（一个 prompt）
└── 如何防止污染？
    └── 注入时机不同导致理解错误
```

---

## 🧠 第一性原理分析

```markdown
# 原理层：问题本质的拆解

## 原理1: Context 的目的是什么？
├── 不是"让 AI 知道更多信息"
└── 而是"让 AI 在当前决策点做出符合全局目标的局部最优选择"
    ├── 子目标1：局部正确（当前操作正确执行）
    └── 子目标2：全局对齐（操作不破坏整体）

## 原理2: Harness 是什么？
├── 一组规则，描述
│   ├── Agent 能做什么（权限）
│   ├── Agent 应该怎么做（流程）
│   └── Agent 不能做什么（禁忌）
└── 规则的本质是语义，不是语法

## 原理3: 为什么之前需要代码？
├── 传统运行时不懂自然语言
└── 只懂代码
└── 现在有 LLM 作为智能运行时
    ├── 能理解自然语言规则
    ├── 能执行这些规则（生成符合规则的代码/行为）

## 原理4: 全局意识 ≠ 全局内容
├── AI 不需要读取所有文件内容
└── 只需要
    ├── 知道有哪些模块（索引层）
    ├── 知道模块间依赖关系（关系图）
    └── 知道当前改动会影响哪些模块（影响分析）
└── 这可以压缩到几百 tokens

## 原理5: 约束的目的
├── 不是"限制 AI"
└── 而是"降低 AI 需要做出的决策复杂度"
    ├── 好的约束 = AI 只需要在有限选项中做选择
    └── 坏的约束 = AI 被 handcuff，无法完成任务

## 原理6: 随机性是特性，不是 bug
├── 随机性提供了
│   ├── 创造性
│   ├── 适应性
│   ├── 多样性
└── 问题：在哪里需要随机性，在哪里不需要？
    ├── 创意区：允许随机（方案设计、代码风格）
    ├── 执行区：限制随机（文件路径、API 调用）
    └── 安全区：禁止随机（权限检查、沙盒边界）
```

---

## 💡 解决方案框架

```markdown
# 方案层：系统设计策略

## 方案1: 分层 Context 策略
├── Layer 0: 结构层（永久保留）
│   ├── AGENTS.md（项目约束）
│   ├── 目录结构（项目骨架）
│   ├── 关键接口定义
│   └── 成本：低（<500 tokens）
├── Layer 1: 任务层（按需加载）
│   ├── 当前任务上下文
│   ├── 相关文件内容
│   └── 成本：中等（动态管理）
├── Layer 2: 历史层（压缩摘要）
│   ├── Session 历史压缩
│   ├── 过往决策摘要
│   └── 成本：压缩后可控
└── Layer 3: 全局层（索引而非内容）
    ├── 项目文件索引（不加载内容）
    ├── 模块关系图（语义图）
    └── 成本：极低（<200 tokens）

## 方案2: 语义标签系统
├── 每条信息打标签
│   ├── type: constraint | goal | context | history | reference
│   ├── scope: global | local | task-specific
│   ├── priority_base: 1-10
│   ├── decay_rate: 时间衰减率
│   └── dependencies: 依赖哪些其他信息
└── 判断流程
    ├── 信息 → 打语义标签
    ├── 任务分类器 → 确定筛选策略
    ├── 动态评分 → priority = base × relevance × decay
    └── 筛选决策 → 按评分排序 + 依赖检查 + 预算截断

## 方案3: 任务分类器（多阶段）
├── 阶段1：规则引擎快速分类（零成本）
│   └── 关键词匹配 → 粗分类
│   └── 如果置信度够高，直接用
├── 阶段2：上下文启发式分类（低成本）
│   └── 基于当前状态推断
│   └── 例如：正在改文件 → execution 类
├── 阶段3：主模型意图声明（中成本，高准确）
│   └── 让主模型先输出意图声明
│   └── "我的意图是：执行一个修复任务..."
└── 阶段4：运行时动态调整
    └── 根据执行过程调整策略

## 方案4: 结构化 Prompt 格式
├── [CONSTRAINTS - 永久约束]
│   └── 约束信息，如 AGENTS.md、权限规则
├── [GOAL - 当前任务]
│   └── 任务目标、预期结果
├── [CONTEXT - 任务相关上下文]
│   └── 相关文件内容、依赖关系
├── [HISTORY - 历史摘要]
│   └── 压缩后的历史对话、决策摘要
└── [REFERENCE - 可用资源索引]
    └── 文件列表、模块索引（不含具体内容）

## 方案5: 固定注入顺序
├── 顺序：constraint → goal → reference → context → history
└── 原因
    ├── 约束先注入 → 建立"不能做什么"框架
    ├── 目标次注入 → 在框架内理解"要做什么"
    ├── 索引再注入 → 知道"有哪些资源可用"
    ├── 内容后注入 → 在框架内选择性理解细节
    └── 历史最后注入 → 知道"之前发生了什么"，不被主导

## 方案6: 动态约束策略
├── 探索性任务
│   ├── 约束：宽松
│   ├── Context：丰富
│   └── 目的：让 AI 有足够信息探索
├── 确定性任务
│   ├── 约束：严格
│   ├── Context：精简
│   └── 目的：让 AI 按既定路径执行
└── 危险任务
    ├── 约束：极严格
    ├── Context：最小必要
    └── 目的：限制破坏范围
```

---

## ✅ 已验证的实现

```markdown
# 验证层：生产级实现对比

## Continuous-Claude-v3 (3676⭐) - 最完整验证
├── Skill Activation Hints
│   ├── ✅ 验证"任务分类器"
│   ├── 方案：规则引擎 + keywords + intentPatterns
│   └── 没有用小模型，用主模型意图声明
├── TLDR 5-layer Code Analysis
│   ├── ✅ 验证"分层 Context"
│   ├── L1:AST → L2:CallGraph → L3:CFG → L4:DFG → L5:Slicing
│   └── 95% token 节省验证
├── Ledger + Handoff 系统
│   ├── ✅ 验证"历史层压缩"
│   ├── YAML 格式高效传输
│   └── Session 状态管理
├── Hooks 系统 (30 hooks)
│   ├── ✅ 验证"固定顺序注入"
│   ├── SessionStart → PreToolUse → PostToolUse → SessionEnd
│   └── 生命周期拦截注入 context
└── Memory System
    ├── ✅ 验证"语义记忆"
    ├── PostgreSQL + pgvector
    └── Daemon 自动提取 learnings

## hoangsa (16⭐) - Context Engineering 系统
├── DAG-Based Execution
│   ├── ✅ 验证"依赖关系检查"
│   ├── 任务 DAG
│   └── 每个 worker bounded context
├── context_pointers
│   ├── ✅ 验证"按需加载"
│   ├── 每个任务只加载需要的文件
│   └── 防止污染
└── Fresh context per task
    ├── ✅ 验证"层级隔离"
    └── 每个 task 在 fresh context window 执行

## agent-mcp-gateway (40⭐) - MCP Context 管理
├── On-Demand Tool Discovery
│   ├── ✅ 验证"按需加载"
│   ├── 90%+ context reduction
│   └── 只加载 3 个 gateway tools
├── Per-Agent Access Control
│   ├── ✅ 验证"语义标签"
│   ├── Policy Engine + deny-before-allow
│   └── agent_id 参数传递身份
└── Wildcard Support
    ├── ✅ 验证"动态约束"
    └── get_*, *_user 等模式匹配

## PromptKit (Microsoft, 32⭐) - 结构化 Prompt
├── 5层组件系统
│   ├── ✅ 验证"结构化 Prompt 格式"
│   ├── Persona → Protocol → Format → Taxonomy → Template
│   └── 组件组装，版本控制
└── Template Chaining
    ├── ✅ 验证"依赖关系"
    └── Pipeline: requirements → design → validation

## claude-rolling-context (8⭐) - 智能修剪
├── Dependency Analysis
│   ├── ✅ 验证"依赖保留"
│   ├── tool_use/tool_result pairs 必须保留
│   ├── parent-child chains 引用关系
└── LLM Summaries
    ├── ✅ 验证"历史层压缩"
    ├── 记忆桥接（memory bridge）
    └── archive boundary message

## Prompt-Programming-Language (0⭐) - DSL
├── ALL_CAPS Sections
│   ├── ✅ 验证"结构化标签"
│   └── [CONSTRAINTS] [GOAL] [CONTEXT] 格式
└── 验证了显式结构帮助 AI 理解层级
```

---

## 🔄 验证状态总结

```markdown
# 验证状态：推理框架的验证程度

| 我推理的概念 | 验证状态 | 已验证的实现 | 说明 |
|--------------|----------|--------------|------|
| 任务分类器 | ✅ 部分验证 | Continuous-Claude-v3 | 规则引擎验证，小模型方案未验证 |
| 语义标签系统 | ✅ 完全验证 | agent-mcp-gateway | Policy Engine + agent_id |
| 动态评分公式 | ⚠️ 未验证 | - | 无直接实现，需进一步验证 |
| 结构化 Prompt | ✅ 完全验证 | PromptKit | 5层组件系统 |
| 固定顺序注入 | ✅ 完全验证 | Hooks 系统 | 30 hooks 生命周期拦截 |
| 依赖关系检查 | ✅ 完全验证 | hoangsa | DAG execution + context_pointers |
| 历史层压缩 | ✅ 完全验证 | Ledger + Handoff | YAML 格式高效传输 |
| 语义隔离标记 | ⚠️ 部分验证 | claude-rolling-context | dependency analysis |
| 分层 Context | ✅ 完全验证 | TLDR 5-layer | 95% token 节省 |
| 动态约束策略 | ✅ 完全验证 | agent-mcp-gateway | deny-before-allow |

## 未验证的部分
├── 动态评分公式
│   └── priority = base × relevance × decay
│   └── 类似实现有向量相似度，但无 decay 因子
└── 小模型分类器
    ├── 主流方案都绕过了小模型
    └── 工程实践中被避免（可靠性问题）
```

---

## 📌 核心洞察

```markdown
# 一句话总结

## Harness Engineering
└── "把 Harness 从'代码实现'提升到'语义契约'"
    └── 执行交给智能运行时（LLM）
    └── 约束留在自然语言

## Context 管理
└── "Context 管理的本质不是'选什么'，而是'在哪一层处理什么'"
    └── 语义层 → 必须保留 → 决定方向
    └── 内容层 → 按需加载 → 支持执行
    └── 历史层 → 压缩摘要 → 提供线索
    └── 索引层 → 永久保留 → 提供坐标

## 约束与变通
└── "随机性在创意层，确定性在执行层，安全在代码层"

## 筛选标准
└── "从'内容'转向'语义'——筛选什么语义必须保留，而非什么内容"
```

---

## 🎯 实现建议

```markdown
# 基于验证结果的实现建议

## 核心
├── 任务分类器 → 规则引擎 + 主模型意图声明（避开小模型）
├── 语义标签 → 参考 agent-mcp-gateway Policy Engine
├── 分层 Context → 参考 TLDR 5-layer 系统
├── 依赖检查 → 参考 hoangsa DAG execution
└── 结构化 Prompt → 参考 PromptKit 组件系统

## 动态评分公式
├── 需要进一步验证
├── 可以先实现基础版本（base + relevance）
└── decay 因子可选

## 整合到现有项目
├── 你的 Context Manager 项目已有基础
│   ├── TokenBudget → 复用
│   ├── PriorityTruncator → 扩展为语义优先级
│   ├── LLMCompressor → 复用为历史层压缩
│   └── MultiAgentContext → 扩展为 DAG execution
└── 新增模块
    ├── SemanticTagger（语义标签）
    ├── PromptAssembler（结构化组装）
    ├── TaskClassifier（规则引擎 + 意图声明）
```

---

*生成时间：2026-04-07*
*基于讨论：Harness Engineering + Context Management 深度分析*