@echo off
REM SEO Content Generator - Convenience Runner
REM
REM Generate mode:
REM   run_seo_generator.bat --vendor "Pentart" --output data/pentart_seo.csv
REM   run_seo_generator.bat --barcode "1234567890"
REM
REM Push mode:
REM   run_seo_generator.bat --push-csv data/pentart_seo.csv

cd /d "%~dp0\.."
venv\Scripts\python.exe seo\generate_seo_quick.py %*
