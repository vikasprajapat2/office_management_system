import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app import app

# This is the handler that Vercel will call
def handler(request, context):
    return app(request, context)
