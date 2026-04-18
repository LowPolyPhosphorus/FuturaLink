import sys
import os

# Add src to path so tests can import converter, machine, ui without cd-ing into src
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
