import sys
import os
print(f"Current working directory: {os.getcwd()}")
print(f"sys.path: {sys.path}")
try:
    import utils
    print(f"Successfully imported utils: {utils}")
except ImportError as e:
    print(f"Failed to import utils: {e}")
