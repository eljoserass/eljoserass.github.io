#!/usr/bin/env python3
# Converts markdown to HTML with template structure. Handles: headings, paragraphs, bold, italic, code, lists, blockquotes, links, hr. Ignores: images, small tags.

import argparse
import markdown

def convert_markdown_to_html(md_content, title="My Site"):
    """Convert markdown to full HTML page matching template structure."""
    
    # Convert markdown to HTML body content
    md = markdown.Markdown(extensions=['extra', 'codehilite'])
    body_html = md.convert(md_content)
    
    # Wrap in full HTML structure matching template
    html_template = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title}</title>
  <link rel="stylesheet" href="/style.css">
</head>
<body>
  {body_html}
</body>
</html>"""
    
    return html_template

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Convert Markdown to HTML with custom template')
    parser.add_argument('input', help='Input markdown file')
    parser.add_argument('output', help='Output HTML file')
    parser.add_argument('-t', '--title', default='My Site', help='Page title (default: My Site)')
    
    args = parser.parse_args()
    
    # Read markdown file
    with open(args.input, 'r', encoding='utf-8') as f:
        md_content = f.read()
    
    # Convert to HTML
    html = convert_markdown_to_html(md_content, args.title)
    
    # Write output file
    with open(args.output, 'w', encoding='utf-8') as f:
        f.write(html)
