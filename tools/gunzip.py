import gzip
import shutil
import sys
import time

def main():
    if len(sys.argv) < 3:
        print("Usage: gunzip.py <input.gz> <output>")
        sys.exit(1)
    
    gz_path = sys.argv[1]
    out_path = sys.argv[2]
    
    start = time.time()
    print(f"Decompressing {gz_path} -> {out_path}...")
    with gzip.open(gz_path, 'rb') as f_in:
        with open(out_path, 'wb') as f_out:
            shutil.copyfileobj(f_in, f_out, length=64 * 1024 * 1024)
    elapsed = time.time() - start
    print(f"Decompression completed in {elapsed:.1f}s")

if __name__ == '__main__':
    main()
