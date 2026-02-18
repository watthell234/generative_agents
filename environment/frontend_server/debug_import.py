import sys
import os
import importlib

print(f"Current working directory: {os.getcwd()}")
print(f"sys.path: {sys.path}")

try:
    import frontend_server
    print(f"Successfully imported frontend_server: {frontend_server}")
    print(f"frontend_server file: {frontend_server.__file__}")
except ImportError as e:
    print(f"Failed to import frontend_server: {e}")

try:
    import frontend_server.settings
    print(f"Successfully imported frontend_server.settings: {frontend_server.settings}")
    print(f"frontend_server.settings file: {frontend_server.settings.__file__}")
except ImportError as e:
    print(f"Failed to import frontend_server.settings: {e}")

try:
    import frontend_server.settings.mylocal
    print(f"Successfully imported frontend_server.settings.mylocal: {frontend_server.settings.mylocal}")
except ImportError as e:
    print(f"Failed to import frontend_server.settings.mylocal: {e}")
