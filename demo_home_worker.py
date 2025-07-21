#!/usr/bin/env python3
# Home Automation Worker - Browser and Computer control
import sys
import os
sys.path.append(os.path.dirname(__file__))
from enhanced_worker_launcher import main
import sys

# Override sys.argv for this demo
sys.argv = [
    'enhanced_worker_launcher.py',
    '--integrations', 'browser:google_search,youtube_search', 'computer:volume_control,media_control',
    '--name', 'Home-Automation-Worker',
    '--location', 'Living Room',
    '--server', 'http://192.168.1.100:8080'
]

if __name__ == "__main__":
    main()
