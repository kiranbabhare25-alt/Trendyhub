import os
import sys


def main():
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "trendyhub_project.settings")

    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Django is not installed. Run `pip install -r requirements.txt` first."
        ) from exc

    execute_from_command_line(["manage.py", "runserver", *sys.argv[1:]])


if __name__ == "__main__":
    main()
