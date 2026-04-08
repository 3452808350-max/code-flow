#!/usr/bin/env python3
"""Start the Harness Lab backend inside Docker."""

import os
import sys
import time
import logging
from pathlib import Path

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def setup_directories():
    directories = [
        "backend/data/harness_lab",
        "backend/data/harness_lab/artifacts",
        "logs"
    ]

    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)
        logger.info(f"Created directory: {directory}")

def check_environment():
    required_vars = ['HOST', 'PORT']

    for var in required_vars:
        if not os.getenv(var):
            logger.warning(f"Environment variable {var} not set")

    os.environ.setdefault('HOST', '0.0.0.0')
    os.environ.setdefault('PORT', '4600')
    os.environ.setdefault('DEBUG', 'False')

    logger.info(f"Server will start on {os.getenv('HOST')}:{os.getenv('PORT')}")

def wait_for_dependencies():
    time.sleep(2)
    logger.info("Dependencies check completed")

def start_server():
    import uvicorn
    from backend.app.main import app

    host = os.getenv('HOST', '0.0.0.0')
    port = int(os.getenv('PORT', '4600'))
    debug = os.getenv('DEBUG', 'False').lower() == 'true'

    logger.info(f"Starting server on {host}:{port}")

    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level="info" if not debug else "debug",
        access_log=True
    )

def main():
    try:
        logger.info("Starting Harness Lab backend...")
        setup_directories()
        check_environment()
        wait_for_dependencies()
        start_server()
    except Exception as e:
        logger.error(f"Failed to start server: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
