# Saves a Google Drive connector download (JSON with base64 "content") as a file.
# Usage: python3 unpack.py <saved download .txt/.json> <destination path>
import base64, json, os, sys
d = json.load(open(sys.argv[1]))
os.makedirs(os.path.dirname(os.path.abspath(sys.argv[2])), exist_ok=True)
open(sys.argv[2], 'wb').write(base64.b64decode(d['content']))
print(sys.argv[2], os.path.getsize(sys.argv[2]), 'bytes')
