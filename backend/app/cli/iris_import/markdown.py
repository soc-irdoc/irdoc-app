"""A small Markdown -> HTML converter for IRIS summaries and notes.

IRDoc's rich-text fields only keep a short list of tags (see
incident_service._RICH_TEXT_TAGS), so a full Markdown renderer would mostly
produce markup that gets stripped anyway. This converter emits only tags on
that list:

- headings: h1-h3 (h4-h6 become h3)
- paragraphs: p, with br for line breaks
- inline: strong, em, s
- lists: ul/ol/li (nesting is flattened)
- blockquote

Constructs with no matching tag keep their text:

- code blocks: one escaped line per br
- inline code: plain text
- links: "text (url)"
- images: "[image: alt] (url)"
- tables: one paragraph per row, cells joined with " | "

All text is HTML-escaped, so raw HTML in a note shows up as text instead of
being interpreted.
"""
import html
import re

_HEADING = re.compile(r"^(#{1,6})\s+(.*?)\s*#*\s*$")
_FENCE = re.compile(r"^\s*(```|~~~)")
_UL_ITEM = re.compile(r"^\s*[-*+]\s+(.*)$")
_OL_ITEM = re.compile(r"^\s*\d+[.)]\s+(.*)$")
_QUOTE = re.compile(r"^\s*>\s?(.*)$")
_HR = re.compile(r"^\s*([-*_])(\s*\1){2,}\s*$")
_TABLE_SEP = re.compile(r"^\s*\|?\s*:?-+:?\s*(\|\s*:?-+:?\s*)*\|?\s*$")
_TASK = re.compile(r"^\[([ xX])\]\s+")

_CODE_SPAN = re.compile(r"`([^`]+)`")
_IMAGE = re.compile(r"!\[([^\]]*)\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")
_LINK = re.compile(r"\[([^\]]+)\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")
_AUTOLINK = re.compile(r"<(https?://[^>\s]+)>")
_BOLD = re.compile(r"(\*\*|__)(?=\S)(.+?)(?<=\S)\1")
_STRIKE = re.compile(r"~~(?=\S)(.+?)(?<=\S)~~")
_EM_STAR = re.compile(r"(?<![*\w])\*(?=\S)(.+?)(?<=\S)\*(?![*\w])")
_EM_UNDER = re.compile(r"(?<![_\w])_(?=\S)(.+?)(?<=\S)_(?![_\w])")


def _inline(text: str) -> str:
    """Convert inline Markdown in one block of text to escaped HTML."""
    # Code spans first, so their content is never formatted. Placeholders
    # contain no Markdown characters and survive escaping unchanged.
    spans: list[str] = []

    def keep(value: str) -> str:
        spans.append(value)
        return f"\x00{len(spans) - 1}\x00"

    text = _CODE_SPAN.sub(lambda m: keep(html.escape(m.group(1), quote=False)), text)
    text = _IMAGE.sub(lambda m: keep(html.escape(f"[image: {m.group(1) or 'image'}] ({m.group(2)})", quote=False)),
                      text)
    text = _LINK.sub(lambda m: f"{m.group(1)} " + keep(html.escape(f"({m.group(2)})", quote=False)), text)
    text = _AUTOLINK.sub(lambda m: keep(html.escape(m.group(1), quote=False)), text)

    text = html.escape(text, quote=False)
    text = _BOLD.sub(r"<strong>\2</strong>", text)
    text = _STRIKE.sub(r"<s>\1</s>", text)
    text = _EM_STAR.sub(r"<em>\1</em>", text)
    text = _EM_UNDER.sub(r"<em>\1</em>", text)

    return re.sub(r"\x00(\d+)\x00", lambda m: spans[int(m.group(1))], text)


def _paragraph(lines: list[str]) -> str:
    return "<p>" + "<br>".join(_inline(line.strip()) for line in lines) + "</p>"


def markdown_to_html(text: str | None) -> str:
    """Convert Markdown to HTML that uses only IRDoc's allowed rich-text tags."""
    if not text or not text.strip():
        return ""

    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    out: list[str] = []
    para: list[str] = []
    list_tag: str | None = None
    list_items: list[str] = []

    def flush_para() -> None:
        if para:
            out.append(_paragraph(para))
            para.clear()

    def flush_list() -> None:
        nonlocal list_tag
        if list_tag:
            out.append(f"<{list_tag}>" + "".join(f"<li>{item}</li>" for item in list_items) + f"</{list_tag}>")
            list_items.clear()
            list_tag = None

    def flush_all() -> None:
        flush_para()
        flush_list()

    i = 0
    while i < len(lines):
        line = lines[i]

        if _FENCE.match(line):
            flush_all()
            fence = _FENCE.match(line).group(1)
            code: list[str] = []
            i += 1
            while i < len(lines) and not lines[i].strip().startswith(fence):
                code.append(lines[i])
                i += 1
            if code:
                out.append("<p>" + "<br>".join(html.escape(c, quote=False) for c in code) + "</p>")
            i += 1  # skip the closing fence
            continue

        if not line.strip():
            flush_all()
            i += 1
            continue

        heading = _HEADING.match(line)
        if heading:
            flush_all()
            level = min(len(heading.group(1)), 3)
            out.append(f"<h{level}>{_inline(heading.group(2))}</h{level}>")
            i += 1
            continue

        if _HR.match(line):
            flush_all()
            i += 1
            continue

        if line.lstrip().startswith("|"):
            flush_all()
            while i < len(lines) and lines[i].lstrip().startswith("|"):
                row = lines[i]
                if not _TABLE_SEP.match(row):
                    cells = [c.strip() for c in row.strip().strip("|").split("|")]
                    out.append("<p>" + " | ".join(_inline(c) for c in cells) + "</p>")
                i += 1
            continue

        quote = _QUOTE.match(line)
        if quote:
            flush_all()
            quoted: list[str] = []
            while i < len(lines) and _QUOTE.match(lines[i]):
                quoted.append(_QUOTE.match(lines[i]).group(1))
                i += 1
            inner = markdown_to_html("\n".join(quoted))
            out.append(f"<blockquote>{inner}</blockquote>")
            continue

        ul = _UL_ITEM.match(line)
        ol = None if ul else _OL_ITEM.match(line)
        if ul or ol:
            flush_para()
            tag = "ul" if ul else "ol"
            if list_tag and list_tag != tag:
                flush_list()
            list_tag = tag
            item = (ul or ol).group(1)
            task = _TASK.match(item)
            if task:
                item = ("[x] " if task.group(1).lower() == "x" else "[ ] ") + item[task.end():]
            list_items.append(_inline(item))
            i += 1
            continue

        if list_tag and line.startswith((" ", "\t")):
            # Continuation of the previous list item.
            list_items[-1] += "<br>" + _inline(line.strip())
            i += 1
            continue

        flush_list()
        para.append(line)
        i += 1

    flush_all()
    return "".join(out)
