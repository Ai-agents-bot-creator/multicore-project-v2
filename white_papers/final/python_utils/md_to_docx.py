#!/usr/bin/env python3
"""
Convert SRS_REVIEW_v2.md to a professionally formatted DOCX document.
Uses python-docx with proper styles, tables, and formatting.
"""

from docx import Document
from docx.shared import Inches, Pt, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.style import WD_STYLE_TYPE
import re
import sys

def create_styles(doc):
    """Create custom styles for the document."""
    style = doc.styles['Normal']
    font = style.font
    font.name = 'Calibri'
    font.size = Pt(11)
    style.paragraph_format.space_after = Pt(6)
    style.paragraph_format.line_spacing = 1.15

    # Code block style
    if 'Code Block' not in doc.styles:
        code_style = doc.styles.add_style('Code Block', WD_STYLE_TYPE.PARAGRAPH)
        code_style.base_style = doc.styles['Normal']
        code_font = code_style.font
        code_font.name = 'Consolas'
        code_font.size = Pt(9)
        code_font.color.rgb = RGBColor(0x33, 0x33, 0x33)
        code_style.paragraph_format.space_before = Pt(6)
        code_style.paragraph_format.space_after = Pt(6)
        code_style.paragraph_format.left_indent = Cm(1)
        code_style.paragraph_format.line_spacing = 1.0

    # Table cell style
    if 'Table Cell' not in doc.styles:
        cell_style = doc.styles.add_style('Table Cell', WD_STYLE_TYPE.PARAGRAPH)
        cell_style.base_style = doc.styles['Normal']
        cell_font = cell_style.font
        cell_font.name = 'Calibri'
        cell_font.size = Pt(9)
        cell_style.paragraph_format.space_before = Pt(2)
        cell_style.paragraph_format.space_after = Pt(2)

    # Heading styles customization
    for i in range(1, 5):
        heading_style = doc.styles[f'Heading {i}']
        heading_font = heading_style.font
        heading_font.name = 'Calibri'
        heading_font.color.rgb = RGBColor(0x1B, 0x3A, 0x5C)  # Dark blue
        if i == 1:
            heading_font.size = Pt(22)
            heading_font.bold = True
            heading_style.paragraph_format.space_before = Pt(24)
            heading_style.paragraph_format.space_after = Pt(12)
        elif i == 2:
            heading_font.size = Pt(18)
            heading_font.bold = True
            heading_style.paragraph_format.space_before = Pt(18)
            heading_style.paragraph_format.space_after = Pt(10)
        elif i == 3:
            heading_font.size = Pt(14)
            heading_font.bold = True
            heading_style.paragraph_format.space_before = Pt(14)
            heading_style.paragraph_format.space_after = Pt(8)
        elif i == 4:
            heading_font.size = Pt(12)
            heading_font.bold = True
            heading_style.paragraph_format.space_before = Pt(10)
            heading_style.paragraph_format.space_after = Pt(6)


def add_paragraph_with_formatting(doc, text, style='Normal'):
    """Add a paragraph handling bold, italic, and inline code."""
    p = doc.add_paragraph(style=style)
    
    # Split by markdown formatting
    parts = re.split(r'(\*\*.*?\*\*|\*.*?\*|`.*?`)', text)
    
    for part in parts:
        if not part:
            continue
        run = p.add_run(part)
        if part.startswith('**') and part.endswith('**'):
            run.bold = True
            run.text = part[2:-2]
        elif part.startswith('*') and part.endswith('*'):
            run.italic = True
            run.text = part[1:-1]
        elif part.startswith('`') and part.endswith('`'):
            run.font.name = 'Consolas'
            run.font.size = Pt(9)
            run.font.color.rgb = RGBColor(0x33, 0x33, 0x33)
            run.text = part[1:-1]
    return p


def parse_markdown_table(lines, start_idx):
    """Parse a markdown table starting at start_idx. Returns (table_data, next_idx)."""
    table_lines = []
    i = start_idx
    
    # Collect table lines
    while i < len(lines) and lines[i].strip().startswith('|'):
        table_lines.append(lines[i].rstrip())
        i += 1
    
    if not table_lines:
        return None, start_idx
    
    # Parse rows
    rows = []
    for line in table_lines:
        # Split by | and clean
        cells = [cell.strip() for cell in line.split('|')]
        # Remove empty first/last from leading/trailing |
        if cells and not cells[0]:
            cells = cells[1:]
        if cells and not cells[-1]:
            cells = cells[:-1]
        rows.append(cells)
    
    # Check for separator row (---)
    if len(rows) > 1:
        separator = rows[1]
        if all(re.match(r'^:?-+:?$', cell) for cell in separator):
            # Has header row
            header = rows[0]
            data_rows = rows[2:]
            return (header, data_rows), i
    
    return (rows[0], rows[1:]), i


def add_markdown_table(doc, header, data_rows):
    """Add a formatted table to the document."""
    if not header:
        return
    
    table = doc.add_table(rows=1 + len(data_rows), cols=len(header))
    table.style = 'Table Grid'
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    
    # Header row
    hdr_cells = table.rows[0].cells
    for j, cell_text in enumerate(header):
        p = hdr_cells[j].paragraphs[0]
        run = p.add_run(cell_text)
        run.bold = True
        run.font.size = Pt(9)
        run.font.name = 'Calibri'
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        # Set shading for header
        from docx.oxml.ns import qn
        from docx.oxml import OxmlElement
        shading = OxmlElement('w:shd')
        shading.set(qn('w:fill'), '1B3A5C')
        shading.set(qn('w:val'), 'clear')
        hdr_cells[j]._tc.get_or_add_tcPr().append(shading)
        run.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
    
    # Data rows
    for i, row_data in enumerate(data_rows):
        row_cells = table.rows[i + 1].cells
        for j, cell_text in enumerate(row_data):
            if j < len(row_cells):
                p = row_cells[j].paragraphs[0]
                # Handle multiline cell content
                lines = cell_text.split('\n')
                for k, line in enumerate(lines):
                    if k > 0:
                        p = row_cells[j].add_paragraph()
                    run = p.add_run(line)
                    run.font.size = Pt(9)
                    run.font.name = 'Calibri'
                p.alignment = WD_ALIGN_PARAGRAPH.LEFT
    
    doc.add_paragraph()  # Space after table


def process_markdown_file(doc, md_path):
    """Process the markdown file and add content to the document."""
    with open(md_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    i = 0
    in_code_block = False
    code_block_lines = []
    code_lang = ''
    
    while i < len(lines):
        line = lines[i].rstrip('\n')
        
        # Code block handling
        if line.startswith('```'):
            if not in_code_block:
                in_code_block = True
                code_lang = line[3:].strip()
                code_block_lines = []
            else:
                in_code_block = False
                # Add code block
                code_text = '\n'.join(code_block_lines)
                p = doc.add_paragraph(style='Code Block')
                run = p.add_run(code_text)
                run.font.name = 'Consolas'
                run.font.size = Pt(9)
            i += 1
            continue
        
        if in_code_block:
            code_block_lines.append(line)
            i += 1
            continue
        
        # Horizontal rule
        if line.strip() == '---':
            doc.add_paragraph().add_run('_' * 60).font.color.rgb = RGBColor(0x99, 0x99, 0x99)
            i += 1
            continue
        
        # Headings
        heading_match = re.match(r'^(#{1,4})\s+(.*)', line)
        if heading_match:
            level = len(heading_match.group(1))
            text = heading_match.group(2)
            doc.add_heading(text, level=level)
            i += 1
            continue
        
        # Table
        if line.strip().startswith('|'):
            table_data, next_i = parse_markdown_table(lines, i)
            if table_data:
                header, data_rows = table_data
                add_markdown_table(doc, header, data_rows)
                i = next_i
                continue
        
        # Bullet points
        bullet_match = re.match(r'^(\s*)[-*+]\s+(.*)', line)
        if bullet_match:
            indent = len(bullet_match.group(1))
            text = bullet_match.group(2)
            p = doc.add_paragraph(style='List Bullet')
            p.clear()
            add_paragraph_with_formatting(doc, text, 'List Bullet')
            # Adjust indent level
            if indent >= 4:
                p.paragraph_format.left_indent = Cm(2)
            i += 1
            continue
        
        # Numbered list
        num_match = re.match(r'^(\s*)\d+\.\s+(.*)', line)
        if num_match:
            indent = len(num_match.group(1))
            text = num_match.group(2)
            p = doc.add_paragraph(style='List Number')
            p.clear()
            add_paragraph_with_formatting(doc, text, 'List Number')
            i += 1
            continue
        
        # Blockquote
        if line.startswith('> '):
            text = line[2:]
            p = doc.add_paragraph(style='Quote')
            p.clear()
            run = p.add_run(text)
            run.italic = True
            i += 1
            continue
        
        # Empty line
        if not line.strip():
            doc.add_paragraph()
            i += 1
            continue
        
        # Regular paragraph
        add_paragraph_with_formatting(doc, line)
        i += 1


def main():
    md_path = '/mnt/Code/visualstudio/Design-arch_multi-core/white_papers/final/SRS_REVIEW_v2.md'
    output_path = '/mnt/Code/visualstudio/Design-arch_multi-core/white_papers/final/SRS_REVIEW_v2.docx'
    
    doc = Document()
    
    # Set default margins
    for section in doc.sections:
        section.top_margin = Cm(2.54)
        section.bottom_margin = Cm(2.54)
        section.left_margin = Cm(2.54)
        section.right_margin = Cm(2.54)
    
    create_styles(doc)
    
    # Add title page
    title_p = doc.add_paragraph()
    title_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    title_p.paragraph_format.space_before = Pt(72)
    run = title_p.add_run('Comprehensive System Requirements\nSpecification Review Report (SRS v2.0)')
    run.bold = True
    run.font.size = Pt(28)
    run.font.color.rgb = RGBColor(0x1B, 0x3A, 0x5C)
    run.font.name = 'Calibri'
    
    subtitle_p = doc.add_paragraph()
    subtitle_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = subtitle_p.add_run('Deep Verification, Standards Benchmarking, Defect Adjudication,\nand Independent Gate Sign-Off')
    run.font.size = Pt(14)
    run.font.color.rgb = RGBColor(0x4A, 0x4A, 0x4A)
    run.font.name = 'Calibri'
    
    doc.add_paragraph()
    doc.add_paragraph()
    
    # Metadata table
    meta_table = doc.add_table(rows=9, cols=2)
    meta_table.style = 'Table Grid'
    meta_data = [
        ('Document Identifier', 'SRS_REVIEW_v2.md'),
        ('Target Document Under Review', 'SRS_final_v2.docx (v2.0, Elevated Institutional Release)'),
        ('Baseline Document', 'SRS_final.docx (v0.2, Patched Working Draft)'),
        ('Verification Suite', 'verify_srs.py (v2.0 Hardened, 67 Automated Checks)'),
        ('Authoring Body', 'Worker Report Writer 1 (Group 16 Documentation & Verification Team)'),
        ('Project Group', 'Group 16 (PGCP VLSI)'),
        ('Authors', 'Durgesh Kolhe, Sai Charan, Additya, Joshna'),
        ('Group Mentor', 'Mr. Hemat'),
        ('Date of Release', '2026-11-09'),
    ]
    for i, (key, value) in enumerate(meta_data):
        cell_key = meta_table.rows[i].cells[0]
        cell_val = meta_table.rows[i].cells[1]
        run = cell_key.paragraphs[0].add_run(key)
        run.bold = True
        run.font.size = Pt(10)
        run = cell_val.paragraphs[0].add_run(value)
        run.font.size = Pt(10)
    
    doc.add_paragraph()
    
    # Final status
    status_p = doc.add_paragraph()
    status_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = status_p.add_run('Final Verification Status: PASSED / UNANIMOUS APPROVAL (5/5 GATES)')
    run.bold = True
    run.font.size = Pt(14)
    run.font.color.rgb = RGBColor(0x00, 0x7A, 0x33)
    
    doc.add_page_break()
    
    # Process the markdown content
    process_markdown_file(doc, md_path)
    
    doc.save(output_path)
    print(f"Document saved to {output_path}")


if __name__ == '__main__':
    main()