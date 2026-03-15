import sys
import os

# Add the current directory to the path so Python can find the 'backend' package
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from backend.app import app

if __name__ == "__main__":
    app.run()
