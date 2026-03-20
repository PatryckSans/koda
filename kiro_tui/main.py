#!/usr/bin/env python3
"""Entry point for KODA"""
import sys
from kiro_tui.app import KodaApp


def main():
    """Run the KODA application"""
    app = KodaApp()
    app.run()


if __name__ == "__main__":
    main()
