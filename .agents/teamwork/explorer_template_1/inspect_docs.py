#!/usr/bin/env python3
import sys
import os
import re
from docx import Document
from docx.table import Table
from docx.text.paragraph import Paragraph

def dump_structure(path, label):
    doc = Document(path)
    print(f"=== STRUCTURE OF {label} ({path}) ===")
    
    def iter_blocks(parent, d):
        for child in parent.iterchildren():
            if child.tag.endswith('}p'):
                yield Paragraph(child, d)
            elif child.tag.endswith('}tbl'):
                yield Table(child, d)

    block_idx = 0
    p_idx = 0
    t_idx = 0
    headings = []
    tables_info = []
    
    for b in iter_blocks(doc.element.body, doc):
        block_idx += 1
        if isinstance(b, Paragraph):
            p_idx += 1
            t = b.text.strip()
            st = b.style.name if b.style else "?"
            if st.startswith("Heading") or st.startswith("Title") or st.startswith("Subtitle") or re.match(r"^\d+(\.\d+)*\s+", t):
                headings.append((block_idx, p_idx, st, t))
                print(f"[P{p_idx} | B{block_idx}] {st}: {t}")
        elif isinstance(b, Table):
            t_idx += 1
            rows = len(b.rows)
            cols = len(b.columns) if b.rows else 0
            hdr = [c.text.strip().replace('\n', ' ') for c in b.rows[0].cells] if b.rows else []
            tables_info.append((block_idx, t_idx, rows, cols, hdr))
            print(f"[T{t_idx} | B{block_idx}] Table {t_idx} ({rows}x{cols}): Headers = {hdr[:5]}")
            
    return headings, tables_info

print("Extracting doc_final...")
h_final, t_final = dump_structure('/mnt/Code/visualstudio/Design-arch_multi-core/white_papers/final/SRS_final.docx', 'SRS_final')
print("\nExtracting doc_tmpl...")
h_tmpl, t_tmpl = dump_structure('/mnt/Code/visualstudio/Design-arch_multi-core/white_papers/SRS/SRS_Template_final.docx', 'SRS_Template')

