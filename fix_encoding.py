#!/usr/bin/env python3
import os
import sys
import codecs
import chardet

def convert_to_utf8(file_path):
    print(f"Converting {file_path} to UTF-8...")
    
    # Detect the encoding
    with open(file_path, 'rb') as f:
        raw_data = f.read()
        result = chardet.detect(raw_data)
        encoding = result['encoding']
        confidence = result['confidence']
    
    print(f"Detected encoding: {encoding} with confidence: {confidence}")
    
    if encoding is None:
        print(f"Could not detect encoding for {file_path}, skipping")
        return
    
    try:
        # Try to decode with the detected encoding
        content = raw_data.decode(encoding)
        
        # Write the content back with UTF-8 encoding
        with codecs.open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f"Successfully converted {file_path} to UTF-8")
    except Exception as e:
        print(f"Error converting {file_path}: {e}")

def process_directory(directory):
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith('.py'):
                file_path = os.path.join(root, file)
                convert_to_utf8(file_path)

if __name__ == "__main__":
    directory = "/home/chris/normx-ai"
    if len(sys.argv) > 1:
        directory = sys.argv[1]
    
    process_directory(directory)
    print("Conversion completed.")