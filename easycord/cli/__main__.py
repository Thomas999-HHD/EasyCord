"""EasyCord CLI entry point."""
import sys
from .quickstart import main as quickstart_main


def main() -> None:
    """Main CLI entry point."""
    if len(sys.argv) < 2:
        print("EasyCord CLI")
        print()
        print("Commands:")
        print("  easycord quickstart  - Get running in 60 seconds")
        print()
        sys.exit(0)

    command = sys.argv[1]

    if command == "quickstart":
        quickstart_main()
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)


if __name__ == "__main__":
    main()
