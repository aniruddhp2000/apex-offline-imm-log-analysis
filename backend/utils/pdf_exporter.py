import os
import re

class PDFExporter:
    @staticmethod
    def markdown_to_html(markdown_str: str) -> str:
        # Simple markdown-to-HTML parser (handles headings, bullets, blocks, alerts)
        html = markdown_str
        
        # Heading 1
        html = re.sub(r"^#\s+(.+)$", r"<h1>\1</h1>", html, flags=re.MULTILINE)
        # Heading 2
        html = re.sub(r"^##\s+(.+)$", r"<h2>\1</h2>", html, flags=re.MULTILINE)
        # Heading 3
        html = re.sub(r"^###\s+(.+)$", r"<h3>\1</h3>", html, flags=re.MULTILINE)
        # Heading 4
        html = re.sub(r"^####\s+(.+)$", r"<h4>\1</h4>", html, flags=re.MULTILINE)

        # Bold
        html = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", html)
        # Italic
        html = re.sub(r"\*(.+?)\*", r"<em>\1</em>", html)
        # Inline code
        html = re.sub(r"`(.+?)`", r"<code>\1</code>", html)

        # Mermaid block wrapping
        html = re.sub(r"```mermaid\n(.*?)\n```", r'<div class="mermaid">\1</div>', html, flags=re.DOTALL)
        
        # Code blocks
        html = re.sub(r"```(.*?)\n(.*?)\n```", r'<pre><code>\2</code></pre>', html, flags=re.DOTALL)

        # Alert boxes (GitHub syntax)
        # Warning
        html = re.sub(r"^>\s+\[!WARNING\]\s*\n(.*?)(?=\n\n|\n[^\s>])", r'<div class="alert alert-warning">\1</div>', html, flags=re.MULTILINE | re.DOTALL)
        # Critical
        html = re.sub(r"^>\s+\[!CRITICAL\]\s*\n(.*?)(?=\n\n|\n[^\s>])", r'<div class="alert alert-critical">\1</div>', html, flags=re.MULTILINE | re.DOTALL)
        # Important
        html = re.sub(r"^>\s+\[!IMPORTANT\]\s*\n(.*?)(?=\n\n|\n[^\s>])", r'<div class="alert alert-important">\1</div>', html, flags=re.MULTILINE | re.DOTALL)
        # Note
        html = re.sub(r"^>\s+\[!NOTE\]\s*\n(.*?)(?=\n\n|\n[^\s>])", r'<div class="alert alert-note">\1</div>', html, flags=re.MULTILINE | re.DOTALL)

        # Simple list items (bullet points)
        html = re.sub(r"^\*\s+(.+)$", r"<li>\1</li>", html, flags=re.MULTILINE)
        html = re.sub(r"^(\d+)\.\s+(.+)$", r"<li>\2</li>", html, flags=re.MULTILINE)

        # Tables
        # Matches markdown tables and wraps them
        # Note: A real markdown parser works better, but simple line regex covers standard reports
        lines = html.split('\n')
        in_table = False
        table_lines = []
        parsed_lines = []
        for line in lines:
            if line.startswith('|'):
                in_table = True
                table_lines.append(line)
            else:
                if in_table:
                    # Parse the table block
                    parsed_lines.append(PDFExporter._parse_table_block(table_lines))
                    in_table = False
                    table_lines = []
                parsed_lines.append(line)
        if in_table:
            parsed_lines.append(PDFExporter._parse_table_block(table_lines))
        
        html = "\n".join(parsed_lines)

        # Paragraphs (basic wrapping)
        html = re.sub(r"\n\n([^\n<]+)\n\n", r"\n\n<p>\1</p>\n\n", html)

        return html

    @staticmethod
    def _parse_table_block(lines: list) -> str:
        table_html = ['<table class="report-table">']
        is_first = True
        for line in lines:
            if "---" in line:
                continue # Skip divider
            cells = [c.strip() for c in line.split('|')[1:-1]]
            tag = "th" if is_first else "td"
            row_content = "".join([f"<{tag}>{c}</{tag}>" for c in cells])
            table_html.append(f"<tr>{row_content}</tr>")
            is_first = False
        table_html.append('</table>')
        return "\n".join(table_html)

    @classmethod
    def generate_html_report(cls, title: str, markdown_str: str) -> str:
        body_content = cls.markdown_to_html(markdown_str)
        
        template = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>{title}</title>
    <script src="https://cdn.jsdelivr.net/npm/mermaid/dist/mermaid.min.js"></script>
    <script>
        document.addEventListener("DOMContentLoaded", function() {{
            mermaid.initialize({{ startOnLoad: true, theme: 'neutral' }});
        }});
    </script>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            color: #333;
            line-height: 1.6;
            max-width: 900px;
            margin: 40px auto;
            padding: 0 20px;
            background-color: #fff;
        }}
        h1 {{
            border-bottom: 2px solid #eaecef;
            padding-bottom: 10px;
            color: #1a1a1a;
        }}
        h2 {{
            border-bottom: 1px solid #eaecef;
            padding-bottom: 5px;
            color: #24292e;
            margin-top: 30px;
        }}
        h3 {{
            color: #2f363d;
        }}
        p, li {{
            font-size: 16px;
        }}
        pre {{
            background-color: #f6f8fa;
            border-radius: 6px;
            padding: 16px;
            overflow: auto;
            font-family: "SFMono-Regular", Consolas, "Liberation Mono", Menlo, monospace;
        }}
        code {{
            background-color: rgba(27,31,35,0.05);
            padding: 0.2em 0.4em;
            border-radius: 3px;
            font-family: "SFMono-Regular", Consolas, "Liberation Mono", Menlo, monospace;
            font-size: 85%;
        }}
        pre code {{
            background-color: transparent;
            padding: 0;
        }}
        .report-table {{
            border-collapse: collapse;
            width: 100%;
            margin: 20px 0;
        }}
        .report-table th, .report-table td {{
            border: 1px solid #dfe2e5;
            padding: 8px 12px;
            text-align: left;
        }}
        .report-table th {{
            background-color: #f6f8fa;
        }}
        .report-table tr:nth-child(even) {{
            background-color: #f9f9f9;
        }}
        .alert {{
            padding: 12px 16px;
            border-left: 4px solid;
            border-radius: 4px;
            margin: 20px 0;
        }}
        .alert-warning {{
            background-color: #fff8c5;
            border-left-color: #d29922;
            color: #765700;
        }}
        .alert-critical {{
            background-color: #ffebe9;
            border-left-color: #cf222e;
            color: #a40e26;
        }}
        .alert-important {{
            background-color: #f0f8ff;
            border-left-color: #0366d6;
            color: #004085;
        }}
        .alert-note {{
            background-color: #f6f8fa;
            border-left-color: #24292e;
            color: #24292e;
        }}
        .mermaid {{
            margin: 20px 0;
            text-align: center;
        }}
        .no-print {{
            margin-bottom: 20px;
            display: flex;
            gap: 10px;
        }}
        button {{
            padding: 10px 16px;
            font-weight: 600;
            border-radius: 4px;
            border: 1px solid #ccc;
            background: #f6f8fa;
            cursor: pointer;
        }}
        button.primary {{
            background: #0366d6;
            color: white;
            border-color: #0366d6;
        }}
        @media print {{
            body {{
                margin: 0;
                padding: 0;
            }}
            .no-print {{
                display: none;
            }}
            pre, blockquote, .alert {{
                page-break-inside: avoid;
            }}
        }}
    </style>
</head>
<body>
    <div class="no-print">
        <button class="primary" onclick="window.print()">Print / Save as PDF</button>
        <button onclick="window.close()">Close Tab</button>
    </div>
    {body_content}
</body>
</html>
"""
        return template
