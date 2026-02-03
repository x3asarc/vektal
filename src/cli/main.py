"""
Unified Typer-based CLI for Shopify Multi-Supplier Product Management.

Consolidates functionality from multiple scripts into a single interface.
"""

import typer
from typing_extensions import Annotated

app = typer.Typer(
    name="shopify-tools",
    help="Unified CLI for Shopify product management",
    add_completion=False,
    no_args_is_help=True
)

# Import and add subcommand groups
from src.cli.commands import products, search

app.add_typer(products.app, name="products", help="Product operations (update, analyze, process)")
app.add_typer(search.app, name="search", help="Search operations (by-sku, by-title, by-handle)")


@app.callback()
def main():
    """
    Shopify Multi-Supplier Product Management CLI

    Consolidates functionality from multiple scripts into unified interface.

    Use --help with any command to see available options.
    """
    pass


def cli():
    """Entry point for the CLI."""
    app()


if __name__ == "__main__":
    cli()
