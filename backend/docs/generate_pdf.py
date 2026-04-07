"""Convert GMS Technical Design Document from Markdown to PDF."""

import markdown
from weasyprint import HTML

INPUT_MD = "docs/GMS_Technical_Design_Document.md"
OUTPUT_PDF = "docs/GMS_Technical_Design_Document.pdf"

CSS = """
@page {
    size: A4;
    margin: 2cm 2.5cm;
    @bottom-center {
        content: "Page " counter(page) " of " counter(pages);
        font-size: 9px;
        color: #666;
    }
    @top-right {
        content: "GMS — Technical Design Document";
        font-size: 9px;
        color: #999;
    }
}
body {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
    font-size: 11px;
    line-height: 1.6;
    color: #1a1a1a;
}

h1 {
    font-size: 26px;
    color: #0d1117;
    border-bottom: 2px solid #0969da;
    padding-bottom: 8px;
    margin-top: 30px;
    page-break-after: avoid;
}

h1:first-of-type {
    font-size: 32px;
    text-align: center;
    border-bottom: none;
    margin-top: 80px;
    margin-bottom: 5px;
}

h2 {
    font-size: 20px;
    color: #0d1117;
    border-bottom: 1px solid #d1d9e0;
    padding-bottom: 6px;
    margin-top: 28px;
    page-break-after: avoid;
}

h3 {
    font-size: 15px;
    color: #24292f;
    margin-top: 22px;
    page-break-after: avoid;
}

h4 {
    font-size: 13px;
    color: #24292f;
    margin-top: 16px;
    page-break-after: avoid;
}

p {
    margin: 8px 0;
}

table {
    border-collapse: collapse;
    width: 100%;
    margin: 12px 0;
    font-size: 10px;
    page-break-inside: auto;
}

tr {
    page-break-inside: avoid;
}

th {
    background-color: #f0f3f6;
    border: 1px solid #d1d9e0;
    padding: 6px 8px;
    text-align: left;
    font-weight: 600;
    color: #24292f;
}

td {
    border: 1px solid #d1d9e0;
    padding: 5px 8px;
    vertical-align: top;
}

tr:nth-child(even) td {
    background-color: #f8f9fa;
}

code {
    background-color: #eff1f3;
    padding: 1px 5px;
    border-radius: 3px;
    font-family: "SF Mono", "Fira Code", Consolas, monospace;
    font-size: 10px;
    color: #0550ae;
}

pre {
    background-color: #f6f8fa;
    border: 1px solid #d1d9e0;
    border-radius: 6px;
    padding: 12px;
    overflow-x: auto;
    font-size: 10px;
    line-height: 1.5;
    page-break-inside: avoid;
}

pre code {
    background: none;
    padding: 0;
    color: #1a1a1a;
}

hr {
    border: none;
    border-top: 1px solid #d1d9e0;
    margin: 24px 0;
}

ul, ol {
    margin: 8px 0;
    padding-left: 24px;
}

li {
    margin: 3px 0;
}

strong {
    color: #0d1117;
}

blockquote {
    border-left: 3px solid #0969da;
    margin: 12px 0;
    padding: 8px 16px;
    background-color: #f0f7ff;
    color: #24292f;
}

/* Title page styling */
body > h1:first-of-type + h1 {
    text-align: center;
    font-size: 18px;
    color: #57606a;
    border-bottom: none;
    margin-top: 0;
}
"""


def main():
    with open(INPUT_MD, "r") as f:
        md_content = f.read()

    html_body = markdown.markdown(
        md_content,
        extensions=["tables", "fenced_code", "toc"],
    )

    full_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <style>{CSS}</style>
</head>
<body>
{html_body}
</body>
</html>"""

    HTML(string=full_html).write_pdf(OUTPUT_PDF)
    print(f"PDF generated: {OUTPUT_PDF}")


if __name__ == "__main__":
    main()
