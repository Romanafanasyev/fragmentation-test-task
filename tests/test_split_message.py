import re
import unittest
from bs4 import BeautifulSoup
from msg_split import split_message


class TestSplitMessage(unittest.TestCase):
    def _assert_fragments(self, fragments, max_len):
        tag_pattern = re.compile(r"<(/)?([a-zA-Z0-9]+)([^>]*)>")

        for frag in fragments:
            # Проверка длины
            self.assertLessEqual(len(frag), max_len, "Фрагмент превышает max_len")

            # Проверка парсинга BeautifulSoup (проверка, что HTML в целом разборчив)
            soup = BeautifulSoup(frag, 'html.parser')

            # Ручная проверка корректности вложенности тегов
            stack = []
            for match in tag_pattern.finditer(frag):
                is_closing = (match.group(1) == '/')
                tag_name = match.group(2).lower()
                full_tag_str = match.group(0)
                attrs_str = match.group(3)

                is_self_closing = False
                if attrs_str is not None:
                    is_self_closing = attrs_str.strip().endswith('/')

                if is_closing:
                    if not stack:
                        self.fail(f"Закрывающий тег </{tag_name}> без соответствующего открывающего в фрагменте:\n{frag}")
                    opened = stack.pop()
                    if opened != tag_name:
                        self.fail(f"Несовпадающие теги: ожидался </{opened}>, а встречен </{tag_name}> в фрагменте:\n{frag}")
                else:
                    if not is_self_closing:
                        stack.append(tag_name)

            if stack:
                self.fail(f"Не все теги закрыты в фрагменте: остались открытыми {stack}.\nФрагмент:\n{frag}")

    def test_empty_html(self):
        source = ""
        max_len = 100
        fragments = list(split_message(source, max_len))
        self.assertEqual(len(fragments), 0)

    def test_small_html_fits_in_one_fragment(self):
        source = "<p>Hello</p>"
        max_len = 100
        fragments = list(split_message(source, max_len))
        self.assertEqual(len(fragments), 1)
        self._assert_fragments(fragments, max_len)

    def test_text_only_short(self):
        source = "Hello world"
        max_len = 20
        fragments = list(split_message(source, max_len))
        self.assertEqual(len(fragments), 1)
        self.assertEqual(fragments[0], "Hello world")
        self._assert_fragments(fragments, max_len)

    def test_text_only_too_long(self):
        source = "a" * 5000
        max_len = 4096
        fragments = list(split_message(source, max_len))

        self.assertEqual(len(fragments), 2)
        self._assert_fragments(fragments, max_len)

    def test_single_breakable_tag_too_large(self):
        source = "<p>" + ("a" * 5000) + "</p>"
        max_len = 4096
        fragments = list(split_message(source, max_len))

        self.assertEqual(len(fragments), 2)
        self._assert_fragments(fragments, max_len)

    def test_unbreakable_tag_too_large(self):
        source = "<a>" + ("a" * 5000) + "</a>"
        max_len = 4096
        with self.assertRaises(ValueError):
            list(split_message(source, max_len))

    def test_break_at_allowed_tag(self):
        source = "<p>" + ("a" * 3000) + " " + ("b" * 3000) + "</p>"
        max_len = 4096
        fragments = list(split_message(source, max_len))
        self.assertGreater(len(fragments), 1)
        self._assert_fragments(fragments, max_len)

        alltext = "".join(fragments)
        soup = BeautifulSoup(alltext, 'html.parser')
        text = soup.get_text()
        self.assertIn("a" * 3000, text)
        self.assertIn("b" * 3000, text)

    def test_break_with_nested_tags(self):
        part1 = "a" * 2000
        part2 = "b" * 3000
        source = f"<div><p>{part1}</p><p>{part2}</p></div>"
        max_len = 4096
        fragments = list(split_message(source, max_len))
        self.assertGreaterEqual(len(fragments), 2, "Ожидается как минимум два фрагмента")
        self._assert_fragments(fragments, max_len)

        combined = "".join(fragments)
        soup = BeautifulSoup(combined, 'html.parser')
        text = soup.get_text()
        self.assertIn(part1, text)
        self.assertIn(part2, text)

    def test_closing_tag_not_fitting_at_fragment_end(self):
        text_len = 45
        text_content = "a" * text_len
        source = f"<p>{text_content}</p>"
        max_len = 50
        fragments = list(split_message(source, max_len))

        self.assertTrue(len(fragments) >= 1)
        self._assert_fragments(fragments, max_len)

        combined = "".join(fragments)
        soup = BeautifulSoup(combined, 'html.parser')
        self.assertEqual(soup.get_text(), text_content)

    def test_unbreakable_tag_fits_in_new_fragment(self):
        text_content = "a" * 40
        source = f"<p>{text_content}</p><a>short</a>"
        max_len = 50
        fragments = list(split_message(source, max_len))
        self.assertEqual(len(fragments), 2, "Ожидаются два фрагмента")
        self._assert_fragments(fragments, max_len)

    def test_many_small_breakable_tags(self):
        single_span_text = "x" * 10
        spans_count = 20
        source = "".join([f"<span>{single_span_text}</span>" for _ in range(spans_count)])
        max_len = 50
        fragments = list(split_message(source, max_len))
        self._assert_fragments(fragments, max_len)

        combined = "".join(fragments)
        soup = BeautifulSoup(combined, 'html.parser')
        total_text = soup.get_text()
        self.assertEqual(total_text.count("x"), spans_count * 10)

    def test_mixed_break_at_breakable(self):
        part1 = "a" * 3000
        part2 = "b" * 500
        source = f"<div><p>{part1}</p><a>{part2}</a></div>"
        max_len = 2000

        fragments = list(split_message(source, max_len))
        self.assertTrue(len(fragments) >= 1)
        self._assert_fragments(fragments, max_len)

    def test_mixed_break_at_unbreakable(self):
        part1 = "a" * 500
        part2 = "b" * 3000
        source = f"<div><p>{part1}</p><a>{part2}</a></div>"
        max_len = 2000

        with self.assertRaises(ValueError):
            list(split_message(source, max_len))


if __name__ == '__main__':
    unittest.main()
