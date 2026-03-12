"""Entry point for running the Temporal HTR server: python -m digital_scribe"""

from digital_scribe.server import mcp

if __name__ == "__main__":
    mcp.run(transport="stdio")
