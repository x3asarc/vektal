"""
Search operations CLI commands.

Commands for searching products by SKU, title, or handle.
"""

import sys
from pathlib import Path
from typing import Optional
from typing_extensions import Annotated

import typer
from rich.console import Console
from rich.table import Table

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from src.core.shopify_resolver import ShopifyResolver

app = typer.Typer(help="Search operations")
console = Console()


def display_products(matches, search_term: str, search_type: str):
    """Display search results in a formatted table."""
    if not matches:
        console.print(f"[yellow]No products found for {search_type}: {search_term}[/yellow]")
        return

    table = Table(title=f"Search Results ({len(matches)} found)")
    table.add_column("ID", style="cyan")
    table.add_column("Title", style="green")
    table.add_column("Handle", style="blue")
    table.add_column("SKU", style="magenta")
    table.add_column("Vendor", style="yellow")

    for product in matches:
        product_id = product.get("id", "N/A")
        title = product.get("title", "N/A")
        handle = product.get("handle", "N/A")

        # Get SKU from primary variant
        primary_variant = product.get("primary_variant", {})
        sku = primary_variant.get("sku", "N/A") if primary_variant else "N/A"

        vendor = product.get("vendor", "N/A")

        table.add_row(product_id, title, handle, sku, vendor)

    console.print(table)


@app.command("by-sku")
def search_by_sku(
    sku: Annotated[str, typer.Argument(help="SKU to search for")],
    dry_run: Annotated[bool, typer.Option("--dry-run", help="Dry run (no effect for search)")] = False,
):
    """
    Search for products by SKU.

    Finds all products matching the given SKU.
    """
    resolver = ShopifyResolver()
    identifier = {"kind": "sku", "value": sku}

    console.print(f"[blue]Searching for SKU: {sku}[/blue]")

    result = resolver.resolve_identifier(identifier)
    matches = result.get("matches", [])

    display_products(matches, sku, "SKU")


@app.command("by-title")
def search_by_title(
    title: Annotated[str, typer.Argument(help="Title to search for")],
    dry_run: Annotated[bool, typer.Option("--dry-run", help="Dry run (no effect for search)")] = False,
):
    """
    Search for products by title.

    Finds products matching the given title (partial match supported).
    """
    resolver = ShopifyResolver()
    identifier = {"kind": "title", "value": title}

    console.print(f"[blue]Searching for title: {title}[/blue]")

    result = resolver.resolve_identifier(identifier)
    matches = result.get("matches", [])

    display_products(matches, title, "title")


@app.command("by-handle")
def search_by_handle(
    handle: Annotated[str, typer.Argument(help="Handle to search for")],
    dry_run: Annotated[bool, typer.Option("--dry-run", help="Dry run (no effect for search)")] = False,
):
    """
    Search for product by handle.

    Finds the product with the exact handle.
    """
    resolver = ShopifyResolver()
    identifier = {"kind": "handle", "value": handle}

    console.print(f"[blue]Searching for handle: {handle}[/blue]")

    result = resolver.resolve_identifier(identifier)
    matches = result.get("matches", [])

    display_products(matches, handle, "handle")


if __name__ == "__main__":
    app()
