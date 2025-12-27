import struct
import numpy as np
import re

def read_phi_spectrum(file_path):
    """
    Parses a PHI XPS file (.spe/.pro) separating Text Header and Binary Data.
    """
    # 1. Read the text header first
    header_lines = []
    points_per_region = []
    binary_start_offset = 0
    
    with open(file_path, 'rb') as f:
        # Read line by line until EOFH
        while True:
            line_bytes = f.readline()
            try:
                line_str = line_bytes.decode('utf-8').strip()
            except:
                # Fallback for latin-1 if utf-8 fails
                line_str = line_bytes.decode('latin-1').strip()
            
            header_lines.append(line_str)
            
            # Extract point counts from "SpectralRegDef"
            # Format example: SpectralRegDef: 1 1 Su1s 111 1356 ...
            # The 5th element (index 4) is usually the count.
            if line_str.startswith('SpectralRegDef:'):
                parts = line_str.split()
                if len(parts) > 5:
                    # parts[0] is "SpectralRegDef:", parts[1] is ID...
                    # We look for the large integer. Based on your file: 
                    # "1 1 Su1s 111 1356" -> 1356 is the count.
                    try:
                        count = int(parts[5]) # Index might vary, let's verify with your data
                        points_per_region.append(count)
                    except ValueError:
                        pass

            # Stop at EOFH
            if line_str == 'EOFH':
                binary_start_offset = f.tell()
                break
    
    print(f"Found {len(points_per_region)} regions.")
    print(f"Points per region: {points_per_region}") # Expecting [1356, 201, 201, 201, 801]

    # 2. Parse Binary Data
    # The binary part is tricky because of the headers (pnt, f4, etc.)
    # We will read the ENTIRE binary blob and search for the data blocks.
    
    data_regions = []
    
    with open(file_path, 'rb') as f:
        f.seek(binary_start_offset)
        binary_content = f.read()

        # Strategy: We know we are looking for floats (4 bytes).
        # We know the exact number of points for each region.
        # We will scan the binary blob for sequences that match the expected length.
        
        current_pos = 0
        for count in points_per_region:
            needed_bytes = count * 4
            
            # Simple heuristic: The data usually follows a pattern containing 'f4' or similar.
            # But simpler: The data is likely the largest chunks of valid floats.
            # Let's try to just find the next valid block after skipping the mini-header.
            
            # Scan forward to find where the data *might* start.
            # Usually, PHI binary headers are fixed length (e.g., ~100-300 bytes).
            # Let's try to brute-force find the data by checking values.
            # (Note: In a robust app, we would reverse-engineer the 'pnt' header structure,
            # but for now, let's try reading floats until they make sense or using a known offset).
            
            # HACK: If we just dump all floats in the file, we might find our data.
            # Since you are making a tool, strict parsing is better.
            # PHI Binary Header often ends with distinct bytes.
            # Let's assume a fixed offset skip for now, or just extract ALL floats and split them.
            pass

    # Alternative: "Lazy" extraction
    # Convert the WHOLE binary part to floats, ignoring alignment errors for a moment.
    # This often reveals the data because the "Header" text (pnt, c/s) becomes garbage NaN or huge numbers,
    # while the real data looks like XPS counts (0 to 1,000,000).
    
    all_floats = np.frombuffer(binary_content, dtype=np.float32)
    
    print(f"Total floats found in binary block: {len(all_floats)}")
    print(all_floats[199])
    # Try to slice the data based on known counts
    # This part requires manual tuning: find where the "real" numbers start.
    # We can filter for reasonable values (e.g., counts > 0).
    
    return header_lines, points_per_region, all_floats

#デバック
import tkinter.filedialog as tkfl

path_d=tkfl.askopenfilename()
read_phi_spectrum(path_d)

