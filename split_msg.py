import sys
from msg_split import split_message


def main():
    # Пример вызова: python split_msg.py --max-len=4396 ./source.html
    args = sys.argv[1:]
    max_len = 4096
    input_file = None
    for arg in args:
        if arg.startswith('--max-len='):
            max_len = int(arg.split('=', 1)[1])
        else:
            input_file = arg

    if not input_file:
        print("Usage: python split_msg.py [--max-len=SIZE] input.html", file=sys.stderr)
        sys.exit(1)

    with open(input_file, 'r', encoding='utf-8') as f:
        source = f.read()

    fragments = list(split_message(source, max_len=max_len))

    for i, frag in enumerate(fragments, start=1):
        print(f"fragment #{i}: {len(frag)} chars")
        print(frag)


if __name__ == "__main__":
    main()
