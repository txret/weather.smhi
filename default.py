"""weather.smhi entry point; see resources/lib/smhi/main.py."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'resources', 'lib'))

from smhi.main import main  # noqa: E402

if __name__ == '__main__':
    main(sys.argv)
