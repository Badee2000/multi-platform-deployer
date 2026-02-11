#!/usr/bin/env python
"""
Multi-Platform Deployer CLI Entry Point
Run: python deploy check
     python deploy run
     python deploy run --multi
     python deploy info
     python deploy health --url <url>
     python deploy rollback
"""

from cli import main
import sys

if __name__ == "__main__":
    sys.exit(main())
