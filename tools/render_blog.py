#!/usr/bin/env python3

from __future__ import annotations

import html
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT / "essays"
OUT_DIR = ROOT / "blog"
CSS_PATH = "/stylesheets/blog.css"
ANALYTICS_ID = "G-DFRFDMXXVN"


@dataclass
class Heading:
    level: int
    text: str
    ident: str


@dataclass
class Post:
    title: str
    slug: str
    date: str
    summary: str
    source_path: Path
    body_html: str
    toc: list[Heading]


def slugify(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return slug or "section"


def highlight_code(code: str, lang: str) -> str:
    language = lang.lower()
    if language in {"sh", "shell", "zsh"}:
        language = "bash"
    if language in {"js", "mjs", "cjs", "ts"}:
        language = "javascript"

    specs: dict[str, str] = {
        "bash":
            r"(?P<comment>#[^\n]*)|"
            r"(?P<string>\"(?:[^\"\\\\]|\\\\.)*\"|'(?:[^'\\\\]|\\\\.)*')|"
            r"(?P<keyword>\b(?:if|then|else|fi|for|do|done|case|esac|while|in|function)\b)|"
            r"(?P<builtin>\b(?:cd|echo|printf|export|local|source|read|test)\b)|"
            r"(?P<variable>\$\{?[A-Za-z_][A-Za-z0-9_]*\}?)|"
            r"(?P<number>\b\d+\b)",
        "python":
            r"(?P<comment>#[^\n]*)|"
            r"(?P<string>\"\"\"[\s\S]*?\"\"\"|'''[\s\S]*?'''|\"(?:[^\"\\\\]|\\\\.)*\"|'(?:[^'\\\\]|\\\\.)*')|"
            r"(?P<keyword>\b(?:def|class|return|if|elif|else|for|while|try|except|with|as|import|from|lambda|yield|pass|raise|None|True|False)\b)|"
            r"(?P<builtin>\b(?:print|len|range|list|dict|set|tuple|str|int|float)\b)|"
            r"(?P<number>\b\d+(?:\.\d+)?\b)",
        "rust":
            r"(?P<comment>//[^\n]*)|"
            r"(?P<string>r#?\"(?:[^\"\\\\]|\\\\.)*\"#?|\"(?:[^\"\\\\]|\\\\.)*\"|'(?:[^'\\\\]|\\\\.)*')|"
            r"(?P<keyword>\b(?:fn|let|mut|pub|impl|struct|enum|trait|match|if|else|for|while|loop|return|use|mod|where|async|await|const|static)\b)|"
            r"(?P<builtin>\b(?:Self|self|Some|None|Ok|Err|Result|Option)\b)|"
            r"(?P<number>\b\d+(?:_\d+)*(?:\.\d+)?\b)",
        "javascript":
            r"(?P<comment>//[^\n]*|/\*[\s\S]*?\*/)|"
            r"(?P<string>`(?:[^`\\\\]|\\\\.)*`|\"(?:[^\"\\\\]|\\\\.)*\"|'(?:[^'\\\\]|\\\\.)*')|"
            r"(?P<keyword>\b(?:const|let|var|function|return|if|else|for|while|import|from|export|class|new|async|await|try|catch|throw)\b)|"
            r"(?P<builtin>\b(?:console|window|document|Array|Object|Promise|Map|Set)\b)|"
            r"(?P<number>\b\d+(?:\.\d+)?\b)",
        "json":
            r"(?P<string>\"(?:[^\"\\\\]|\\\\.)*\")|"
            r"(?P<keyword>\b(?:true|false|null)\b)|"
            r"(?P<number>-?\b\d+(?:\.\d+)?\b)",
    }

    spec = specs.get(language)
    if not spec:
        return html.escape(code)

    regex = re.compile(spec, re.MULTILINE)
    out: list[str] = []
    last = 0
    for match in regex.finditer(code):
        start, end = match.span()
        if start > last:
            out.append(html.escape(code[last:start]))
        token_type = match.lastgroup or "text"
        out.append(f'<span class="tok-{token_type}">{html.escape(match.group(0))}</span>')
        last = end
    if last < len(code):
        out.append(html.escape(code[last:]))
    return "".join(out)


def parse_post(path: Path) -> Post:
    raw = path.read_text(encoding="utf-8").splitlines()
    meta: dict[str, str] = {}
    body_start = 0
    for idx, line in enumerate(raw):
        if not line.strip():
            body_start = idx + 1
            break
        if ":" not in line:
            break
        key, value = line.split(":", 1)
        meta[key.strip().lower()] = value.strip()
    body_lines = raw[body_start:]
    title = meta.get("title") or path.stem.replace("-", " ").title()
    slug = meta.get("slug") or slugify(path.stem)
    date = meta.get("date", "")
    summary = meta.get("summary", "")
    if body_lines:
        first = body_lines[0].strip()
        if first == f"# {title}":
            body_lines = body_lines[1:]
            if body_lines and not body_lines[0].strip():
                body_lines = body_lines[1:]
    body_html, toc = render_markdown(body_lines)
    return Post(title, slug, date, summary, path, body_html, toc)


def render_markdown(lines: Iterable[str]) -> tuple[str, list[Heading]]:
    lines = list(lines)
    out: list[str] = []
    toc: list[Heading] = []
    paragraph: list[str] = []
    list_type: str | None = None
    code_lines: list[str] = []
    code_lang = ""
    footnote_defs: dict[str, str] = {}
    footnote_order: list[str] = []
    footnote_numbers: dict[str, int] = {}

    for raw_line in lines:
        footnote_match = re.match(r"^\[\^([^\]]+)\]:\s+(.*)$", raw_line.strip())
        if footnote_match:
            footnote_defs[footnote_match.group(1)] = footnote_match.group(2).strip()

    def flush_paragraph() -> None:
        nonlocal paragraph
        if paragraph:
            text = " ".join(part.strip() for part in paragraph).strip()
            out.append(f"<p>{render_inline(text, footnote_numbers, footnote_order, footnote_defs)}</p>")
            paragraph = []

    def flush_list() -> None:
        nonlocal list_type
        if list_type:
            out.append(f"</{list_type}>")
            list_type = None

    def flush_code() -> None:
        nonlocal code_lines, code_lang
        if code_lines:
            raw_code = "\n".join(code_lines)
            escaped = highlight_code(raw_code, code_lang)
            class_attr = f' class="language-{html.escape(code_lang)}"' if code_lang else ""
            code_attr = html.escape(raw_code, quote=True)
            out.append(
                f'<div class="code-block" data-code="{code_attr}">'
                f'<button class="code-copy" type="button" aria-label="Copy code">⧉</button>'
                f"<pre><code{class_attr}>{escaped}</code></pre>"
                f"</div>"
            )
            code_lines = []
            code_lang = ""

    used_ids: dict[str, int] = {}
    in_code = False

    for raw_line in lines:
        line = raw_line.rstrip("\n")

        if in_code:
            if line.startswith("```"):
                flush_code()
                in_code = False
            else:
                code_lines.append(line)
            continue

        if line.startswith("```"):
            flush_paragraph()
            flush_list()
            in_code = True
            code_lang = line[3:].strip()
            continue

        if not line.strip():
            flush_paragraph()
            flush_list()
            continue

        footnote_match = re.match(r"^\[\^([^\]]+)\]:\s+(.*)$", line)
        if footnote_match:
            flush_paragraph()
            flush_list()
            continue

        heading_match = re.match(r"^(#{1,6})\s+(.*)$", line)
        if heading_match:
            flush_paragraph()
            flush_list()
            level = len(heading_match.group(1))
            text = heading_match.group(2).strip()
            base = slugify(text)
            count = used_ids.get(base, 0)
            used_ids[base] = count + 1
            ident = base if count == 0 else f"{base}-{count+1}"
            anchor = (
                f'<a class="heading-anchor" href="#{ident}" aria-label="Link to {html.escape(text)}">¶</a>'
            )
            out.append(
                f'<h{level} id="{ident}">'
                f"{render_inline(text, footnote_numbers, footnote_order, footnote_defs)}"
                f"{anchor}</h{level}>"
            )
            if level >= 2:
                toc.append(Heading(level, text, ident))
            continue

        ul_match = re.match(r"^-\s+(.*)$", line)
        ol_match = re.match(r"^\d+\.\s+(.*)$", line)
        if ul_match or ol_match:
            flush_paragraph()
            next_type = "ul" if ul_match else "ol"
            if list_type and list_type != next_type:
                flush_list()
            if not list_type:
                list_type = next_type
                out.append(f"<{list_type}>")
            item = ul_match.group(1) if ul_match else ol_match.group(1)
            out.append(f"<li>{render_inline(item.strip(), footnote_numbers, footnote_order, footnote_defs)}</li>")
            continue

        paragraph.append(line)

    flush_paragraph()
    flush_list()
    flush_code()
    if footnote_order:
        note_items = []
        for key in footnote_order:
            text = footnote_defs.get(key, "")
            note_items.append(
                f'<li id="fn-{html.escape(key)}"><p>{render_inline(text, footnote_numbers, footnote_order, footnote_defs)} '
                f'<a class="footnote-backref" href="#fnref-{html.escape(key)}" aria-label="Back to reference">↩</a></p></li>'
            )
        out.append(
            '<section class="footnotes"><p class="footnotes-label">Footnotes</p><ol>'
            + "".join(note_items)
            + "</ol></section>"
        )
    return "\n".join(out), toc


def render_inline(
    text: str,
    footnote_numbers: dict[str, int],
    footnote_order: list[str],
    footnote_defs: dict[str, str],
) -> str:
    escaped = html.escape(text)

    def replace_footnote(match: re.Match[str]) -> str:
        key = match.group(1)
        if key not in footnote_numbers:
            footnote_order.append(key)
            footnote_numbers[key] = len(footnote_order)
        number = footnote_numbers[key]
        if key not in footnote_defs:
            return match.group(0)
        preview = html.escape(footnote_defs[key], quote=True)
        return (
            f'<sup class="footnote-ref" id="fnref-{html.escape(key)}">'
            f'<a href="#fn-{html.escape(key)}" data-footnote-preview="{preview}" '
            f'data-footnote-key="{html.escape(key, quote=True)}" data-footnote-number="{number}">[{number}]</a></sup>'
        )

    escaped = re.sub(r"\[\^([^\]]+)\]", replace_footnote, escaped)
    escaped = re.sub(
        r"!\[([^\]]*)\]\(([^)]+)\)",
        lambda m: (
            f'<img src="{html.escape(m.group(2), quote=True)}" '
            f'alt="{html.escape(m.group(1), quote=True)}" loading="lazy">'
        ),
        escaped,
    )
    escaped = re.sub(r"`([^`]+)`", lambda m: f"<code>{m.group(1)}</code>", escaped)
    escaped = re.sub(
        r"\[([^\]]+)\]\(([^)]+)\)",
        lambda m: f'<a href="{html.escape(m.group(2), quote=True)}">{m.group(1)}</a>',
        escaped,
    )
    escaped = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", escaped)
    escaped = re.sub(r"\*([^*]+)\*", r"<em>\1</em>", escaped)
    return escaped


def page_template(title: str, body: str, *, page_title: str | None = None) -> str:
    full_title = f"{title} | Kumar Kartikeya Dwivedi" if page_title is None else page_title
    return f"""<!DOCTYPE html>
<html>
<head>
\t<!-- Google tag (gtag.js) -->
\t<script async src="https://www.googletagmanager.com/gtag/js?id={ANALYTICS_ID}"></script>
\t<script>
\t  window.dataLayer = window.dataLayer || [];
\t  function gtag(){{dataLayer.push(arguments);}}
\t  gtag('js', new Date());

\t  gtag('config', '{ANALYTICS_ID}');
\t</script>
\t<meta charset="utf-8">
\t<meta name="viewport" content="width=device-width, initial-scale=1">
\t<title>{html.escape(full_title)}</title>
\t<link rel="stylesheet" href="/stylesheets/site.css">
\t<link rel="stylesheet" href="{CSS_PATH}">
</head>
<body>
{body}
<script src="/scripts/site.js"></script>
</body>
</html>
"""


def render_post(post: Post) -> str:
    toc_items = []
    for heading in post.toc:
        indent = f" toc-depth-{heading.level}" if heading.level >= 3 else ""
        toc_items.append(
            f'<li class="toc-item{indent}"><a href="#{heading.ident}">{html.escape(heading.text)}</a></li>'
        )
    toc_html = "\n".join(toc_items) if toc_items else '<li class="toc-item"><span>No sections yet</span></li>'
    date_html = f'<p class="post-date">{html.escape(post.date)}</p>' if post.date else ""
    content = f"""<div class="blog-shell toc-collapsed">
\t<button class="mobile-toc-toggle" type="button" aria-label="Open table of contents" aria-expanded="false" aria-controls="mobile-toc-overlay"></button>
\t<div class="mobile-toc-overlay" id="mobile-toc-overlay" hidden>
\t\t<div class="mobile-toc-panel">
\t\t\t<div class="mobile-toc-header">
\t\t\t\t<p class="sidebar-label">Table of Contents</p>
\t\t\t\t<button class="mobile-toc-close" type="button" aria-label="Close contents">×</button>
\t\t\t</div>
\t\t\t<ol class="toc">
{toc_html}
\t\t\t</ol>
\t\t</div>
\t</div>
\t<button class="desktop-toc-toggle" type="button" aria-label="Show table of contents" aria-expanded="false"></button>
\t<aside class="blog-sidebar">
\t\t<div class="sidebar-inner">
\t\t\t<div class="sidebar-head">
\t\t\t\t<p class="sidebar-label">Table of Contents</p>
\t\t\t\t<button class="sidebar-collapse" type="button" aria-label="Hide table of contents">×</button>
\t\t\t</div>
\t\t\t<ol class="toc">
{toc_html}
\t\t\t</ol>
\t\t</div>
\t</aside>
\t<main class="blog-main">
\t\t<header class="post-header">
\t\t\t<p class="back-link"><a href="/">Home</a> <span>/</span> <a href="/blog/">Blog</a></p>
\t\t\t<h1>{html.escape(post.title)}</h1>
\t\t\t{date_html}
\t\t</header>
\t\t<article class="post-body">
{post.body_html}
\t\t</article>
\t\t<p class="post-footer-nav"><a href="/">Home</a> <span>/</span> <a href="/blog/">Blog</a></p>
\t</main>
</div>
<script>
const tocLinks = Array.from(document.querySelectorAll('.toc a'));
const smoothHashLinks = Array.from(document.querySelectorAll('.heading-anchor, .footnote-ref a, .footnote-backref'));
const footnoteLinks = Array.from(document.querySelectorAll('.footnote-ref a'));
const codeCopyButtons = Array.from(document.querySelectorAll('.code-copy'));
const mobileToggle = document.querySelector('.mobile-toc-toggle');
const mobileOverlay = document.querySelector('.mobile-toc-overlay');
const mobileClose = document.querySelector('.mobile-toc-close');
const desktopToggle = document.querySelector('.desktop-toc-toggle');
const sidebarCollapse = document.querySelector('.sidebar-collapse');
const sidebarInner = document.querySelector('.sidebar-inner');
const blogShell = document.querySelector('.blog-shell');
const blogMain = document.querySelector('.blog-main');
const headings = tocLinks
  .map((link) => document.getElementById(link.getAttribute('href').slice(1)))
  .filter(Boolean);

const setOverlayOpen = (open) => {{
  if (!mobileToggle || !mobileOverlay) return;
  mobileToggle.setAttribute('aria-expanded', open ? 'true' : 'false');
  mobileOverlay.hidden = !open;
  mobileOverlay.classList.toggle('open', open);
}};

const footnotePopupOverlay = document.createElement('div');
footnotePopupOverlay.className = 'footnote-popup-overlay';
footnotePopupOverlay.hidden = true;
const footnotePopup = document.createElement('div');
footnotePopup.className = 'footnote-popup';
footnotePopup.hidden = true;
footnotePopup.innerHTML = '<div class="footnote-popup-body"></div>';
document.body.appendChild(footnotePopupOverlay);
document.body.appendChild(footnotePopup);

const closeFootnotePopup = () => {{
  footnotePopupOverlay.hidden = true;
  footnotePopupOverlay.classList.remove('open');
  footnotePopup.hidden = true;
  footnotePopup.classList.remove('open');
  footnotePopup.style.removeProperty('left');
  footnotePopup.style.removeProperty('top');
}};

const openFootnotePopup = (link) => {{
  const preview = link.getAttribute('data-footnote-preview') || '';
  const key = link.getAttribute('data-footnote-key') || '';
  const number = link.getAttribute('data-footnote-number') || '';
  footnotePopup.querySelector('.footnote-popup-body').innerHTML =
    preview + ' <a class="footnote-popup-link" href="#fn-' + key + '" aria-label="Jump to note [' + number + ']">↪</a>';
  if (window.innerWidth > 900) {{
    const rect = link.getBoundingClientRect();
    footnotePopup.style.left = Math.min(rect.left + window.scrollX, window.scrollX + window.innerWidth - 320) + 'px';
    footnotePopup.style.top = rect.bottom + window.scrollY + 10 + 'px';
  }}
  footnotePopupOverlay.hidden = false;
  requestAnimationFrame(() => footnotePopupOverlay.classList.add('open'));
  footnotePopup.hidden = false;
  requestAnimationFrame(() => footnotePopup.classList.add('open'));
}};

for (const button of codeCopyButtons) {{
  const defaultLabel = '⧉';
  button.textContent = defaultLabel;
  button.addEventListener('click', async () => {{
    const block = button.closest('.code-block');
    const code = block?.dataset.code || '';
    if (!code) return;
    try {{
      await navigator.clipboard.writeText(code);
      button.classList.add('copied');
      window.setTimeout(() => {{
        button.classList.remove('copied');
      }}, 1600);
    }} catch (_error) {{
      button.textContent = '!';
      window.setTimeout(() => {{
        button.textContent = defaultLabel;
      }}, 1600);
    }}
  }});
}}

if (mobileToggle && mobileOverlay && mobileClose) {{
  const syncToggleVisibility = () => {{
    mobileToggle.classList.toggle('visible', window.scrollY > 80);
  }};
  mobileToggle.addEventListener('click', () => setOverlayOpen(true));
  mobileClose.addEventListener('click', () => setOverlayOpen(false));
  mobileOverlay.addEventListener('click', (event) => {{
    if (event.target === mobileOverlay) setOverlayOpen(false);
  }});
  document.addEventListener('scroll', syncToggleVisibility, {{ passive: true }});
  window.addEventListener('load', syncToggleVisibility);
  syncToggleVisibility();
}}

const setDesktopTocCollapsed = (collapsed) => {{
  if (!blogShell || !desktopToggle) return;
  blogShell.classList.toggle('toc-collapsed', collapsed);
  desktopToggle.setAttribute('aria-expanded', collapsed ? 'false' : 'true');
}};

if (desktopToggle && sidebarCollapse && blogShell && sidebarInner && blogMain) {{
  let sidebarControlsTimer = 0;
  let desktopToggleTimer = 0;
  const showSidebarControls = () => {{
    window.clearTimeout(sidebarControlsTimer);
    sidebarInner.classList.add('controls-visible');
  }};
  const hideSidebarControlsSoon = () => {{
    window.clearTimeout(sidebarControlsTimer);
    sidebarControlsTimer = window.setTimeout(() => {{
      sidebarInner.classList.remove('controls-visible');
    }}, 1800);
  }};
  const showDesktopToggle = () => {{
    window.clearTimeout(desktopToggleTimer);
    desktopToggle.classList.add('visible');
  }};
  const hideDesktopToggleSoon = () => {{
    window.clearTimeout(desktopToggleTimer);
    desktopToggleTimer = window.setTimeout(() => {{
      desktopToggle.classList.remove('visible');
    }}, 1800);
  }};
  const syncDesktopToggleVisibility = () => {{
    if (!blogShell.classList.contains('toc-collapsed')) {{
      desktopToggle.classList.remove('visible');
      return;
    }}
    showDesktopToggle();
    hideDesktopToggleSoon();
  }};
  const syncDesktopToggleHotzone = (event) => {{
    if (!blogShell.classList.contains('toc-collapsed')) return;
    const articleRect = blogMain.getBoundingClientRect();
    if (event.clientX <= articleRect.left) {{
      showDesktopToggle();
      hideDesktopToggleSoon();
    }} else if (!desktopToggle.matches(':hover, :focus-visible')) {{
      hideDesktopToggleSoon();
    }}
  }};
  const hideDesktopToggleOnScroll = () => {{
    if (!blogShell.classList.contains('toc-collapsed')) return;
    if (desktopToggle.matches(':hover, :focus-visible')) return;
    window.clearTimeout(desktopToggleTimer);
    desktopToggle.classList.remove('visible');
  }};

  desktopToggle.addEventListener('click', () => setDesktopTocCollapsed(false));
  desktopToggle.addEventListener('mouseenter', showDesktopToggle);
  desktopToggle.addEventListener('mouseleave', hideDesktopToggleSoon);
  desktopToggle.addEventListener('focusin', showDesktopToggle);
  desktopToggle.addEventListener('focusout', hideDesktopToggleSoon);
  sidebarCollapse.addEventListener('click', () => {{
    setDesktopTocCollapsed(true);
    syncDesktopToggleVisibility();
  }});
  sidebarInner.addEventListener('mouseenter', showSidebarControls);
  sidebarInner.addEventListener('mousemove', showSidebarControls);
  sidebarInner.addEventListener('mouseleave', hideSidebarControlsSoon);
  sidebarInner.addEventListener('focusin', showSidebarControls);
  sidebarInner.addEventListener('focusout', () => {{
    window.setTimeout(() => {{
      if (!sidebarInner.contains(document.activeElement)) hideSidebarControlsSoon();
    }}, 0);
  }});
  showSidebarControls();
  hideSidebarControlsSoon();
  document.addEventListener('scroll', hideDesktopToggleOnScroll, {{ passive: true }});
  document.addEventListener('mousemove', syncDesktopToggleHotzone, {{ passive: true }});
}}

if (tocLinks.length && headings.length) {{
  let pinnedId = "";
  let ignoreScrollUntil = 0;
  const revealTocLink = (link) => {{
    const container = link.closest('.sidebar-inner, .mobile-toc-panel');
    if (!container) return;
    const buffer = 56;
    const containerRect = container.getBoundingClientRect();
    const linkRect = link.getBoundingClientRect();
    const linkTop = linkRect.top - containerRect.top + container.scrollTop;
    const linkBottom = linkTop + linkRect.height;
    const visibleTop = container.scrollTop + buffer;
    const visibleBottom = container.scrollTop + container.clientHeight - buffer;
    if (linkTop < visibleTop) {{
      container.scrollTo({{
        top: Math.max(0, linkTop - buffer),
        behavior: 'smooth',
      }});
    }} else if (linkBottom > visibleBottom) {{
      container.scrollTo({{
        top: Math.min(container.scrollHeight - container.clientHeight, linkBottom - container.clientHeight + buffer),
        behavior: 'smooth',
      }});
    }}
  }};
  const navigateToId = (id, options = {{}}) => {{
    const target = document.getElementById(id);
    if (!target) return;
    if (options.pinToc) {{
      pinnedId = id;
      ignoreScrollUntil = Date.now() + 400;
      setActive(id);
    }}
    history.replaceState(null, '', '#' + id);
    target.scrollIntoView({{ block: 'start', behavior: 'smooth' }});
  }};
  const setActive = (id) => {{
    for (const link of tocLinks) {{
      const active = link.getAttribute('href') === '#' + id;
      link.classList.toggle('active', active);
      if (active) {{
        revealTocLink(link);
      }}
    }}
  }};

  const syncActive = () => {{
    if (Date.now() < ignoreScrollUntil && pinnedId) {{
      setActive(pinnedId);
      return;
    }}
    const hashId = decodeURIComponent(window.location.hash.slice(1));
    if (hashId) {{
      pinnedId = hashId;
      const hashHeading = document.getElementById(hashId);
      if (hashHeading) {{
        const rect = hashHeading.getBoundingClientRect();
        if (rect.top <= window.innerHeight * 0.6 && rect.bottom >= 80) {{
          setActive(hashHeading.id);
          return;
        }}
      }}
    }}
    let current = headings[0];
    for (const heading of headings) {{
      if (heading.getBoundingClientRect().top <= 120) current = heading;
    }}
    setActive(current.id);
  }};
  for (const link of tocLinks) {{
    link.addEventListener('click', (event) => {{
      event.preventDefault();
      const id = link.getAttribute('href').slice(1);
      setOverlayOpen(false);
      navigateToId(id, {{ pinToc: true }});
    }});
  }}
  for (const link of smoothHashLinks) {{
    link.addEventListener('click', (event) => {{
      const href = link.getAttribute('href') || '';
      if (!href.startsWith('#')) return;
      if (link.closest('.footnote-ref')) return;
      const id = href.slice(1);
      if (!id) return;
      event.preventDefault();
      navigateToId(id);
    }});
  }}
  for (const link of footnoteLinks) {{
    link.addEventListener('click', (event) => {{
      event.preventDefault();
      if (!footnotePopup.hidden && footnotePopup.dataset.anchor === link.getAttribute('href')) {{
        closeFootnotePopup();
        return;
      }}
      footnotePopup.dataset.anchor = link.getAttribute('href') || '';
      openFootnotePopup(link);
    }});
  }}
  footnotePopup.addEventListener('click', (event) => {{
    const jump = event.target.closest('.footnote-popup-link');
    if (!jump) return;
    const href = jump.getAttribute('href') || '';
    if (!href.startsWith('#')) return;
    event.preventDefault();
    closeFootnotePopup();
    navigateToId(href.slice(1));
  }});
  document.addEventListener('click', (event) => {{
    if (footnotePopup.hidden) return;
    if (footnotePopup.contains(event.target)) return;
    if (event.target.closest('.footnote-ref')) return;
    closeFootnotePopup();
  }});
  footnotePopupOverlay.addEventListener('click', closeFootnotePopup);
  window.addEventListener('resize', closeFootnotePopup);
  window.addEventListener('hashchange', closeFootnotePopup);
  document.addEventListener('scroll', syncActive, {{ passive: true }});
  window.addEventListener('hashchange', syncActive);
  window.addEventListener('load', syncActive);
  syncActive();
}}
</script>
"""
    return page_template(post.title, content)


def render_index(posts: list[Post]) -> str:
    items = []
    for post in posts:
        date = f'<p class="post-card-date">{html.escape(post.date)}</p>' if post.date else ""
        items.append(
            f"""<li class="post-card">
\t<h2><a href="/blog/{post.slug}/">{html.escape(post.title)}</a></h2>
\t{date}
\t<p>{html.escape(post.summary)}</p>
</li>"""
        )
    content = f"""<main class="blog-index">
\t<header class="index-header">
\t\t<p class="back-link"><a href="/">Home</a></p>
\t\t<h1>Blog</h1>
\t\t<p class="index-summary">Notes and essays written in markdown and rendered into the site.</p>
\t</header>
\t<ul class="post-list">
{chr(10).join(items)}
\t</ul>
</main>
"""
    return page_template("Blog", content, page_title="Blog | Kumar Kartikeya Dwivedi")


def main() -> None:
    posts = sorted((parse_post(path) for path in SRC_DIR.glob("*.md")), key=lambda post: post.date, reverse=True)
    OUT_DIR.mkdir(exist_ok=True)
    (OUT_DIR / "index.html").write_text(render_index(posts), encoding="utf-8")
    for post in posts:
        post_dir = OUT_DIR / post.slug
        post_dir.mkdir(parents=True, exist_ok=True)
        (post_dir / "index.html").write_text(render_post(post), encoding="utf-8")


if __name__ == "__main__":
    main()
