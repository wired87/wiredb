
import re
import zlib
from typing import List

def extract_math_from_pdf(pdf_bytes: bytes) -> List[str]:
    """
    Extracts text from PDF bytes using pure Python (zlib+regex) and identifies math elements.
    
    Args:
        pdf_bytes (bytes): The raw bytes of the PDF file.
        
    Returns:
        List[str]: A list of strings containing potential math elements.
    """
    text_content = _extract_raw_text(pdf_bytes)
    math_elements = _filter_math_elements(text_content)
    return math_elements

def _extract_raw_text(data: bytes) -> str:
    """
    Iterates through PDF objects, decompresses streams, and extracts text from Tj/TJ operators.
    This is a simplistic PDF parser.
    """
    text_fragments = []
    
    # Find stream blocks
    curr_pos = 0
    while True:
        # Locate stream start
        stream_start_kw = data.find(b'stream', curr_pos)
        if stream_start_kw == -1:
            break

        # Locate stream end
        stream_end_kw = data.find(b'endstream', stream_start_kw)
        if stream_end_kw == -1:
            break
            
        # The 'stream' keyword is followed by CRLF or LF.
        # usually 1 or 2 bytes.
        content_start = data.find(b'\n', stream_start_kw, stream_start_kw + 20)
        if content_start == -1:
            # Fallback for spacing
            content_start = stream_start_kw + 6
        else:
            content_start += 1
            
        stream_content = data[content_start:stream_end_kw].strip()
        
        # Update cursor (fast forward)
        curr_pos = stream_end_kw + 9
        
        # Attempt Decompression (FlateDecode)
        decoded_stream = b""
        try:
            decoded_stream = zlib.decompress(stream_content)
        except Exception:
            # Parsing the dictionary to check /Filter is better, but expensive with regex.
            # If it's not compressed or different algo, we skip or treat as raw if looks like text.
            # Verify if it looks like text stream
            if b'BT' in stream_content or b'Tj' in stream_content:
                decoded_stream = stream_content
            else:
                continue

        # Extract Text from Stream
        if decoded_stream:
            text = _parse_content_stream(decoded_stream)
            if text:
                text_fragments.append(text)

    return "\n".join(text_fragments)

def _parse_content_stream(stream: bytes) -> str:
    """
    Parses BT...ET blocks and extracting text from (string)Tj and [(str) 20 (ing)]TJ operators.
    """
    extracted = []
    
    # We process the stream looking for text operators.
    # Simple regex based approach.
    
    # Matches: (content) Tj
    tj_pattern = re.compile(rb'\((.*?)\)\s*Tj')
    
    # Matches: [(...)] TJ
    # Handling nested parenthesis in regex is hard, simplified for standard PDF strings
    tj_array_pattern = re.compile(rb'\[(.*?)\]\s*TJ')
    
    # Search for all text objects
    # Note: This does not respect order perfectly if we just regex all, but sufficient for extraction.
    
    # Iterating line by line or token by token is better but regex findall is faster for "bag of words".
    # For "math elements", order matters? Yes.
    
    # scan linearly
    tokens = re.finditer(rb'(\((?:\\.|[^)])*\))\s*Tj|\[(.*?)\]\s*TJ', stream)
    
    for match in tokens:
        # Case 1: (...) Tj
        if match.group(1):
             raw = match.group(1)
             text = _clean_pdf_string(raw)
             extracted.append(text)
             
        # Case 2: [...] TJ
        elif match.group(2):
            array_content = match.group(2)
            # Extract strings (...) inside the array
            sub_matches = re.finditer(rb'\((?:\\.|[^)])*\)', array_content)
            line_parts = []
            for sub in sub_matches:
                text = _clean_pdf_string(sub.group(0))
                line_parts.append(text)
            extracted.append("".join(line_parts))
            
    return "\n".join(extracted)

def _clean_pdf_string(pdf_str: bytes) -> str:
    """
    Decodes a PDF string object (...) into a python string.
    Removes the outer parens first.
    """
    # Remove outer parens
    if pdf_str.startswith(b'(') and pdf_str.endswith(b')'):
        pdf_str = pdf_str[1:-1]
    
    # Unescape \\, \(, \)
    pdf_str = pdf_str.replace(b'\\(', b'(').replace(b'\\)', b')').replace(b'\\\\', b'\\')
    
    # Decode
    # Try utf-8, fall back to latin1 (WinAnsiEncoding common default)
    try:
        return pdf_str.decode('utf-8')
    except:
        return pdf_str.decode('latin1', errors='ignore')

def _filter_math_elements(text: str) -> List[str]:
    """
    Identifies strings that look like math equations.
    """
    math_lines = []
    
    # Indicators of math
    # 1. Operators
    operators = set("=+-<>/^∫∑∂√")
    
    # 2. Heuristics
    # a. High density of symbols?
    # b. Contains equals sign surrounded by stuff?
    
    lines = text.split('\n')
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        # Count operators
        op_count = sum(1 for char in line if char in operators)
        
        # If it has equals and some length, or multiple operators
        if "=" in line and len(line) > 3:
             math_lines.append(line)
        elif op_count >= 2:
             math_lines.append(line)
        # Check for specific patterns like "f(x)"
        elif re.search(r'\b[a-zA-Z]\([a-zA-Z0-9_,]+\)', line):
             math_lines.append(line)
             
    return list(set(math_lines)) # De-duplicate
