"""Entry point for running the Temporal HTR server: python -m digital_scribe"""

from digital_scribe.server import mcp


def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
