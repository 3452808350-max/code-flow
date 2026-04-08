#!/usr/bin/env python3
"""Health check for the Harness Lab backend container."""

import sys
import requests
import os

def health_check():
    try:
        port = os.getenv('PORT', '4600')
        url = f"http://localhost:{port}/api/health"
        response = requests.get(url, timeout=10)

        if response.status_code == 200:
            data = response.json()
            payload = data.get('data', {})
            if data.get('success') is True and payload.get('status') == 'healthy':
                print("Health check passed")
                return 0
            print(f"Service unhealthy: {data}")
            return 1
        print(f"Health check failed with status code: {response.status_code}")
        return 1
    except requests.exceptions.RequestException as e:
        print(f"Health check failed with error: {e}")
        return 1
    except Exception as e:
        print(f"Unexpected error during health check: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(health_check())
