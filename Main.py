class CharReader:
    def __init__(self, file):
        self.file = file
        self.lookahead = None

    def read(self):
        if self.lookahead is not None:
            char = self.lookahead
            self.lookahead = None
            return char
        return self.file.read(1)

    def peek(self):
        if self.lookahead is None:
            self.lookahead = self.file.read(1)
        return self.lookahead


def read_dat_file_smart(file_path):
    """
    Reads a DAT file smartly, ignoring newlines that occur inside quoted fields.
    Yields complete logical lines.
    """
    QUOTE_CHAR = '\xfe'
    FIELD_SEP = '\x14'
    in_quote = True

    with open(file_path, 'r', encoding='utf-8') as f:
        buffer = ''
        reader = CharReader(f)
        while True:
            char = reader.read()
            if not char:
                # End of file
                if buffer:
                    yield buffer.strip('\r\n')
                break

            if char == QUOTE_CHAR:
                # Peek next character
                next_char = reader.peek()
                if in_quote:
                    if next_char == FIELD_SEP :#or next_char == '\n' or next_char == '\r':
                        # Likely end of quoted field
                        in_quote = False
                    buffer += char
            elif char == FIELD_SEP:
                if in_quote:
                    buffer += char
                else:
                    buffer += char

            elif char == '\n':
                if in_quote:
                    buffer += char
                else:
                    yield buffer.strip('\r\n')
                    buffer = ''

            else:
                buffer += char


# Example usage
if __name__ == '__main__':
    file_path = r"C:\Users\ehsan\OneDrive\Desktop\DAT\Test2.dat"

    for i, line in enumerate(read_dat_file_smart(file_path)):
        print(f"Parsed line {i}:", line)