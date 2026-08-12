#!/usr/bin/env python
"""Django komut satırı yardımcı aracı."""
import os
import sys


def main() -> None:
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:  # pragma: no cover
        raise ImportError(
            "Django import edilemedi. Sanal ortam etkin mi, "
            "requirements.txt kuruldu mu?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
