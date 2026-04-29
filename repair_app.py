# -*- coding: utf-8 -*-
import os

def repair_file():
    print("🔍 Starting GVN Repair Engine...")
    input_file = "app.py"
    backup_file = "app_backup.py"
    
    if not os.path.exists(input_file):
        print(f"❌ Error: {input_file} not found!")
        return

    try:
        # Create a backup first
        with open(input_file, 'rb') as f:
            data = f.read()
        
        with open(backup_file, 'wb') as f:
            f.write(data)
        print(f"✅ Backup created: {backup_file}")

        # Clean the file
        # 1. Remove Null Bytes
        clean_data = data.replace(b'\x00', b'')
        
        # 2. Add UTF-8 Header if missing
        header = b"# -*- coding: utf-8 -*-\n"
        if not clean_data.startswith(header):
            clean_data = header + clean_data
            
        # 3. Handle line 2308 SyntaxError (by replacing non-ascii with space)
        # We process as lines to be safe
        lines = clean_data.splitlines()
        print(f"📊 Total lines detected: {len(lines)}")
        
        final_lines = []
        for i, line in enumerate(lines):
            try:
                line.decode('utf-8')
                final_lines.append(line)
            except UnicodeDecodeError:
                print(f"⚠️ Fixing line {i+1} (removed non-UTF8 characters)")
                # Keep only printable ascii or replace with space
                repaired_line = "".join([chr(b) if b < 128 else " " for b in line]).encode('utf-8')
                final_lines.append(repaired_line)

        with open(input_file, 'wb') as f:
            f.write(b'\n'.join(final_lines))
            
        print("✨ SUCCESS: 'app.py' has been repaired and cleaned!")
        print("🚀 Now try running: python app.py")

    except Exception as e:
        print(f"💥 Repair Failed: {e}")

if __name__ == "__main__":
    repair_file()
