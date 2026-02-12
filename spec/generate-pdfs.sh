#!/bin/bash
# Generate PDF files from Markdown files in this directory.
# Usage: ./generate-pdfs.sh [file1.md file2.md ...]
# If no files specified, converts all *.md files.
# Requires: pandoc and a LaTeX engine (pdflatex, xelatex, or lualatex)
#
# Install dependencies (Ubuntu/Debian):
#   sudo apt install pandoc texlive-latex-recommended texlive-fonts-recommended texlive-latex-extra

set -euo pipefail
cd "$(dirname "$0")"

if ! command -v pandoc &>/dev/null; then
    echo "Error: pandoc is not installed." >&2
    echo "  sudo apt install pandoc texlive-latex-recommended texlive-fonts-recommended texlive-latex-extra --pdf-engine=xelatex" >&2
    exit 1
fi

if [ $# -gt 0 ]; then
    files=("$@")
else
    files=(*.md)
fi

count=0
for md in "${files[@]}"; do
    [ -f "$md" ] || continue
    pdf="${md%.md}.pdf"
    echo "Converting $md -> $pdf"
    pandoc "$md" -o "$pdf" \
        --pdf-engine=xelatex \
        -V geometry:margin=1in \
        -V colorlinks=true \
        --toc
    count=$((count + 1))
done

echo "Done. Generated $count PDF file(s)."
