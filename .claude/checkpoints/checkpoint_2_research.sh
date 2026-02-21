#!/usr/bin/env bash
# Checkpoint 2: Research Validation
# Part of Progressive Verification MVP

set -euo pipefail

PHASE=$1
RESEARCH_FILE=$(ls .planning/phases/${PHASE}*/*-RESEARCH.md 2>/dev/null | head -1)

echo "=== Checkpoint 2: Research Validation ==="

if [ -z "$RESEARCH_FILE" ] || [ ! -f "$RESEARCH_FILE" ]; then
  echo "❌ FAIL: Research file not found for phase $PHASE"
  echo "Expected pattern: .planning/phases/${PHASE}*/*-RESEARCH.md"
  exit 1
fi

echo "Research file: $RESEARCH_FILE"

# Verify research depth (character count)
char_count=$(wc -c < "$RESEARCH_FILE")
if [ "$char_count" -lt 2000 ]; then
  echo "❌ FAIL: Research too shallow ($char_count chars, need ≥2000)"
  echo "Hint: Research should cover architecture patterns, trade-offs, and standard practices"
  exit 1
fi

# Extract dependencies mentioned
dependencies=$(grep -oP '`[a-z0-9_-]+`' "$RESEARCH_FILE" 2>/dev/null | sort -u | wc -l || echo 0)

# Check for standard patterns
has_standards=0
if grep -q -E "(standard|recommended|industry|best practice)" "$RESEARCH_FILE"; then
  has_standards=1
fi

if [ "$has_standards" -eq 0 ]; then
  echo "⚠️  WARNING: No standard patterns referenced"
  echo "Consider: Are we using proven patterns or inventing custom solutions?"
fi

echo "✅ PASS: Research complete and validated"
echo "Depth: $char_count characters"
echo "Dependencies mentioned: $dependencies"
echo "Standard patterns referenced: $([ $has_standards -eq 1 ] && echo 'Yes' || echo 'No')"
exit 0
