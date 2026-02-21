#!/usr/bin/env bash
# Checkpoint 1: Discussion Validation
# Part of Progressive Verification MVP

set -euo pipefail

PHASE=$1
DISCUSSION_FILE=$(ls .planning/phases/${PHASE}*/*-DISCUSSION-STATE.md 2>/dev/null | head -1)

echo "=== Checkpoint 1: Discussion Validation ==="

if [ -z "$DISCUSSION_FILE" ] || [ ! -f "$DISCUSSION_FILE" ]; then
  echo "❌ FAIL: Discussion file not found for phase $PHASE"
  echo "Expected pattern: .planning/phases/${PHASE}*/*-DISCUSSION-STATE.md"
  exit 1
fi

echo "Discussion file: $DISCUSSION_FILE"

# Check required sections
required_sections=("domain" "decisions" "specifics")
for section in "${required_sections[@]}"; do
  if ! grep -q "<$section>" "$DISCUSSION_FILE"; then
    echo "❌ FAIL: Missing <$section> section"
    exit 1
  fi
done

# Check decisions documented (at least 3)
decision_count=$(grep -c "^### " "$DISCUSSION_FILE" 2>/dev/null || echo 0)
if [ "$decision_count" -lt 3 ]; then
  echo "❌ FAIL: Only $decision_count decisions documented (need ≥3)"
  echo "Hint: Document key architectural decisions in <decisions> section"
  exit 1
fi

# Check success criteria defined
if ! grep -q "Success Criteria" "$DISCUSSION_FILE"; then
  echo "❌ FAIL: No success criteria defined"
  echo "Hint: Add 'Success Criteria' section defining what must be TRUE"
  exit 1
fi

# Calculate vagueness score (for future predictive analysis)
word_count=$(wc -w < "$DISCUSSION_FILE")
vague_words=$(grep -oi '\(maybe\|perhaps\|possibly\|probably\|TBD\|TODO\)' "$DISCUSSION_FILE" 2>/dev/null | wc -l || echo 0)
if [ "$word_count" -gt 0 ]; then
  vagueness_score=$(awk "BEGIN {printf \"%.3f\", $vague_words / $word_count}")
else
  vagueness_score="0.000"
fi

echo "✅ PASS: Discussion complete and validated"
echo "Decisions: $decision_count"
echo "Vagueness score: $vagueness_score (lower is better)"
exit 0
