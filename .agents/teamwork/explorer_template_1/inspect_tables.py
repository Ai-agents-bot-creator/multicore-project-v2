#!/usr/bin/env python3
import sys
import re
from docx import Document

doc = Document('/mnt/Code/visualstudio/Design-arch_multi-core/white_papers/final/SRS_final.docx')

print(f"Total tables: {len(doc.tables)}")

placeholders = ['TODO', 'TBD', '[TBD]', '[', ']', '???', 'FIXME', 'TBA']

for idx, tbl in enumerate(doc.tables, 1):
    print(f"\n==================================================")
    print(f"TABLE {idx}: {len(tbl.rows)} rows x {len(tbl.columns)} cols")
    
    # Check headers
    if not tbl.rows:
        print("  WARNING: Empty table!")
        continue
    
    hdr = [c.text.strip().replace('\n', ' ') for c in tbl.rows[0].cells]
    print(f"  Header: {hdr}")
    
    # Check for duplicate headers in subsequent rows
    for r_idx, row in enumerate(tbl.rows[1:], 2):
        row_cells = [c.text.strip().replace('\n', ' ') for c in row.cells]
        if row_cells == hdr:
            print(f"  WARNING: Row {r_idx} is a DUPLICATE HEADER ROW!")
            
    # Check column count consistency across rows
    for r_idx, row in enumerate(tbl.rows, 1):
        if len(row.cells) != len(tbl.columns):
            print(f"  WARNING: Row {r_idx} has {len(row.cells)} cells, expected {len(tbl.columns)}")
            
    # Check for empty cells or placeholders
    empty_cells = []
    placeholder_cells = []
    for r_idx, row in enumerate(tbl.rows, 1):
        for c_idx, cell in enumerate(row.cells, 1):
            txt = cell.text.strip()
            if not txt:
                empty_cells.append((r_idx, c_idx))
            for ph in ['TODO', 'TBD', '[TBD]', '???', 'FIXME', 'TBA', '[date]', '[name]']:
                if ph.lower() in txt.lower():
                    placeholder_cells.append((r_idx, c_idx, txt))
            if re.search(r"\[[A-Za-z0-9_\s/.-]+\]", txt):
                placeholder_cells.append((r_idx, c_idx, txt))
                
    if empty_cells:
        print(f"  Empty cells ({len(empty_cells)}): {empty_cells[:10]}")
    if placeholder_cells:
        print(f"  Placeholder cells ({len(placeholder_cells)}): {placeholder_cells[:10]}")

    # Print first 2 data rows
    for r_idx, row in enumerate(tbl.rows[1:3], 2):
        print(f"  Row {r_idx}: {[c.text.strip().replace(chr(10), ' ') for c in row.cells]}")

