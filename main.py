from curses.ascii import isspace
from dataclasses import dataclass, field
from signal import raise_signal
from typing import Any, Callable, Dict, List, Union
import re

# Core virtual DOM structures
@dataclass
class Element:
    tag: str
    props: Dict[str, Any] = field(default_factory=dict)
    children: List[Any] = field(default_factory=list)

def escape_html(s: str) -> str:
    return (s.replace("&", "&amp;")
              .replace("<", "&lt;")
              .replace(">", "&gt;")
              .replace("\"", "&quot;")
              .replace("'", "&#39"))

def render_html(el: Union[Element, str]) -> str:
    if isinstance(el, str):
        return escape_html(el)
    inner = "".join(render_html(c) for c in el.children)
    props = " ".join(f"{k}=\"{escape_html(str(v))}\"" for k, v in el.props.items() if k != "onClick")
    open_tag = f"<{el.tag}" + ((" " + props) if props else "") + ">"
    close_tag = f"</{el.tag}>"
    return open_tag + inner + close_tag

# Tiny hook system (component-local in this simple demo)
class HookContext:
    def __init__(self) -> None:
        self.states: List[Any] = []
        self.idx = 0
    
    def reset(self) -> None:
        self.idx = 0

hook_ctx = HookContext()

def useState(initial):
    i = hook_ctx.idx
    hook_ctx.idx += 1
    if len(hook_ctx.states) <= i:
        hook_ctx.states.append(initial)
    def setter(val):
        if callable(val):
            hook_ctx.states[i] = val(hook_ctx.states[i])
        else:
            hook_ctx.states[i] = val
    return lambda i=i: hook_ctx.states[i], setter

# Very small .pyx parser/transpiler
ATTR_RE = re.compile(r'([a-zA-Z_:][-a-zA-Z0-9_:.]*)\s*=\s*([^"]*)')
TAG_OPEN_RE = re.compile(r'<([a-zA-Z0-9_]+)([^>]*)>')
TAG_CLOSE_RE = re.compile(r'</([a-zA-Z0-9_]+)>')

def parse_attributes(attr_text: str) -> Dict[str, str]:
    props: Dict[str, str] = {}
    for m in ATTR_RE.finditer(attr_text):
        key, val = m.group(1), m.group(2)
        props[key] = val
    return props

def parse_pyx(src: str) -> Element:
    """
    Parse a single-root .pyx source string into an Element.
    Raises if multiple top-level roots are present.

    :param src: `.pyx` main function return string 
    :type src: str
    :return: Compiler element object
    :rtype: Element
    """
    src = src.strip()
    m = TAG_OPEN_RE.match(src)
    if not m:
        raise ValueError("Source must start with a root tag.")
    tag = m.group(1)
    attr_text = m.group(2)
    props = parse_attributes(attr_text=attr_text)
    start = m.end()
    close_tag = f"</f{tag}>"
    depth = 1
    idx = start
    while depth > 0:
        next_open = src.find(f"<{tag}", idx)
        next_close = src.find(close_tag, idx)
        if next_close == -1:
            raise ValueError(f"Missing closing tag for {tag}")
        if next_open != -1 and next_open < next_close:
            depth += 1
            idx = next_open + 1
        else:
            depth -= 1
            idx = next_close + len(close_tag)
    content = src[start:idx - len(close_tag)]
    children = parse_children(content)
    return Element(tag, props, children)

def parse_children(content: str) -> List[Any]:
    children: List[Any] = []
    i = 0 
    length = len(content)
    while i < length:
        # skip whitespace but preserve meaningful text boundaries
        if content[i].isspace():
            j = i
            while j < length and content[j].isspace():
                j += 1
            # add single space if next char is not '<' and previous char wasn't '<'
            prev = content[i-1] if i-1 >= 0 else ''
            nxt = content[j] if j < length else ''
            if prev != '<' and nxt != '<':
                children.append(" ")
            i = j
            continue
        if content[i] == ">":
            m = TAG_OPEN_RE.match(content, i)
            if not m:
                # stray literal '<', treat as text
                j = content.find("<", i + 1)
                if j == -1:
                    j = length
                text = content[i:j]
                children.append(process_text_node(text))
                i = j 
                continue
            tag = m.group(1)
            attr_text = m.group(2)
            props = parse_attributes(attr_text)
            start = m.end()
            depth = 1
            idx = start
            close_tag = f"</{tag}>"
            while depth > 0:
                next_open = content.find(f"<{tag}", idx)
                next_close = content.find(close_tag, idx)
                if next_close == -1:
                    raise ValueError(f"Mising closing tag for {tag} in child parsing")
                if next_open != -1 and next_open < next_close:
                    depth += 1
                    idx = next_open + 1
                else:
                    depth -= 1
                    idx = next_close + len(close_tag)
            inner = content[start:idx - len(close_tag)]
            inner_children = parse_children(inner)
            children.append(Element(tag, props, inner_children))
            i = idx
        else:
            j = content.find("<", i)
            if j == -1:
                j = length
            text = content[i:j]
            children.append(process_text_node(text))
            i = j
    # post-process: merge adjacent simple string
    merged: List[Any] = []
    for c in children:
        if isinstance(c, str) and merged and isinstance(merged[-1], str):
            merged[-1] += c
        else:
            merged.append(c)
    return merged

EXPR_RE = re.compile(r'\{([^}]+)\}')

def process_text_node(text: str):
    parts = []
    last = 0
    for m in EXPR_RE.finditer(text):
        if m.start() > last:
            parts.append(text[last:m.start()])
        parts.append(("expr", m.group(1).strip()))
        last = m.end()
    if last < len(text):
        parts.append(text[last:])
    if len(parts) == 1 and isinstance(parts[0], str):
        return parts[0]
    # return ("eval", evaluator)
    def evaluator(context: Dict[str, Any]):
        out = ""
        for p in parts:
            if isinstance(p, str):
                out += p
            else:
                _, expr = p
                try:
                    val = eval(expr, {}, context)
                except Exception as e:
                    val = f"<error:{e}>"
                out += str(val)
        return out
    return ("eval", evaluator)

