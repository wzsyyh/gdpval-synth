#!/usr/bin/env bash
# GDPval 合成任务生成流水线 —— 一键运行脚本
#
# 用法:
#   ./quickstart.sh              # 完整流程（检查种子 → 运行流水线 → 生成图表）
#   ./quickstart.sh --skip-seeds # 跳过种子采集（种子已存在时）
#   ./quickstart.sh --small      # 小规模测试：只跑 10 个种子
#

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

SKIP_SEEDS=false
BATCH_SIZE=117
WORKERS=4

# 解析参数
while [[ $# -gt 0 ]]; do
    case $1 in
        --skip-seeds)
            SKIP_SEEDS=true
            shift
            ;;
        --small)
            BATCH_SIZE=10
            WORKERS=2
            shift
            ;;
        -h|--help)
            echo "用法: $0 [--skip-seeds] [--small]"
            echo ""
            echo "选项:"
            echo "  --skip-seeds   跳过种子采集（种子已存在时使用）"
            echo "  --small        小规模测试：只跑 10 个种子，2 个 worker"
            exit 0
            ;;
        *)
            echo "未知选项: $1"
            echo "用法: $0 [--skip-seeds] [--small]"
            exit 1
            ;;
    esac
done

echo "========================================"
echo "GDPval 合成任务生成流水线"
echo "========================================"
echo ""

# ── 1. 检查 .env ──
if [[ ! -f .env ]]; then
    echo "⚠️  未找到 .env 文件"
    if [[ -f .env.example ]]; then
        echo "   已复制 .env.example → .env，请先编辑填写 API key"
        cp .env.example .env
    else
        echo "   请创建 .env 文件并填写以下变量："
        echo "     MIMO_API_KEY=..."
        echo "     COURTLISTENER_API_TOKEN=..."
        echo "     GITHUB_TOKEN=..."
    fi
    exit 1
fi

# 检查关键变量是否已填写
MISSING_VARS=()
for var in MIMO_API_KEY COURTLISTENER_API_TOKEN GITHUB_TOKEN; do
    if ! grep -qE "^${var}=[^\.]+" .env 2>/dev/null; then
        MISSING_VARS+=("$var")
    fi
done

if [[ ${#MISSING_VARS[@]} -gt 0 ]]; then
    echo "⚠️  .env 中以下变量未填写："
    printf "   - %s\n" "${MISSING_VARS[@]}"
    exit 1
fi

echo "✅ .env 配置检查通过"
echo ""

# ── 2. 安装依赖 ──
echo "📦 安装依赖..."
uv sync
echo "✅ 依赖安装完成"
echo ""

# ── 3. 采集种子 ──
if [[ "$SKIP_SEEDS" == true ]]; then
    echo "⏭️  跳过种子采集（--skip-seeds）"
else
    echo "🌱 检查种子..."
    SEED_DIRS=(
        "pipeline/seeds/store/lawyer"
        "pipeline/seeds/store/financial_analyst"
        "pipeline/seeds/store/software_engineer"
    )

    NEED_HARVEST=false
    for dir in "${SEED_DIRS[@]}"; do
        count=$(find "$dir" -name "*.json" 2>/dev/null | wc -l | tr -d ' ')
        if [[ "$count" -eq 0 ]]; then
            echo "   ❌ $dir: 0 个种子"
            NEED_HARVEST=true
        else
            echo "   ✅ $dir: $count 个种子"
        fi
    done

    if [[ "$NEED_HARVEST" == true ]]; then
        echo ""
        echo "🌾 开始采集种子..."
        uv run python -m pipeline.seeds.courtlistener
        uv run python -m pipeline.seeds.edgar_xbrl
        uv run python -m pipeline.seeds.github_issues
        echo "✅ 种子采集完成"
    else
        echo "✅ 所有种子已存在，跳过采集"
    fi
fi
echo ""

# ── 4. 运行流水线 ──
echo "🚀 运行流水线（batch_size=$BATCH_SIZE, workers=$WORKERS）..."
uv run python -m pipeline.orchestrator -n "$BATCH_SIZE" --workers "$WORKERS" --skip-validation
echo "✅ 流水线运行完成"
echo ""

# ── 5. 生成图表 ──
echo "📊 生成报告图表..."
uv run python scripts/generate_charts.py
echo "✅ 图表生成完成"
echo ""

# ── 6. 结果汇总 ──
echo "========================================"
echo "🎉 全部完成！"
echo "========================================"
echo ""

ACCEPTED_COUNT=$(find data/accepted -name "*.json" 2>/dev/null | wc -l | tr -d ' ')
REJECTED_COUNT=$(find data/rejected -name "*.json" 2>/dev/null | wc -l | tr -d ' ')

echo "📋 结果统计:"
echo "   已验收任务: $ACCEPTED_COUNT"
echo "   已拒绝任务: $REJECTED_COUNT"
echo ""
echo "📁 输出目录:"
echo "   data/accepted/       — 已验收任务 JSON + 附件"
echo "   data/deliverables/   — 渲染后的交付物文件"
echo "   assets/              — 报告图表"
echo ""
echo "🔍 查看单个任务:"
echo "   uv run python scripts/inspect_task.py --task-id sc_xxx"
echo ""
