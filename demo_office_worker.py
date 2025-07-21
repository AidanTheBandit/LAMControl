#!/usr/bin/env python3
# Office Worker - Browser, Computer, and AI capabilities
import sys
import os
sys.path.append(os.path.dirname(__file__))
from enhanced_worker_launcher import main
import sys

# Override sys.argv for this demo
sys.argv = [
    'enhanced_worker_launcher.py',
    '--integrations', 'browser', 'computer', 'ai:openinterpreter',
    '--name', 'Office-Assistant',
    '--location', 'Home Office',
    '--server', 'http://localhost:8080'
]

if __name__ == "__main__":
    main()
