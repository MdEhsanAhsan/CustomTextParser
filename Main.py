class CharReader:
    def __init__(self, file):
        self.file = file
        self.lookahead = None

    def read(self):
        """Reads the next character from the file."""
        if self.lookahead is not None:
            char = self.lookahead
            self.lookahead = None
            return char
        return self.file.read(1)

    def peek(self):
        """Peeks at the next character without consuming it."""
        if self.lookahead is None:
            self.lookahead = self.file.read(1)
        return self.lookahead
    
#Global constants for the DAT file format
# These constants are used to identify the structure of the DAT file.

QUOTE_CHAR = '\xfe' # Quote character used to enclose fields.
FIELD_SEP = '\x14' # Data Control 4 (DC4) character, used as field separator.

def read_dat_file_smart(file_path):
    """
    Reads a DAT file smartly, ignoring newlines that occur inside quoted fields.
    Yields complete logical lines.
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        reader = CharReader(f)
        buffer = ''
        in_quote = True  # Start in quoted state

        while True:
            char = reader.read()
            next_char = reader.peek()
            if not char:
                # End of file
                if buffer:
                    yield buffer.strip('\r\n')
                break

            if char == QUOTE_CHAR and next_char == FIELD_SEP:
                # Toggle quote state
                in_quote = not in_quote
                buffer += char

            elif char == FIELD_SEP:
                if in_quote:
                    # Inside quoted field → keep DC4
                    buffer += char
                else:
                    # Outside quoted field → end of field
                    buffer += char

            elif char == '\n':
                if in_quote:
                    # Inside quoted field → keep newline
                    buffer += char
                else:
                    # Real end of line → yield it
                    yield buffer.strip('\r\n')
                    buffer = ''

            else:
                buffer += char



# Example usage
if __name__ == '__main__':
    file_path = r"C:\Users\ehsan\OneDrive\Desktop\DAT\Test2.dat"

    for i, line in enumerate(read_dat_file_smart(file_path)):
        print(f"Parsed line {i}:", line)