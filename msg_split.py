from typing import Generator
from bs4 import BeautifulSoup, NavigableString, Tag

MAX_LEN = 4096
BLOCK_TAGS = {'p', 'b', 'strong', 'i', 'ul', 'ol', 'div', 'span'}


def split_message(source: str, max_len=MAX_LEN) -> Generator[str, None, None]:
    soup = BeautifulSoup(source, 'html.parser')

    def closing_tags(stack):
        tags = "".join("</{}>".format(t) for t in reversed(stack))
        return tags

    def opening_tags(stack):
        tags = "".join("<{}>".format(t) for t in stack)
        return tags

    current_fragment = ""
    current_length = 0
    open_stack = []

    def can_fit(content_len):
        c = content_len + len(closing_tags(open_stack))
        fit = (current_length + c <= max_len)
        return fit

    def flush_fragment():
        nonlocal current_fragment, current_length
        if current_length > 0:
            yield_fragment = current_fragment + closing_tags(open_stack)
            yield yield_fragment
        current_fragment = opening_tags(open_stack)
        current_length = len(current_fragment)

    def add_content(content):
        nonlocal current_fragment, current_length
        if can_fit(len(content)):
            current_fragment += content
            current_length += len(content)
        else:
            if len(content) > max_len:
                if isinstance(content, str):
                    pos = 0
                    while pos < len(content):
                        space = max_len - current_length - len(closing_tags(open_stack))
                        if space <= 0:
                            for f in flush_fragment():
                                yield f
                            continue
                        chunk = content[pos:pos+space]
                        pos += len(chunk)
                        current_fragment += chunk
                        current_length += len(chunk)
                        if pos < len(content):
                            for f in flush_fragment():
                                yield f
                else:
                    raise ValueError("Cannot fit content even in an empty fragment.")
            else:
                for f in flush_fragment():
                    yield f
                if not can_fit(len(content)):
                    raise ValueError("Cannot fit content in a new fragment.")
                current_fragment += content
                current_length += len(content)

    def process_node(node):
        if isinstance(node, NavigableString):
            text = str(node)
            pos = 0
            while pos < len(text):
                space = max_len - current_length - len(closing_tags(open_stack))
                if space <= len(closing_tags(open_stack)):
                    for f in flush_fragment():
                        yield f
                    continue
                chunk = text[pos:pos+space]
                pos += len(chunk)
                current_fragment_list = list(add_content(chunk))
                for f in current_fragment_list:
                    yield f
        elif isinstance(node, Tag):
            name = node.name.lower()
            inner = "".join(str(e) for e in node.children)
            if name in BLOCK_TAGS:
                open_tag = "<{}>".format(name)
                close_tag = "</{}>".format(name)
                if not can_fit(len(open_tag)):
                    for f in flush_fragment():
                        yield f
                    if not can_fit(len(open_tag)):
                        raise ValueError("Cannot fit block tag in empty fragment.")
                current_fragment_list = list(add_content(open_tag))
                for f in current_fragment_list:
                    yield f
                open_stack.append(name)
                for child in node.children:
                    for f in process_node(child):
                        yield f
                if not can_fit(len(close_tag)):
                    for f in flush_fragment():
                        yield f
                current_fragment_list = list(add_content(close_tag))
                for f in current_fragment_list:
                    yield f
                open_stack.pop()
            else:
                full_tag = str(node)
                if not can_fit(len(full_tag)):
                    for f in flush_fragment():
                        yield f
                    if not can_fit(len(full_tag)):
                        raise ValueError("Cannot fit non-block tag in empty fragment.")
                current_fragment_list = list(add_content(full_tag))
                for f in current_fragment_list:
                    yield f

    for element in soup.contents:
        for fragment in process_node(element):
            yield fragment
    if current_length > 0:
        final_fragment = current_fragment + closing_tags(open_stack)
        yield final_fragment
