#!/usr/bin/env python3
"""extract_docx.py - Extract plain text and tables from docx for verification."""
import sys
from docx import Document

if len(sys.argv) < 2:
    print(f"Usage: {sys.argv[0]} <file.docx>", file=sys.stderr)
    sys.exit(1)

doc = Document(sys.argv[1])

for p in doc.paragraphs:
    t = p.text.strip()
    if t:
        print(t)

for i, table in enumerate(doc.tables, 1):
    print(f"\n=== TABLE {i} ===")
    for row in table.rows:
        row_str = " | ".join(cell.text.strip() for cell in row.cells)
        if row_str.strip():
            print(row_str)
