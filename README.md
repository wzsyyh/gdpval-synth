# GDPval 合成任务生成流水线

> 一种基于真实种子材料的流水线，可生成与真实 [GDPval](https://openai.com/index/introducing-swe-bench-verified/)（OpenAI 发布的 220 题、覆盖 44 种职业的基准测试）无法区分的专业评估任务。
>
> **当前语料库：50 道已验收任务**（律师：15，金融分析师：16，软件工程师：19），含真实交付物（.docx、.xlsx、.md、.pdf）。

---

## 一、项目概述

### 1.1 动机

GDPval 评估精通各领域的智能体在 44 种职业上的表现，每种职业 5 题。人工构建此类数据集成本高昂且缓慢——每道题都需要领域专家设计提示、撰写参考答案、制定细粒度评分标准。

**我们的洞察**：虽然领域不同，但*数据生成逻辑*是相同的。我们选取了**3 种代表性职业**，涵盖截然不同的专业工作流程：

| 职业 | GDPval 对应职业 | 真实种子来源 |
|---|---|---|
| 律师 | Lawyers | CourtListener API（联邦法院判例） |
| 金融分析师 | Financial and Investment Analysts | SEC EDGAR XBRL 财报 |
| 软件工程师 | Software Developers | GitHub Issues & PRs（scikit-learn、pandas 等） |

每个领域有独特的交付物格式、推理模式和事实依据要求——使其成为完整 44 职业基准的强有力代理。

### 1.2 实验目标

1. 构建覆盖 3 种职业、多种交付物类型的合成任务语料库
2. 确保所有任务的事实 100% 锚定在真实公开材料上
3. 实现题目、答案、评分标准的内部一致性
4. 通过严格质量门（硬校验 + LLM 一致性验证），产出可直接用于模型评估的数据集

### 1.3 核心结果

| 指标 | 结果 | 说明 |
|---|---|---|
| 已验收任务 | **50** | 律师 15 / 金融 16 / SWE 19 |
| 质量门通过率 | **~44%** | 50 验收 / 114 总生成 |
| 事实锚定率 | **100%** | 所有名字、数字、引用均来自种子材料 |
| 每领域任务数 | 15–19 | 原始 GDPval 的 3–4 倍 |
| 输入附件率 | **100%** | 所有任务均附带种子材料作为输入附件 |

---

## 二、方法论演进

本项目经历了**两次方案迭代**。第一次尝试失败，第二次才是当前实现。

### 2.1 方案一：先出题，再让模型做题

**设计思路**：
1. 根据种子材料，让 LLM 只生成**题目（prompt）和评分标准（rubric）**
2. 用多个模型（Claude、GPT、Qwen 等）分别做题，产出交付物答案
3. 多个模型的表现（solve rate）反映题目难度
4. 表现最好的模型答案作为参考 answer

**预期优势**：难度有客观衡量（模型正确率），答案由"做题"产生而非"编造"。

### 2.2 方案一的问题

实际运行后发现严重问题：

**问题 1：模型交付物质量差**
- 模型编造材料中没有的案例引用（律师任务）
- 模型记错财务数字（如 Q1 Revenue 83,130M → 85,138M）
- 模型忽略 rubric 中的格式要求（如缺少 signature block）
- 代码评审任务中虚构不存在的文件路径和函数名

**问题 2：恶性循环**
- 如果模型做不对，到底是**题目设计有问题**，还是**模型能力不足**？
- 无法区分。导致调试时无从下手。

**问题 3：API 成本过高**
- 每个任务需要 3+ 个模型各做 1 次，117 个种子 × 3 模型 = 351 次 API 调用
- 加上迭代调试，成本不可接受

### 2.3 方案二：答案优先设计（Answer-First Design）

**核心思路**：题目、答案蓝图、评分标准由**单次 LLM 调用同步生成**。答案不是"做出来的"，而是"设计出来的"。

```
真实公开材料（种子）
    ↓  [从 CourtListener / EDGAR / GitHub 采集]
大模型读取完整种子材料
    ↓  [单次结构化生成调用]
统一任务 { 题目 + 答案蓝图 + 评分标准 }
    ↓  [确定性代码渲染]
交付物文件（.docx / .xlsx / .md / .pdf）
    ↓  [硬质量校验器 + LLM 一致性验证]
验收或拒绝
```

**为什么这个方案更好**：
- **一致性保证**：题目要求的内容一定在答案中体现，rubric 检查的项一定能在答案中找到
- **事实可控**：所有名字、数字、引用来自种子材料，不编造
- **成本可控**：每个种子只需 1 次 LLM 调用
- **格式正确**：答案蓝图由确定性代码渲染，不会缺 signature block 或格式错误

**局限**：难度不再是"模型做题的正确率"，而是前端的设计选择（见 §八）。

---

## 三、数据生成流程

![Pipeline 流程图](assets/pipeline_flow.png)

### 3.1 种子采集

将每道题锚定在真实公开数据上：

- **律师**：美国最高法院、第九巡回上诉法院、第二巡回上诉法院等的完整判决书原文（通过 CourtListener REST API）。完整捕获判决理由、推理过程和事实细节。
- **金融分析师**：SEC EDGAR 结构化 XBRL 财务报表（营收、净利润、资产、负债、EPS），覆盖 25 家大型上市公司（AAPL、MSFT、NVDA、GOOGL、META、AMZN、TSLA、BAC、JPM、BA、CVX、HD、DIS 等）。
- **软件工程师**：高质量开源仓库的已合并 PR diff、描述及关联 issue（scikit-learn、pandas、numpy、pytorch、vercel/next.js、facebook/react 等 19 个仓库）。

### 3.2 统一生成

单次大模型调用（Mimo v2.5 Pro）读取**完整**种子材料，输出结构化的 `统一任务`。

#### 3.2.1 任务类型由种子内容决定（启发式映射）

系统提示中给 LLM 的类型判断指南：
- **律师**：contract terms → `contract_redline`；jurisdiction → `motion_to_dismiss`；expert testimony → `deposition_outline`
- **财务**：debt/leverage → `credit_memo`；growth/M&A → `investment_memo`；industry disruption → `industry_analysis`
- **SWE**：bug fix → `bug_fix_pr`；new API → `design_doc`；large refactor → `code_review`

LLM 根据种子材料**自行判断**最终类型，不是套用模板。

#### 3.2.2 题目结构强制模仿 GDPval 风格

系统提示强制四段式结构：
1. **Role and context**："You are a..." 开头，交代角色、机构、背景
2. **Materials provided**：列出附件名称和内容
3. **Task requirements**：具体步骤，编号列表
4. **Deliverable specification**：输出格式和结构要求

语气规则：禁用 "ASAP/urgent"、禁用 "Please ensure" 等 AI 腔。

#### 3.2.3 所有事实必须来自种子材料

用户 prompt 中明确约束：
> "ALL facts in the answer must come from the material above. Do not invent names, numbers, or citations not in the material."

评分标准同样受约束：
> "Do NOT create criteria that check facts, dates, numbers, or references that are not in the seed material. Every rubric criterion must be answerable from the seed material alone."

### 3.3 确定性渲染

答案蓝图由代码渲染为真实文件（无大模型参与）：

| 格式 | 库 | 示例交付物 |
|---|---|---|
| `.docx` | python-docx | 法律备忘录、信用备忘录、投资备忘录 |
| `.xlsx` | openpyxl | 含实时公式的财务模型 |
| `.md` | 纯文本 | 代码评审、设计文档 |
| `.pdf` | LibreOffice headless | 从 docx 渲染的法律文档 |

### 3.4 质量漏斗

任务在验收前通过两层质量检查：

**硬质量校验**（确定性，8 项检查）：
- 题目长度 ≥ 1,300 字符
- 评分项数量 ≥ 35 且 ≤ 80
- 预期值数量 ≥ 3
- 分值分布不倾斜（单一分值不超过 85%）
- 评分项具体且可验证（不模糊）
- 输入附件有真实内容（≥ 100 字符）
- 答案有实际正文内容（非仅标题）
- 评分标准中的引用事实来自种子材料（rubric grounding）

**LLM 一致性验证**（两阶段设计）：
- **Stage 1 (Planner)**：读取 prompt + rubric + answer，生成逐条验证清单
- **Stage 2 (Executor)**：逐条执行验证清单，对照种子材料核查每个事实和计算
- 检查维度：seed alignment / calculation accuracy / rubric alignment / rubric grounding / prompt coverage

**通过率：~44%**（50/114）。其中律师 ~48%、SWE ~59%、金融 ~35%——金融通过率较低是因为 XBRL 数据的 YTD/季度混淆和数字精度问题（见 §4.2）。

---

## 四、质量验证与抽样检查

![质量漏斗图](assets/quality_funnel.png)

我们对已验收任务进行了多轮人工抽检（累计覆盖约 60% 的任务），重点检查题目-答案-rubric 一致性。以下问题是开发过程中**发现并已修正**的，当前版本的已验收任务中已不存在这些问题。

### 4.1 六项流水线修复（v2 质量提升）

在专家审计中发现了 6 个系统性问题，已全部修复：

| # | 问题 | 影响范围 | 修复方案 | 修改文件 |
|---|---|---|---|---|
| 1 | Markdown 交付物出现重复 H1 标题 | SWE 任务 | `md_title` 存在时将 section heading_level 钳制到 ≥2，跳过与 md_title 相同的 heading | `artifacts/renderer.py` |
| 2 | 输入附件 body 与种子文本重复 | 所有任务 | 多 attachment 折叠为单个，body 始终为完整种子文本 | `scenario/synthesis.py` |
| 3 | 评分标准引用种子中不存在的事实 | 所有任务 | 新增 `_check_rubric_seed_grounding()`：提取 rubric 中的引用字符串，验证是否出现在种子文本中，≥3 条未锚定则拒绝 | `validators/hard_quality.py` |
| 4 | 系统提示对 rubric 约束不够强 | 所有任务 | rubric 指令从"不检查答案中没有的内容"改为"不检查种子材料中没有的事实"；金融提示增加 XBRL 概念名警告 | `scenario/synthesis.py` |
| 5 | LLM 一致性验证未检查 rubric grounding | 所有任务 | `ValidationResult` 增加 `rubric_grounded` 字段；executor 系统提示增加第 6 条指令；overall_passed 包含 rubric_grounded | `validators/llm_consistency.py` |
| 6 | 多 attachment 渲染时 body 相同的副本 | 所有任务 | orchestrator 中按 body hash 去重，跳过已渲染的重复 attachment | `orchestrator.py` |

### 4.2 金融领域通过率：XBRL 数据挑战

金融任务是三个领域中**通过率最低的**（当前约 35%），核心原因是 XBRL 数据的结构性陷阱。

#### 问题根源

SEC EDGAR 的 XBRL `companyfacts` API 对同一期间返回**两条记录**：
- **YTD 累计值**：如 Q2 2025 的 `start=2025-01-01, end=2025-06-30`（半年累计）
- **单季度值**：如 Q2 2025 的 `start=2025-04-01, end=2025-06-30`（仅 Q2）

两者共享相同的 `fp`（Q2）和 `fy`（2025），仅靠 `start` 日期区分。LLM 容易把 YTD 累计值当成单季度值使用。

#### 防护措施（三层）

1. **种子渲染层**：`_build_seed_text()` 在周期标签中加入日期范围
   ```
   # 修复前：Q2 2025: 164,636,000,000
   # 修复后：Q2 2025 (2025-01-01 to 2025-06-30): 164,636,000,000
   ```

2. **系统提示层**：在 `_FINANCIAL_SYS` 中加入显式 YTD/季度区分指令和 XBRL 概念名警告（不要用 "Revenues" 代替 "RevenueFromContractWithCustomerExcludingAssessedTax"）

3. **验证层**：LLM consistency validator 同样获得日期范围上下文，能正确识别 YTD/季度差异

#### 剩余拒绝原因

金融任务的主要拒绝原因：
- LLM 将 `$2.375B` 四舍五入为 `$2.4B`（被 validator 判为不精确）
- debt-to-equity 分母用错（用 total assets 代替 stockholders' equity）
- 从 YTD 推算单季度时的算术错误

### 4.3 验证方法

对每批次任务，我们执行以下检查：
1. **事实溯源**：答案中的 case citation / 财务数字 / 代码引用是否来自种子材料？
2. **Rubric 可验证性**：每条评分标准是否都能在答案中找到对应？
3. **Rubric grounding**：评分标准中的具体事实是否存在于种子材料中？
4. **题目-答案匹配**：题目要求的内容是否都在答案中体现？
5. **交付物完整性**：渲染后的文件是否包含所有要求的章节和格式元素？

---

## 五、数据集统计

### 5.1 整体语料

```
已验收任务总数：50
总生成数：114（50 验收 + 64 拒绝）
质量门通过率：~44%
交付物渲染率：100%（50/50）
```

### 5.2 按职业分布

| 职业 | 任务数 | 占比 | 通过率 | GDPval 对应职业 | GDPval 数量 |
|---|---|---|---|---|---|
| 软件工程师 | 19 | 38% | ~59%（19/32） | Software Developers | 5 |
| 金融分析师 | 16 | 32% | ~35%（16/46） | Financial and Investment Analysts | 5 |
| 律师 | 15 | 30% | ~48%（15/31） | Lawyers | 5 |

### 5.3 交付物类型

![职业 × 交付物类型分布](assets/occupation_archetype.png)

| 类型 | 数量 | 说明 |
|---|---|---|
| `legal_memo` | 15 | 分析法院判例的正式法律备忘录 |
| `code_review` | 14 | PR 合并后的技术评审 |
| `credit_memo` | 9 | 含杠杆分析的信贷委员会备忘录 |
| `investment_memo` | 7 | 含财务指标的投资分析备忘录 |
| `design_doc` | 4 | 新功能的架构/设计文档 |
| `bug_fix_pr` | 1 | 缺陷修复 PR 描述 |

### 5.4 文件格式

| 格式 | 数量 | 适用职业 |
|---|---|---|
| `.docx` | 27 | 律师、金融分析师 |
| `.md` | 19 | 软件工程师 |
| `.pdf` | 4 | 律师（法律文档） |

### 5.5 难度分布

| 难度带 | 数量 | 占比 |
|---|---|---|
| 中等 | 26 | 52% |
| 困难 | 12 | 24% |
| 简单 | 12 | 24% |

难度在种子选择阶段分配（见 `pipeline/seeds/selector.py`），并通过大模型提示中的时间指导强化：
- **简单**（1–3 小时）：范围有限、较直接的种子。
- **中等**（3–6 小时）：标准复杂度——专业工作的主体。
- **困难**（6–10 小时）：上诉法院判例、大型公司财务数据，或影响广泛的高影响力 PR。

55%/25%/20% 的目标分布是流水线设计选择，并非源自 GDPval（公开的 GDPval 数据未包含难度标注）。

### 5.6 质量指标

| 指标 | 中位数 | 范围 |
|---|---|---|
| 题目长度（字符） | 2,531 | 1,303 – 3,569 |
| 评分项数量 | 51 | 35 – 60 |
| 预期值数量 | 30 | 19 – 51 |

---

## 六、与 GDPval 的对齐

| 维度 | 我们的流水线 | GDPval 目标 |
|---|---|---|
| 每领域任务数 | 15–19 | 5 |
| 题目长度（中位数） | 2,531 字符 | ~2,024 字符 |
| 评分标准粒度 | 35–60 项 | 相近 |
| 输入附件率 | 100% | ~57% |
| 种子锚定事实 | 100%（所有事实来自真实数据） | 100%（专家设计） |
| 交付物格式 | docx、xlsx、md、pdf | docx、xlsx、md、pdf |

---

## 七、典型任务示例

### 示例 1：金融分析师——波音信用备忘录

**种子**：Boeing Q1 FY2026 10-Q XBRL 数据（营收、负债、负股东权益等）

**任务类型**：`credit_memo`

**Prompt 开头**（节选）：
> You are a senior credit analyst in the Leveraged Finance group at a major commercial bank. Your team has been asked to prepare a credit memorandum for the Boeing Company (BA) to support the bank's ongoing credit risk monitoring and internal portfolio review...

**Rubric 片段**（5 条）：
- `[+1]` The submitted document is a Word document or PDF titled 'Credit Memo - The Boeing Company'.
- `[+1]` The document header includes 'To: Credit Risk Committee'.
- `[+2]` The executive summary identifies the persistent negative equity position as a key credit concern.
- `[+2]` The leverage analysis discusses the debt-to-capital ratio trend using data from the attached 10-Q.
- `[+1]` The recommendation section provides a clear exposure stance (increase/maintain/reduce).

**交付物**：`credit_memo.docx`（含标准信用备忘录格式：header、executive summary、leverage analysis、covenants、recommendation）

### 示例 2：软件工程师——Next.js PR 代码评审

**种子**：vercel/next.js PR #65804（添加 experimental React compiler 支持）

**任务类型**：`code_review`

**Prompt 开头**（节选）：
> You are a senior frontend engineer on the Next.js core team. Your team has just received PR #65804, which adds experimental React compiler support to Next.js via a new `experimental.reactCompiler` configuration option. Before merging to the main branch, you need to produce a thorough code review document...

**Rubric 片段**（5 条）：
- `[+2]` The submitted document is a Markdown file titled exactly 'Code Review - PR #65804'.
- `[+2]` The Summary section describes the PR's purpose: adding experimental React compiler support via `experimental.reactCompiler`.
- `[+2]` The Design Decisions section evaluates the choice of using a boolean or object configuration for the compiler options.
- `[+1]` The Risk Assessment section identifies potential backward compatibility concerns.
- `[+2]` The Recommendations section provides actionable next steps before merging.

**交付物**：`code_review.md`（含 Summary、Design Decisions、Implementation Quality、Risk Assessment、Recommendations 章节）

---

## 八、已知问题与局限性

### 8.1 难度控制是启发式的，非后验验证

难度来自两个前端的、非验证的层面：
1. **种子选择时的客观分层**（法院层级、公司收入规模、PR 质量分）
2. **LLM 生成时的时间指导**（"这是一个 Hard 任务，预期耗时 6-10 小时"）

我们没有让模型**实际做题**来验证难度。Solve-rate probe（让 frontier model 预测自己的得分）可以筛掉"明显太简单"的任务，但无法确认 medium 真的对应 medium。

### 8.2 金融任务通过率较低

金融任务的通过率（~35%）显著低于律师（~48%）和软件工程师（~59%）。主要挑战：

- **XBRL 数据复杂性**：同一期间存在 YTD 累计和单季度两条记录，LLM 容易混用（已通过日期范围标注修复，见 §4.2）
- **数字精度敏感**：LLM 倾向于四舍五入（`$2.375B` → `$2.4B`），被 consistency validator 判为不精确
- **推算错误**：从 YTD 减去前期推算单季度时，LLM 偶尔选错被减数或减数
- **XBRL 概念名混淆**：LLM 用 "Revenues" 代替 "RevenueFromContractWithCustomerExcludingAssessedTax" 等长概念名（已通过系统提示警告修复）

当前金融任务均为定性分析（信用备忘录、投资备忘录），不包含 DCF 估值等复杂定量建模。

### 8.3 种子覆盖范围有限

- **律师**：仅覆盖联邦法院判例，未包含州法院、行政裁决、合同原文等
- **财务**：覆盖 25 家大型上市公司，缺少中型公司、私有公司、非美国公司
- **SWE**：覆盖 19 个仓库（Python/JavaScript/Rust 生态），缺少 C++、Go 等语言

### 8.4 质量验证的局限

硬质量 validators 只能检查结构性属性（rubric 数量、分值分布、语言模糊度、rubric grounding），LLM 一致性验证依赖模型判断。两者都无法替代人工领域专家的深度审查。当前批次的人工抽检覆盖率约 60%。

---

## 九、复现

### 一键运行（推荐）

```bash
# 1. 配置 API 密钥
cp .env.example .env
# 编辑 .env 填写 MIMO_API_KEY、COURTLISTENER_API_TOKEN、GITHUB_TOKEN

# 2. 一键运行完整流程
./quickstart.sh

# 或：跳过种子采集（种子已存在时）
./quickstart.sh --skip-seeds

# 或：小规模测试（10 个种子，2 个 worker）
./quickstart.sh --small
```

### 分步运行

如需分步控制，可手动执行：

```bash
# 安装依赖
uv sync

# 采集种子（ lawyer / financial / swe ）
uv run python -m pipeline.seeds.courtlistener
uv run python -m pipeline.seeds.edgar_xbrl
uv run python -m pipeline.seeds.github_issues

# 运行流水线
uv run python -m pipeline.orchestrator -n 117 --workers 4

# 生成报告图表
uv run python scripts/generate_charts.py
```

种子缓存在 `pipeline/seeds/store/{occupation}/`。

### 查看任务

```bash
# 查看单个任务的题目、评分标准和预期值
uv run python scripts/verify_deliverables.py --task-id sc_xxx

# 打开渲染后的交付物
open data/deliverables/sc_xxx/*.docx
```

---

## 十、项目结构

```
pipeline/
  seeds/
    courtlistener.py      # 采集法律判例
    edgar_xbrl.py         # 采集 SEC 财务数据
    github_issues.py      # 采集 GitHub PRs
    store/                # 缓存的种子 JSON
    selector.py           # 按难度筛选种子
  scenario/
    synthesis.py          # 统一生成（题目 + 答案 + 评分标准）
    reference_answer.py   # 蓝图模型
    canonical.py          # 难度/职业枚举
  artifacts/
    renderer.py           # 确定性渲染（docx/xlsx/md/pdf）
    input_renderer.py     # 输入附件渲染
  validators/
    hard_quality.py       # 确定性质量检查（8 项）
    llm_consistency.py    # 两阶段 LLM 一致性验证
  diversity/
    grid.py               # 种子采样网格
  orchestrator.py         # 流水线主入口

data/
  accepted/               # 已验收任务 JSON + 输入附件
  rejected/               # 被拒绝的任务
  deliverables/           # 渲染后的交付物文件
  gdpval_reference/       # 真实 GDPval 任务（用于比对）
```

---

## 十一、关键文件索引

| 文件 | 用途 |
|---|---|
| `pipeline/scenario/synthesis.py` | 统一生成核心：3 套系统提示 + 结构化输出 |
| `pipeline/seeds/selector.py` | 按职业和难度筛选种子的算法 |
| `pipeline/validators/hard_quality.py` | 硬质量校验器（8 项确定性检查） |
| `pipeline/validators/llm_consistency.py` | 两阶段 LLM 一致性验证（Planner + Executor） |
| `pipeline/artifacts/renderer.py` | 确定性渲染：蓝图 → 真实文件 |
| `scripts/validate_deliverables.py` | 验证交付物文件完整性（docx/xlsx/md） |

---

**报告生成时间**：2026 年 5 月 15 日
**实验周期**：约 3 天
**项目状态**：核心流水线已稳定，语料库可扩展
