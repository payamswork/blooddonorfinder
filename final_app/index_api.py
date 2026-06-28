import sys
import os

# Make sure the root project directory is on the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app

# Vercel expects a variable named `app`
