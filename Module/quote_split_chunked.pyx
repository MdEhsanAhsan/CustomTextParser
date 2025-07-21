# quote_split_chunked.pyx
# | Character | ASCII | Python Char |
# | --------- | ----- | ----------- |
# | `\r`      | 13    | `0x0D`      |
# | `\n`      | 10    | `0x0A`      |

cdef class QuoteLineSplitter:
    cdef str quote_char
    cdef str field_sep
    cdef str leftover
    cdef bint in_quote

    def __cinit__(self, str quote_char=u'\xfe', str field_sep=u'\x14'):
        self.quote_char = quote_char
        self.field_sep = field_sep
        self.leftover = ""
        self.in_quote = False

    def feed_chunk(self, str chunk):
        """
        Process a chunk and return a list of complete logical lines.
        Remaining content (partial line) is saved in self.leftover.
        """
        cdef str buffer = self.leftover + chunk
        cdef Py_ssize_t i = 0
        cdef Py_ssize_t line_start = 0
        cdef Py_ssize_t n = len(buffer)
        cdef list lines = []

        cdef Py_UCS4 c, next1, next2, qchar
        qchar = ord(self.quote_char)
        cdef Py_UCS4 fsep = ord(self.field_sep)

        while i < n:
            c = ord(buffer[i])
            next1 = ord(buffer[i+1]) if i+1 < n else 0
            next2 = ord(buffer[i+2]) if i+2 < n else 0

            if c == qchar and not self.in_quote:
                self.in_quote = True

            elif c == qchar and self.in_quote and (
                (next1 == fsep and next2 == qchar) or
                (next1 == 0x0A and next2 == qchar) or
                (next1 == 0x0D and next2 == qchar) or
                (next1 == 0x0D and next2 == 0x0A)
            ):
                self.in_quote = False

            elif (c == 0x0A or c == 0x0D) and not self.in_quote and not (next1 == qchar and next2 == fsep):
                lines.append(buffer[line_start:i])
                if c == 0x0D and next1 == 0x0A:
                    i += 1  # Handle CRLF
                line_start = i + 1

            i += 1

        self.leftover = buffer[line_start:]
        return lines

    def flush(self):
        """
        Return the final leftover line at EOF if not empty.
        """
        if self.leftover:
            return [self.leftover]
        return []
