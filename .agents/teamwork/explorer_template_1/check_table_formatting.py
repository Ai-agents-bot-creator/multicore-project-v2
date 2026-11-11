#!/usr/bin/env python3
import sys
from docx import Document
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

doc = Document('/mnt/Code/visualstudio/Design-arch_multi-core/white_papers/final/SRS_final.docx')

print("=== TABLE XML & FORMATTING ANALYSIS ===")

for idx, tbl in enumerate(doc.tables, 1):
    rows = len(tbl.rows)
    cols = len(tbl.columns)
    
    # Check tblPr
    tblPr = tbl._tbl.tblPr
    tblStyle = tblPr.find(qn('w:tblStyle'))
    style_val = tblStyle.get(qn('w:val')) if tblStyle is not None else "None"
    
    # Check tblHeader and cantSplit on rows
    header_rows = 0
    cantsplit_rows = 0
    for r in tbl.rows:
        trPr = r._tr.trPr
        if trPr is not None:
            if trPr.find(qn('w:tblHeader')) is not None:
                header_rows += 1
            if trPr.find(qn('w:cantSplit')) is not None:
                cantsplit_rows += 1
                
    # Check cell text alignment and formatting
    sample_cell = tbl.rows[0].cells[0] if rows > 0 and cols > 0 else None
    sample_text = sample_cell.text.strip().replace('\n', ' ') if sample_cell else ""
    
    # Check if header repeats as a data row
    hdr_texts = [c.text.strip() for c in tbl.rows[0].cells] if rows > 0 else []
    dupe_hdr = False
    for r_idx, r in enumerate(tbl.rows[1:], 2):
        if [c.text.strip() for c in r.cells] == hdr_texts:
            dupe_hdr = True
            print(f"  Table {idx} row {r_idx} is a DUPLICATE HEADER ROW!")
            
    print(f"Table {idx:02d} | Rows: {rows:2d} | Cols: {cols:2d} | Style: {style_val:<18} | HeaderRows: {header_rows} | CantSplit: {cantsplit_rows} | FirstHdr: {sample_text[:30]}")

