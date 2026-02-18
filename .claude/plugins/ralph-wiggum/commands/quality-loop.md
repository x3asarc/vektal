# /quality-loop - Iterative Product Quality Improvement Loop

Start a Ralph Wiggum loop specifically for improving product quality scores until all products meet quality standards.

## Usage

```bash
/quality-loop --limit <n> --target-score <score> --max-iterations <n>
```

## Description

This command starts an iterative loop that:
1. Scans products from Shopify
2. Identifies products below target quality score
3. Automatically dispatches repair jobs
4. Re-checks quality after repairs
5. Repeats until all products meet target OR max iterations reached

## Options

- `--limit <n>` - Number of products to process (default: 20)
- `--target-score <score>` - Minimum quality score to achieve (default: 85)
- `--max-iterations <n>` - Maximum loop iterations (default: 10)

## Example

```bash
/quality-loop --limit 50 --target-score 90 --max-iterations 20
```

This will:
- Process 50 products
- Keep improving until all score ≥ 90/100
- Stop after 20 iterations max
- Output `<promise>COMPLETE</promise>` when target reached

## What Gets Fixed

The loop automatically repairs:
- ✅ Country of origin & HS codes
- ✅ SEO titles & descriptions
- ✅ Product tags (AI-generated)
- ✅ Collection assignments
- ✅ Product categorization

## Completion Promise

The loop completes when:
- All products meet target score, OR
- No more improvements possible, OR
- Max iterations reached

Outputs: `<promise>QUALITY_TARGET_REACHED</promise>`

## Integration with Quality Agent

This command wraps the product quality agent with Ralph Wiggum's iterative loop:

```bash
python orchestrator/product_quality_agent.py --scan-all --limit <n> --auto-repair
```

The loop monitors quality scores and continues until improvement plateaus or target is reached.
