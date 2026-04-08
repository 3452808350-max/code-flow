# Harness Architecture Design

> 基于 First-Principles 推理 + 已验证实现的综合设计
> 生成时间: 2026-04-07

---

## 1. 核心定义

### 1.1 Harness 是什么？

**传统定义**: Harness = 测试框架/约束框架（代码实现）

**新定义**: Harness = 语义契约层 + 智能运行时

```
┌─────────────────────────────────────────────────────────────┐
│                    Harness 架构层次                          │
├─────────────────────────────────────────────────────────────┤
│  Layer 4: Natural Language Constraints (NLAH)               │
│           - 用自然语言描述约束                                │
│           - 人类可读、可编辑、可比较                          │
├─────────────────────────────────────────────────────────────┤
│  Layer 3: Semantic Contract Layer                           │
│           - 约束的语义表示（不是语法）                        │
│           - 跨运行时可移植                                    │
├─────────────────────────────────────────────────────────────┤
│  Layer 2: Intelligent Runtime (LLM)                         │
│           - 理解自然语言约束                                  │
│           - 执行约束 → 生成符合约束的代码/行为                 │
├─────────────────────────────────────────────────────────────┤
│  Layer 1: Execution Layer (Tools/Sandbox/State)             │
│           - 实际执行环境                                      │
│           - 确定性边界（沙盒、权限、审计）                     │
├─────────────────────────────────────────────────────────────┤
│  Layer 0: Foundation Layer (Context Management)             │
│           - Token 预算管理                                    │
│           - 上下文选择策略                                    │
│           - 历史压缩/记忆系统                                  │
└─────────────────────────────────────────────────────────────┘
```

### 1.2 Harness vs Agent Framework

| 维度 | Agent Framework | Harness |
|------|-----------------|---------|
| 关注点 | Agent 能做什么 | Agent 不能做什么 + 应该怎么做 |
| 约束方式 | Prompt instructions | 语义契约 + 执行边界 |
| 失败模式 | Agent 不知道怎么做 | Agent 乱操作 → Harness 拦截 |
| 可移植性 | 低（绑定特定 runtime） | 高（语义层独立） |
| 可编辑性 | 需要 prompt 工程技能 | 自然语言可编辑 |

---

## 2. 模块架构

### 2.1 总览

```
┌─────────────────────────────────────────────────────────────────┐
│                      Harness Core System                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐           │
│  │ Constraint   │  │ Context      │  │ Execution    │           │
│  │ Engine       │  │ Manager      │  │ Boundary     │           │
│  │ (语义约束)    │  │ (上下文管理)  │  │ (执行边界)    │           │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘           │
│         │                │                │                     │
│         ▼                ▼                ▼                     │
│  ┌──────────────────────────────────────────────────┐           │
│  │              Orchestrator (调度层)                 │           │
│  │  - Task Classification                           │           │
│  │  - DAG Execution                                 │           │
│  │  - Policy Enforcement                            │           │
│  └──────────────────────────────────────────────────┘           │
│         │                                                        │
│         ▼                                                        │
│  ┌──────────────────────────────────────────────────┐           │
│  │              Agent Runtime (智能运行时)            │           │
│  │  - LLM Interface                                 │           │
│  │  - Tool Gateway                                  │           │
│  │  - State Management                              │           │
│  └──────────────────────────────────────────────────┘           │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 六大核心模块

#### Module 1: Constraint Engine (约束引擎)

**职责**: 管理、解析、执行语义约束

**子模块**:
```
ConstraintEngine
├── ConstraintParser
│   - 解析自然语言约束 → 语义表示
│   - 验证约束一致性
│   - 参考: PromptKit 的 Taxonomy 层
│
├── ConstraintRegistry
│   - 存储所有约束（按类型、作用域）
│   - 约束版本控制
│   - 参考: PromptKit 的 Persona/Protocol 层
│
├── PolicyEngine
│   - deny-before-allow 规则引擎
│   - Wildcard pattern matching
│   - 参考: agent-mcp-gateway 的 Policy Engine
│
└── ConstraintVerifier
    - 运行时验证约束执行
    - 行为-约束一致性检查
```

**约束类型**:
```yaml
constraint_types:
  - type: permission
    scope: global | agent-specific | task-specific
    examples:
      - "禁止删除文件"
      - "只允许读取 /workspace 目录"
      - "网络请求需要审批"
  
  - type: process
    scope: task-specific
    examples:
      - "修改代码前先运行测试"
      - "提交前需要 review"
      - "危险操作需要确认"
  
  - type: safety
    scope: global
    examples:
      - "沙盒边界不可突破"
      - "敏感数据不可泄露"
      - "外部 API 调用需要审计"
```

**验证实现**: agent-mcp-gateway 的 Policy Engine 已验证 deny-before-allow 机制

---

#### Module 2: Context Manager (上下文管理)

**职责**: Token 预算管理、上下文选择、历史压缩

**子模块**:
```
ContextManager
├── TokenBudget
│   - 预算分配策略
│   - 动态调整
│   - 参考: 你的 Context Manager 项目
│
├── SemanticTagger
│   - 信息打标签（type, scope, priority, decay）
│   - 依赖关系标记
│   - 参考: agent-mcp-gateway 的 agent_id 标签
│
├── LayeredContext
│   - Layer 0: 结构层（AGENTS.md, 目录结构）<500 tokens
│   - Layer 1: 任务层（当前任务上下文）动态
│   - Layer 2: 历史层（压缩摘要）
│   - Layer 3: 全局层（索引）<200 tokens
│   - 参考: Continuous-Claude-v3 的 TLDR 5-layer
│
├── ContextSelector
│   - 任务分类 → 选择策略
│   - 依赖检查 → 纳入必要信息
│   - 预算截断
│   - 参考: hoangsa 的 context_pointers
│
├── HistoryCompressor
│   - Ledger + Handoff 系统
│   - YAML 格式压缩
│   - 参考: Continuous-Claude-v3 的 Ledger/Handoff
│
└── MemoryBridge
    - 依赖保留（tool_use/tool_result pairs）
    - Summary message 作为 archive boundary
    - 参考: claude-rolling-context
```

**分层策略**:
```
┌─────────────────────────────────────────────────────┐
│ Layer 0: Structure Layer (永久保留)                  │
│ - AGENTS.md (项目约束)                              │
│ - 目录结构 (项目骨架)                                │
│ - 关键接口定义                                       │
│ Token Budget: <500                                  │
├─────────────────────────────────────────────────────┤
│ Layer 1: Task Layer (按需加载)                       │
│ - 当前任务上下文                                     │
│ - 相关文件内容                                       │
│ - 依赖关系                                           │
│ Token Budget: 动态管理                               │
├─────────────────────────────────────────────────────┤
│ Layer 2: History Layer (压缩摘要)                   │
│ - Session 历史压缩                                   │
│ - 过往决策摘要                                       │
│ - Ledger + Handoff                                  │
│ Token Budget: 压缩后可控                             │
├─────────────────────────────────────────────────────┤
│ Layer 3: Index Layer (坐标系统)                      │
│ - 文件索引（不加载内容）                              │
│ - 模块关系图                                         │
│ - 影响分析                                           │
│ Token Budget: <200                                  │
└─────────────────────────────────────────────────────┘
```

**验证实现**: 
- TLDR 5-layer → 95% token 节省验证
- hoangsa context_pointers → 按需加载验证
- Ledger/Handoff → 历史压缩验证

---

#### Module 3: Execution Boundary (执行边界)

**职责**: 沙盒、权限、审计

**子模块**:
```
ExecutionBoundary
├── SandboxManager
│   - 文件系统隔离
│   - 网络访问控制
│   - 进程隔离
│   - 参考: OpenClaw 的 sandbox mode
│
├── PermissionGateway
│   - Tool access control
│   - On-demand tool discovery
│   - 参考: agent-mcp-gateway 的 Tool Gateway
│
├── AuditLogger
│   - 所有操作记录
│   - 行为追踪
│   - 回滚支持
│
└── SafetyChecker
    - 危险操作检测
    - 安全边界验证
    - 参考: PromptKit 的 Guardrails protocols
```

**Tool Gateway 设计** (参考 agent-mcp-gateway):
```yaml
tool_gateway:
  startup_tools:
    - list_servers      # ~500 tokens
    - get_server_tools  # ~500 tokens
    - execute_tool      # ~500 tokens
    # 总计 ~1500 tokens vs 50000+ 全量工具
  
  on_demand_loading:
    - Agent 请求时才加载具体工具 schema
    - 90%+ context reduction
  
  policy_engine:
    precedence:
      1. explicit_deny    # 最高
      2. wildcard_deny    # (*_delete, *_admin)
      3. explicit_allow
      4. wildcard_allow   # (get_*, read_*)
      5. implicit_grant
      6. default_policy   # deny
```

---

#### Module 4: Orchestrator (调度层)

**职责**: 任务分类、DAG 执行、策略执行

**子模块**:
```
Orchestrator
├── TaskClassifier
│   - 4-stage progressive classification
│   - 参考: Continuous-Claude-v3 的 Skill Activation Hints
│   - 避开小模型，用主模型意图声明
│
├── DAGExecutor
│   - 任务 DAG 构建
│   - 并行/串行执行决策
│   - 参考: hoangsa 的 DAG execution
│
├── PolicyEnforcer
│   - 约束策略执行
│   - 动态策略切换（探索/确定/危险）
│
└── StateTracker
    - 任务状态管理
    - 依赖状态追踪
    - 参考: hoangsa 的 state machine
```

**Task Classifier 4-Stage**:
```
Stage 1: Rule Engine (零成本)
├── 关键词匹配 → 粗分类
├── intentPatterns 匹配
└── confidence > 0.8 → 直接使用

Stage 2: State Heuristics (低成本)
├── 当前文件路径 → 推断类型
├── 最近操作历史 → 推断意图
└── 例如: 正在改 test/ → 测试类型

Stage 3: Main Model Intent Declaration (中成本，高准确)
├── 让主模型输出 <50 token 意图声明
├── "我的意图是: 执行一个重构任务..."
├── 优势: 强理解 + 自一致性

Stage 4: Runtime Dynamic Adjustment
├── 检测行为-意图 mismatch
├── 动态调整策略
└── 异常 → 回退/重新分类
```

**验证实现**: 
- Skill Activation Hints → 规则引擎验证
- DAG execution → 任务依赖管理验证

---

#### Module 5: Agent Runtime (智能运行时)

**职责**: LLM 接口、工具调度、状态管理

**子模块**:
```
AgentRuntime
├── LLMInterface
│   - 多模型支持
│   - Model profile selection (quality/balanced/budget)
│   - 参考: hoangsa 的 multi-profile
│
├── ToolDispatcher
│   - 工具调用路由
│   - 工具结果处理
│   - 参考: agent-mcp-gateway
│
├── StateManager
│   - Session state
│   - Agent state
│   - 参考: Continuous-Claude-v3 的 sessions table
│
└── MemoryService
    - 学习提取
    - 记忆存储
    - 参考: Continuous-Claude-v3 的 Daemon + pgvector
```

---

#### Module 6: Prompt Assembler (Prompt 组装)

**职责**: 结构化 Prompt 组装、注入顺序控制

**子模块**:
```
PromptAssembler
├── TemplateRegistry
│   - Persona templates
│   - Protocol templates
│   - Format templates
│   - 参考: PromptKit 的 5-layer 组件
│
├── AssemblyPipeline
│   - 固定注入顺序: CONSTRAINTS → GOAL → REFERENCE → CONTEXT → HISTORY
│   - 参考: PromptKit 的 Template Chaining
│
├── SemanticMarkers
│   - [CONSTRAINTS_START], [CONSTRAINTS_END]
│   - 防止语义污染
│   - 参考: Prompt-Programming-Language 的 ALL_CAPS sections
│
└── PromptOptimizer
    - Token 优化
    - 重复检测
    - 参考: PromptKit 的 minimal-edit-discipline
```

**组装顺序** (验证理由):
```
ORDER: constraint → goal → reference → context → history

理由:
1. constraint 先注入 → 建立"不能做什么"框架
2. goal 次注入 → 在框架内理解"要做什么"
3. reference 再注入 → 知道"有哪些资源可用"
4. context 后注入 → 在框架内选择性理解细节
5. history 最后注入 → 知道"之前发生了什么"，不被主导

验证: Hooks 系统拦截注入顺序验证
```

---

## 3. 数据流设计

### 3.1 任务执行流程

```
用户输入 → Task Classifier → 确定任务类型
                          ↓
              Context Manager → 选择上下文策略
                          ↓
              Constraint Engine → 加载相关约束
                          ↓
              Prompt Assembler → 组装结构化 Prompt
                          ↓
              Execution Boundary → 检查权限/沙盒
                          ↓
              Agent Runtime → LLM 执行
                          ↓
              Policy Enforcer → 约束验证
                          ↓
              输出结果 → 审计记录
```

### 3.2 DAG 并行执行流程

```
任务分解 → DAG Builder → 构建依赖图
              ↓
         Wave Scheduler → 分波执行
              ↓
         ┌─────────────────────────────┐
         │ Wave 1: Independent Tasks   │
         │  [Task A] [Task B] [Task C] │  ← 并行执行，fresh context
         └─────────────────────────────┘
              ↓
         ┌─────────────────────────────┐
         │ Wave 2: Dependent Tasks     │
         │  [Task D] (depends on A,B)  │  ← 串行，接收 A,B 结果
         └─────────────────────────────┘
              ↓
         结果聚合 → 状态更新
```

参考: hoangsa 的 DAG execution + context_pointers

---

## 4. 验证状态映射

### 4.1 设计概念 → 已验证实现

| 设计概念 | 验证状态 | 已验证实现 | 关键数据 |
|----------|----------|------------|----------|
| 分层 Context | ✅ 完全验证 | TLDR 5-layer | 95% token 节省 |
| 按需加载工具 | ✅ 完全验证 | agent-mcp-gateway | 90%+ reduction |
| DAG 执行 | ✅ 完全验证 | hoangsa | fresh context per task |
| Policy Engine | ✅ 完全验证 | agent-mcp-gateway | deny-before-allow |
| Ledger/Handoff | ✅ 完全验证 | Continuous-Claude-v3 | YAML 格式 |
| 结构化 Prompt | ✅ 完全验证 | PromptKit | 5-layer 组件 |
| Hooks 拦截 | ✅ 完全验证 | Continuous-Claude-v3 | 30 hooks |
| 主模型意图声明 | ✅ 部分验证 | Skill Activation | 避开小模型 |
| 动态评分公式 | ⚠️ 未验证 | - | 需实验验证 |
| 语义隔离标记 | ⚠️ 部分验证 | claude-rolling-context | dependency analysis |

### 4.2 未验证部分 → 实现建议

**动态评分公式**: `priority = base × relevance × exp(-decay × time)`
- 建议: 先实现 base + relevance，decay 可选
- 验证实验: A/B 测试不同 decay 值

**语义隔离标记**: `[SECTION_START] ... [SECTION_END]`
- 建议: 参考 Prompt-Programming-Language 的 ALL_CAPS sections
- 验证实验: 测试标记对 AI 理解的影响

---

## 5. 实现路径

### 5.1 Phase 优先级

```
Phase 0: Foundation (必须优先)
├── Context Manager
│   ├── TokenBudget (你已有)
│   ├── LayeredContext (扩展 TLDR)
│   ├── HistoryCompressor (Ledger/Handoff)
│   └── ContextSelector (依赖检查)
│
└── Execution Boundary
    ├── SandboxManager (OpenClaw 已有)
    └── AuditLogger (基础实现)

Phase 1: Constraint Layer
├── ConstraintParser (自然语言 → 语义表示)
├── ConstraintRegistry (存储)
├── PolicyEngine (deny-before-allow)
│
└── PromptAssembler
    ├── TemplateRegistry
    └── AssemblyPipeline

Phase 2: Orchestration Layer
├── TaskClassifier (4-stage)
├── DAGExecutor
└── PolicyEnforcer

Phase 3: Runtime Layer
├── ToolGateway (On-demand discovery)
├── MemoryService (Daemon + vector)
└── LLMInterface (multi-profile)

Phase 4: NLAH Layer (最上层)
├── Natural Language Constraint Editor
├── Constraint Comparison Tool
└── Semantic Contract Portability
```

### 5.2 与现有项目整合

**你的 Context Manager 项目**:
```
现有模块 → 扩展方向

TokenBudget → 复用，增加动态调整
PriorityTruncator → 扩展为 SemanticTagger + 动态评分
LLMCompressor → 复用为 HistoryCompressor
MultiAgentContext → 扩展为 DAGExecutor
TaskNotificationService → 扩展为 Orchestrator 组件
LanceDBStorageAdapter → 复用为 MemoryService
```

**新增模块**:
```
SemanticTagger (语义标签)
├── type: constraint | goal | context | history | reference
├── scope: global | local | task-specific
├── priority_base: 1-10
├── decay_rate: float
└── dependencies: list

PromptAssembler (结构化组装)
├── TemplateRegistry (PromptKit 风格)
├── AssemblyPipeline (固定顺序)
├── SemanticMarkers (隔离标记)

TaskClassifier (任务分类)
├── RuleEngine (关键词 + intentPatterns)
├── StateHeuristics (状态推断)
├── IntentDeclaration (主模型输出)
└── RuntimeAdjustment (动态调整)

ConstraintEngine (约束引擎)
├── ConstraintParser
├── ConstraintRegistry
├── PolicyEngine (agent-mcp-gateway 风格)
└── ConstraintVerifier

ToolGateway (工具网关)
├── OnDemandDiscovery (90% reduction)
├── PolicyEngine (deny-before-allow)
└── SessionIsolation
```

---

## 6. 技术栈选择

### 6.1 核心组件

```
Context Storage:
├── PostgreSQL + pgvector (参考 Continuous-Claude-v3)
├── LanceDB (你已有)
└── YAML for Ledger/Handoff (高效压缩)

Constraint Storage:
├── YAML/JSON (自然语言友好)
├── Git (版本控制)

DAG Execution:
├── Rust CLI (参考 hoangsa) 或
├── Python + asyncio

LLM Interface:
├── OpenAI SDK
├── Anthropic SDK
├── Alibaba SDK (你已配置)

Tool Gateway:
├── MCP Protocol
├── HTTP/stdio transport
```

### 6.2 Hook 系统设计

参考 Continuous-Claude-v3 的 30 hooks:

```yaml
hooks:
  - name: SessionStart
    actions:
      - load_constraints
      - load_ledger
      - init_state
  
  - name: PreToolUse
    actions:
      - permission_check
      - sandbox_verify
      - policy_enforce
  
  - name: PostToolUse
    actions:
      - result_audit
      - state_update
      - learning_extract
  
  - name: PreCompact
    actions:
      - history_compress
      - handoff_prepare
  
  - name: SessionEnd
    actions:
      - final_audit
      - handoff_write
      - memory_store
```

---

## 7. 关键洞察

### 7.1 设计原则

```
1. "Context 管理的本质不是'选什么'，而是'在哪一层处理什么'"
   - 语义层 → 必须保留 → 决定方向
   - 内容层 → 按需加载 → 支持执行
   - 历史层 → 压缩摘要 → 提供线索
   - 索引层 → 永久保留 → 提供坐标

2. "Harness 从'代码实现'提升到'语义契约'"
   - 执行交给智能运行时 (LLM)
   - 约束留在自然语言

3. "随机性在创意层，确定性在执行层，安全在代码层"
   - creative_zone: 允许随机
   - execution_zone: 限制随机
   - safety_zone: 禁止随机

4. "约束的目的不是限制 AI，而是降低决策复杂度"
   - 好约束 = AI 只需要在有限选项中做选择
   - 坏约束 = AI 被 handcuff，无法完成任务
```

### 7.2 避坑指南

```
❌ 不要用小模型做任务分类
   → 主流实现都避开小模型（可靠性问题）
   → 用规则引擎 + 主模型意图声明

❌ 不要一次性加载所有工具
   → agent-mcp-gateway 证明 90%+ 工具从未使用
   → On-demand discovery

❌ 不要让历史层污染理解
   → 注入顺序: constraint → goal → reference → context → history
   → 历史 last，避免 anchoring bias

❌ 不要在 Prompt 里堆砌内容
   → TLDR 5-layer 证明 95% token 节省可行
   → 分层管理 > 内容堆砌
```

---

## 8. 下一步行动

### 8.1 立即可做

1. **扩展 Context Manager**
   - 添加 SemanticTagger 模块
   - 实现 LayeredContext (参考 TLDR)
   - 添加 Ledger/Handoff 系统

2. **实现 PolicyEngine**
   - 参考 agent-mcp-gateway 的 deny-before-allow
   - Wildcard pattern matching

3. **设计验证实验**
   - 动态评分公式 A/B 测试
   - 语义隔离标记效果测试

### 8.2 中期目标

1. 完整 ConstraintEngine 实现
2. TaskClassifier 4-stage 实现
3. DAGExecutor 实现

### 8.3 长期目标

1. NLAH Layer (自然语言约束编辑器)
2. 跨运行时可移植性
3. 多 Harness 比较工具

---

*设计版本: v1.0*
*生成时间: 2026-04-07*
*基于: First-Principles 推理 + 6 个已验证项目实现*