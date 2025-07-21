#!/usr/bin/env python3
# Minimal Worker - Just browser capabilities
import sys
import os
sys.path.append(os.path.dirname(__file__))
from enhanced_worker_launcher import main
import sys

# Override sys.argv for this demo
sys.argv = [
    'enhanced_worker_launcher.py',
    '--integrations', 'browser:google_search',
    '--name', 'Minimal-Worker',
    '--dry-run'  # Don't actually start, just show what would be loaded
]

if __name__ == "__main__":
    main()
