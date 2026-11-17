"""The IRIS importer's Markdown converter (app/cli/iris_import/markdown.py)."""
import re

from app.cli.iris_import.markdown import markdown_to_html
from app.services.incident_service import _RICH_TEXT_TAGS, _sanitize_html


def _tags(html: str) -> set[str]:
    return set(re.findall(r"</?([a-z0-9]+)", html))


def test_empty_input_gives_empty_string():
    assert markdown_to_html(None) == ""
    assert markdown_to_html("  \n\n ") == ""


def test_headings_are_capped_at_h3():
    assert markdown_to_html("# One") == "<h1>One</h1>"
    assert markdown_to_html("### Three ###") == "<h3>Three</h3>"
    assert markdown_to_html("#### Four") == "<h3>Four</h3>"


def test_paragraph_lines_are_joined_with_br():
    assert markdown_to_html("line one\nline two\n\nnext") == "<p>line one<br>line two</p><p>next</p>"


def test_inline_formatting():
    assert markdown_to_html("**bold** and *em* and _em2_ and ~~gone~~") == (
        "<p><strong>bold</strong> and <em>em</em> and <em>em2</em> and <s>gone</s></p>"
    )


def test_snake_case_words_are_not_italicised():
    assert markdown_to_html("run get_user_name now") == "<p>run get_user_name now</p>"


def test_lists():
    assert markdown_to_html("- a\n- b") == "<ul><li>a</li><li>b</li></ul>"
    assert markdown_to_html("1. a\n2) b") == "<ol><li>a</li><li>b</li></ol>"
    assert markdown_to_html("- [x] done\n- [ ] todo") == "<ul><li>[x] done</li><li>[ ] todo</li></ul>"


def test_list_type_change_starts_a_new_list():
    assert markdown_to_html("- a\n1. b") == "<ul><li>a</li></ul><ol><li>b</li></ol>"


def test_code_is_kept_as_escaped_text_without_formatting():
    assert markdown_to_html("```\n**not bold** <script>\n```") == "<p>**not bold** &lt;script&gt;</p>"
    assert markdown_to_html("use `a*b*c` here") == "<p>use a*b*c here</p>"


def test_links_and_images_keep_their_urls_as_text():
    assert markdown_to_html("[ticket](https://sd.local/1)") == "<p>ticket (https://sd.local/1)</p>"
    assert markdown_to_html("![shot](/datastore/1)") == "<p>[image: shot] (/datastore/1)</p>"
    assert markdown_to_html("<https://a.example/x_y_z>") == "<p>https://a.example/x_y_z</p>"


def test_tables_become_one_paragraph_per_row():
    assert markdown_to_html("| a | b |\n|---|:-:|\n| 1 | 2 |") == "<p>a | b</p><p>1 | 2</p>"


def test_blockquote():
    assert markdown_to_html("> quoted **text**\n> more") == (
        "<blockquote><p>quoted <strong>text</strong><br>more</p></blockquote>"
    )


def test_raw_html_is_escaped():
    out = markdown_to_html('<img src=x onerror="alert(1)"> & <b>hi</b>')
    assert "<img" not in out and "<b>" not in out
    assert "&lt;img" in out and "&amp;" in out


def test_output_only_uses_tags_irdoc_keeps():
    md = (
        "# H1\n## H2\n###### H6\n\npara **b** *i* ~~s~~ `c` [l](https://x)\n\n- a\n- b\n\n1. x\n\n"
        "> q\n\n```\ncode\n```\n\n| t | u |\n|---|---|\n| 1 | 2 |\n\n---\n"
    )
    out = markdown_to_html(md)
    assert _tags(out) <= set(_RICH_TEXT_TAGS)
    # IRDoc's sanitizer has nothing left to remove.
    assert _sanitize_html(out) == out
