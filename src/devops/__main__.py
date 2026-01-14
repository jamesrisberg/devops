import sys

from devops.app import DevopsApp

__version__ = "0.1.0"


def main() -> None:
    """Main entry point for the devops TUI."""
    if len(sys.argv) > 1:
        arg = sys.argv[1]
        if arg in ("-h", "--help"):
            print("devops - Development Environment Topology Visualizer")
            print()
            print("Usage: devops [OPTIONS]")
            print()
            print("A TUI for exploring and managing your development environment.")
            print()
            print("Options:")
            print("  -h, --help     Show this help message and exit")
            print("  -v, --version  Show version and exit")
            print()
            print("Keyboard shortcuts (in app):")
            print("  c              Collapse all tree nodes")
            print("  r              Refresh data")
            print("  q              Quit")
            return
        if arg in ("-v", "--version"):
            print(f"devops {__version__}")
            return

    app = DevopsApp()
    app.run()


if __name__ == "__main__":
    main()
