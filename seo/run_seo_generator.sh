#!/bin/bash
# SEO Content Generator - Convenience Runner
#
# Generate mode:
#   ./run_seo_generator.sh --vendor "Pentart" --output data/pentart_seo.csv
#   ./run_seo_generator.sh --barcode "1234567890"
#
# Push mode:
#   ./run_seo_generator.sh --push-csv data/pentart_seo.csv

cd "$(dirname "$0")/.."
venv/bin/python seo/generate_seo_quick.py "$@"
