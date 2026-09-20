"""Optional startup log for packaged-release QA, disabled for ordinary users."""
import os
import sys
path = os.environ.get('CAPCRAFT_BOOT_LOG')
if path:
    sys.stderr = open(path, 'w', encoding='utf8', buffering=1)
    sys.stdout = sys.stderr
