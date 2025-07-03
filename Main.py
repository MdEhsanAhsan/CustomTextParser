def read_dat_file_smart(file_path):
    """
    Reads a DAT file smartly, ignoring newlines that occur inside quoted fields.
    Yields complete logical lines.
    """
    QUOTE_CHAR = '\xfe'
    in_quote = False

    with open(file_path, 'r', encoding='utf-8') as f:
        buffer = ''
        while True:
            char = f.read(1)
            if not char:
                # End of file
                if buffer:
                    yield buffer.strip('\r\n')
                break

            if char == QUOTE_CHAR:
                in_quote = not in_quote
                buffer += char

            elif char == '\n':
                # Check if inside quote
                if in_quote:
                    # Embedded newline inside quoted field → keep going
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