import os

# Ensure ADMIN_SECRET is set before app.py is imported by test modules.
os.environ.setdefault("ADMIN_SECRET", "test-secret")
