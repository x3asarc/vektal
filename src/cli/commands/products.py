"""
Product-related CLI commands.

Commands for updating products, analyzing quality, and processing identifiers.
"""

import sys
from pathlib import Path
from typing import Optional
from typing_extensions import Annotated

import typer
import pandas as pd

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from src.core.pipeline import process_identifier, apply_payload_with_context
from src.core.shopify_resolver import ShopifyResolver
from src.core.product_analyzer import ProductAnalyzer, present_analysis_cli

app = typer.Typer(help="Product operations")


@app.command("update-sku")
def update_sku(
    sku: Annotated[str, typer.Argument(help="SKU to update")],
    dry_run: Annotated[bool, typer.Option("--dry-run", help="Preview changes without applying")] = False,
    auto_apply: Annotated[bool, typer.Option("--auto-apply", help="Apply changes without confirmation")] = False,
    auto_fix: Annotated[bool, typer.Option("--auto-fix", help="Automatically apply analyzer corrections")] = False,
    no_analyze: Annotated[bool, typer.Option("--no-analyze", help="Skip pre-processing analysis")] = False,
):
    """
    Update a product by SKU.

    Processes the product through the pipeline: resolve → scrape → enrich → apply.
    """
    from cli.main import process_single, build_identifier_from_args

    # Create mock args object for compatibility with existing code
    class Args:
        def __init__(self):
            self.sku = sku
            self.dry_run = dry_run
            self.auto_apply = auto_apply
            self.auto_fix = auto_fix
            self.no_analyze = no_analyze
            self.no_prompt = False
            self.select_index = None
            self.mode = "cli"
            self.out = "pipeline_results.csv"

    args = Args()

    resolver = ShopifyResolver()
    context = {
        "resolver": resolver,
        "shop_domain": resolver.shop_domain,
        "access_token": resolver.client.access_token,
        "api_version": resolver.api_version,
    }

    identifier = {"kind": "sku", "value": sku}
    payload, apply_result = process_single(identifier, args, batch_state={}, context=context)

    if payload.get("errors"):
        typer.secho(f"Errors: {', '.join(payload['errors'])}", fg=typer.colors.RED)
        raise typer.Exit(1)

    typer.secho("✓ Product updated successfully", fg=typer.colors.GREEN)


@app.command("analyze")
def analyze(
    sku: Annotated[Optional[str], typer.Option("--sku", help="Product SKU")] = None,
    handle: Annotated[Optional[str], typer.Option("--handle", help="Product handle")] = None,
    title: Annotated[Optional[str], typer.Option("--title", help="Product title")] = None,
):
    """
    Analyze product quality and suggest corrections.

    Checks for SKU/naming issues, missing fields, and data quality problems.
    """
    if not any([sku, handle, title]):
        typer.secho("Error: Must provide --sku, --handle, or --title", fg=typer.colors.RED)
        raise typer.Exit(1)

    identifier = {}
    if sku:
        identifier = {"kind": "sku", "value": sku}
    elif handle:
        identifier = {"kind": "handle", "value": handle}
    elif title:
        identifier = {"kind": "title", "value": title}

    resolver = ShopifyResolver()
    context = {"resolver": resolver}

    # Resolve product
    resolve_result = resolver.resolve_identifier(identifier)
    matches = resolve_result.get("matches", [])

    if not matches:
        typer.secho("No product found", fg=typer.colors.RED)
        raise typer.Exit(1)

    product = matches[0]

    # Run analysis
    analyzer = ProductAnalyzer(context)
    analysis = analyzer.analyze(product, identifier, product.get("vendor"))

    if analysis.has_issues():
        corrections = present_analysis_cli(analysis, auto_approve=False)
        typer.secho(f"\n✓ Analysis complete: {len(corrections)} corrections suggested", fg=typer.colors.GREEN)
    else:
        typer.secho("✓ No issues found", fg=typer.colors.GREEN)


@app.command("process")
def process(
    csv_file: Annotated[Path, typer.Argument(help="CSV file with product identifiers", exists=True)],
    output: Annotated[Path, typer.Option("--output", "-o", help="Output CSV file")] = Path("pipeline_results.csv"),
    dry_run: Annotated[bool, typer.Option("--dry-run", help="Preview changes without applying")] = False,
    auto_apply: Annotated[bool, typer.Option("--auto-apply", help="Apply changes without confirmation")] = False,
):
    """
    Process multiple products from CSV file.

    CSV should contain columns: SKU, EAN, Handle, Title, or URL.
    """
    from cli.main import process_single, build_identifier_from_row, write_results

    class Args:
        def __init__(self):
            self.dry_run = dry_run
            self.auto_apply = auto_apply
            self.no_prompt = True
            self.select_index = None
            self.mode = "cli"
            self.auto_fix = False
            self.no_analyze = False
            self.out = str(output)

    args = Args()

    resolver = ShopifyResolver()
    context = {
        "resolver": resolver,
        "shop_domain": resolver.shop_domain,
        "access_token": resolver.client.access_token,
        "api_version": resolver.api_version,
    }

    df = pd.read_csv(csv_file)
    rows = []
    batch_state = {}

    typer.secho(f"Processing {len(df)} products from {csv_file}...", fg=typer.colors.BLUE)

    for idx, row in df.iterrows():
        identifier = build_identifier_from_row(row)
        if not identifier:
            typer.secho(f"Row {idx+1}: No valid identifier found", fg=typer.colors.YELLOW)
            continue

        payload, apply_result = process_single(identifier, args, batch_state=batch_state, context=context)

        # Build result row
        from cli.main import _result_row
        rows.append(_result_row(identifier, payload, apply_result))

        status = "✓" if not payload.get("errors") else "✗"
        typer.secho(f"{status} Row {idx+1}: {identifier.get('value')}", fg=typer.colors.GREEN if status == "✓" else typer.colors.RED)

    write_results(rows, args.out)
    typer.secho(f"\n✓ Results written to {output}", fg=typer.colors.GREEN)


if __name__ == "__main__":
    app()
