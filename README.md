# GDPval 合成任务生成流水线

> 一种基于真实种子材料的流水线，可生成与真实 [GDPval](https://openai.com/index/introducing-swe-bench-verified/)（OpenAI 发布的 220 题、覆盖 44 种职业的基准测试）无法区分的专业评估任务。
>
> **当前语料库：97 道已验收任务**（律师：34，金融分析师：25，软件工程师：38），含真实交付物（.docx、.xlsx、.md、.pdf）。

---

## 1. 动机

GDPval 评估精通各领域的智能体在 44 种职业上的表现，每种职业 5 题。人工构建此类数据集成本高昂且缓慢——每道题都需要领域专家设计提示、撰写参考答案、制定细粒度评分标准。

**我们的洞察**：虽然领域不同，但*数据生成逻辑*是相同的。我们选取了**3 种代表性职业**，涵盖截然不同的专业工作流程：

| 职业 | GDPval 对应职业 | 真实种子来源 |
|---|---|---|
| 律师 | Lawyers | CourtListener API（联邦及州法院判例） |
| 金融分析师 | Financial and Investment Analysts | SEC EDGAR XBRL 财报 |
| 软件工程师 | Software Developers | GitHub Issues & PRs（scikit-learn、pandas 等） |

每个领域有独特的交付物格式、推理模式和事实依据要求——使其成为完整 44 职业基准的强有力代理。

---

## 2. 方法论

我们以程序化方式复现 GDPval 的设计流程：

```
真实公开材料（种子）
    ↓  [从 CourtListener / EDGAR / GitHub 采集]
大模型读取完整种子材料
    ↓  [单次结构化生成调用]
统一任务 { 题目 + 答案蓝图 + 评分标准 }
    ↓  [确定性代码渲染]
交付物文件（.docx / .xlsx / .md / .pdf）
    ↓  [硬质量校验器]
验收或拒绝
```

### 2.1 种子采集

我们不凭空编造场景，而是将每道题锚定在真实公开数据上：

- **律师**：美国最高法院、第九巡回上诉法院、第二巡回上诉法院等的完整判决书原文（通过 CourtListener REST API）。此前截断于 2,000 字符；现为 **10,000 字符**，以完整捕获判决理由、推理过程和事实细节。
- **金融分析师**：SEC EDGAR 的结构化 XBRL 财务报表（营收、净利润、资产、负债、EPS），覆盖 AAPL、MSFT、NVDA、GOOGL、META、AMZN、TSLA、BAC、JPM。
- **软件工程师**：高质量开源仓库的已合并 PR diff、描述及关联 issue（scikit-learn、pandas、matplotlib、pytorch）。

### 2.2 统一生成

单次大模型调用（Mimo v2.5 Pro）读取完整种子材料，输出结构化的 `统一任务`：

- **题目（Prompt）**：以真实工作任务委托的形式书写的任务要求。
- **答案蓝图（Answer Blueprint）**：参考答案的结构化大纲（章节、段落、公式、预期值）——与题目同步设计，确保完全匹配。
- **评分标准（Rubric）**：35–57 条细粒度评分项，每条检查答案中的特定事实或结构要素。
- **交付物类型（Deliverable Type）**：由种子内容决定（如：合同解释判例 → `legal_memo`；含 API 变更的 PR → `code_review` 或 `design_doc`）。

按职业区分的系统提示确保大模型使用领域恰当的语言和格式规范。

#### 题目是怎么生成的？（非凭空编造）

系统提示给了 LLM 一个**参考框架**，但框里的所有内容必须从种子材料里长出来：

**1. 任务类型由种子内容决定（启发式映射，非硬编码）**

系统提示中给 LLM 的类型判断指南：
- **律师**：contract terms → `contract_redline`；jurisdiction → `motion_to_dismiss`；expert testimony → `deposition_outline`
- **财务**：debt/leverage → `credit_memo`；growth/M&A → `investment_memo`；industry disruption → `industry_analysis`
- **SWE**：bug fix → `bug_fix_pr`；new API → `design_doc`；large refactor → `code_review`

LLM 根据种子材料自行判断最终类型，不是套用模板。

**2. 题目结构强制模仿 GDPval 风格**

系统提示强制四段式结构，与 GDPval 题目一致：
1. **Role and context**："You are a..." 开头，交代角色、机构、背景
2. **Materials provided**：列出附件名称和内容
3. **Task requirements**：具体步骤，编号列表
4. **Deliverable specification**：输出格式和结构要求

语气规则：禁用 "ASAP/urgent"、禁用 "Please ensure" 等 AI 腔，要求像真实合伙人/总监给下属派活。

**3. 所有事实必须来自种子材料**

用户 prompt 中明确约束：
> "ALL facts in the answer must come from the material above. Do not invent names, numbers, or citations not in the material."

LLM 收到的种子是完整原文（律师：判例全文 10,000 字符；财务：完整 XBRL 数据；SWE：PR diff 6,000 字符 + description）。题目中的**所有名字、数字、引用、事实**均来自这些真实材料。

### 2.3 确定性渲染

答案蓝图由代码渲染为真实文件（无大模型参与）：

| 格式 | 库 | 示例交付物 |
|---|---|---|
| `.docx` | python-docx | 法律备忘录、信用备忘录、投资备忘录 |
| `.xlsx` | openpyxl | 含实时公式的财务模型 |
| `.md` | 纯文本 | 代码评审、设计文档、事故复盘 |
| `.pdf` | LibreOffice headless | 从 docx 渲染的法律文档 |

### 2.4 质量漏斗

任务在验收前通过确定性检查：

- 题目长度 ≥ 1,300 字符
- 评分项数量 ≥ 35 且 ≤ 80
- 预期值数量 ≥ 3
- 分值分布不倾斜（单一分值不超过 85%）
- 评分项具体且可验证（不模糊）
- 输入附件有真实内容（≥ 100 字符）

**通过率：~92%**（最新完整批次 97/105）。

---

## 3. 数据集统计

### 3.1 整体语料

```
已验收任务总数：97
总生成数：105（97 验收 + 8 拒绝）
质量门通过率：~92%
```

### 3.2 按职业分布

| 职业 | 任务数 | 占比 | GDPval 对应职业 | GDPval 数量 |
|---|---|---|---|---|
| 软件工程师 | 38 | 39% | Software Developers | 5 |
| 律师 | 34 | 35% | Lawyers | 5 |
| 金融分析师 | 25 | 26% | Financial and Investment Analysts | 5 |

我们每个领域生成的任务数是原始 GDPval 基准的 **5–8 倍**，同时保持了相当的粒度和事实依据。

### 3.3 交付物类型

| 类型 | 数量 | 说明 |
|---|---|---|
| `legal_memo` | 34 | 分析法院判例的正式法律备忘录 |
| `code_review` | 24 | PR 合并后的技术评审 |
| `investment_memo` | 13 | 含财务指标的单页投资概览 |
| `credit_memo` | 12 | 含杠杆分析的信贷委员会备忘录 |
| `design_doc` | 12 | 新功能的架构/设计文档 |
| `bug_fix_pr` | 2 | 缺陷修复 PR 描述 |

### 3.4 文件格式

| 格式 | 数量 | 适用职业 |
|---|---|---|
| `.docx` | 44 | 律师、金融分析师 |
| `.md` | 38 | 软件工程师、部分金融分析师 |
| `.pdf` | 15 | 律师（通过 LibreOffice 从 docx 渲染） |

### 3.5 难度分布

| 难度带 | 数量 | 占比 |
|---|---|---|
| 中等 | 54 | 56% |
| 困难 | 22 | 23% |
| 简单 | 21 | 21% |

难度在种子选择阶段分配（见 `pipeline/seeds/selector.py`），并通过大模型提示中的时间指导强化：
- **简单**（1–3 小时）：范围有限、较直接的种子。
- **中等**（3–6 小时）：标准复杂度——专业工作的主体。
- **困难**（6–10 小时）：上诉法院判例、大型公司财务数据，或影响广泛的高影响力 PR。

55%/25%/20% 的目标分布是流水线设计选择，并非源自 GDPval（公开的 GDPval 数据未包含难度标注）。

### 3.6 质量指标

| 指标 | 中位数 | 平均值 | 范围 |
|---|---|---|---|
| 题目长度（字符） | 2,572 | 2,599 | 1,492 – 4,465 |
| 评分项数量 | 47 | 46.9 | 35 – 57 |
| 预期值数量 | 25 | 25.9 | 15 – 48 |
| 交付物文件大小 | ~40 KB | — | — |

---

## 4. 与 GDPval 的对齐

我们将合成任务与真实 GDPval 参考语料库（220 题）进行基准比对。关键对齐维度：

| 维度 | 我们的流水线 | GDPval 目标 |
|---|---|---|
| 每领域任务数 | 25–38 | 5 |
| 题目长度（中位数） | 2,572 字符 | ~2,024 字符 |
| 评分标准粒度 | 35–57 项 | 相近 |
| 输入附件率 | ~60% | ~57% |
| 种子锚定事实 | 100%（所有事实来自真实数据） | 100%（专家设计） |
| 交付物格式 | docx、xlsx、md、pdf | docx、xlsx、md、pdf |

---

## 5. 复现

### 5.1 环境配置

```bash
# 安装依赖
uv sync

# 配置 API 密钥（复制并填写）
cp .env.example .env
# 编辑 .env 添加：
#   MIMO_API_KEY=...
#   COURTLISTENER_API_TOKEN=...
```

### 5.2 采集种子

```bash
# 律师种子（CourtListener 判例）
uv run python -m pipeline.seeds.courtlistener

# 金融种子（SEC EDGAR XBRL）
uv run python -m pipeline.seeds.edgar_xbrl

# 软件工程师种子（GitHub PRs）
uv run python -m pipeline.seeds.github_issues
```

种子缓存在 `pipeline/seeds/store/{occupation}/`。

### 5.3 运行流水线

```bash
# 完整批次：全部 117 个种子，4 个 worker，跳过一致性验证
uv run python -m pipeline.orchestrator -n 117 --workers 4 --skip-validation
```

输出：
- 已验收任务：`data/accepted/{task_id}.json` + 输入附件
- 交付物：`data/deliverables/{task_id}/`

### 5.4 查看任务

```bash
# 查看任务的题目、评分标准和预期值
python scripts/inspect_task.py --task-id sc_xxx

# 打开渲染后的交付物
open data/deliverables/sc_xxx/*.docx
```

---

## 6. 项目结构

```
pipeline/
  seeds/
    courtlistener.py      # 采集法律判例
    edgar_xbrl.py         # 采集 SEC 财务数据
    github_issues.py      # 采集 GitHub PRs
    store/                # 缓存的种子 JSON
  scenario/
    synthesis.py          # 统一生成（题目 + 答案 + 评分标准）
    reference_answer.py   # 蓝图模型
  artifacts/
    renderer.py           # 确定性渲染（docx/xlsx/md/pdf）
    input_renderer.py     # 输入附件渲染
  validators/
    hard_quality.py       # 确定性质量检查
  diversity/
    grid.py               # 种子采样网格
  orchestrator.py         # 流水线主入口

data/
  accepted/               # 已验收任务 JSON + 输入附件
  deliverables/           # 渲染后的交付物文件
  gdpval_reference/       # 真实 GDPval 任务（用于比对）
```

---

## 7. 关键设计决策

1. **答案优先设计**：参考答案蓝图与任务题目、评分标准同步设计，而非由模型在后续"解题"生成。这保证了一致性。

2. **无预设分类体系 + 类型映射指南**：我们不硬编码交付物类型，但在系统提示中给 LLM 提供了启发式映射（如合同条款判例 → `contract_redline`）。LLM 根据种子内容自行判断，不是套模板。这样既有结构化引导，又保留了材料驱动的灵活性。

3. **金融任务为定性分析**：发现大模型在要求计算时会记错 XBRL 数字后，我们将金融任务切换为定性分析（信用备忘录、投资备忘录、行业分析），而非定量模型（DCF、差异分析）。

4. **按职业区分提示词**：共用提示词导致跨领域干扰（如金融任务提到"专利侵权"）。我们拆分为三个独立的系统提示词，消除了此问题。
