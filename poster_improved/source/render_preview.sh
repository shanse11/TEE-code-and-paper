#!/bin/zsh
set -euo pipefail
task_dir=$(cd "$(dirname "$0")/.." && pwd)
pdftoppm -r 150 -singlefile -png "$task_dir/NDBC2026_P00145_Poster_Final_Print.pdf" "$task_dir/NDBC2026_P00145_Poster_Preview"
