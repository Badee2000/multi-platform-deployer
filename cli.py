"""Compatibility CLI entrypoint.

This thin wrapper lets developers continue running ``python cli.py`` locally
while all real logic lives in ``multi_platform_deployer.cli``.
"""

from multi_platform_deployer.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
