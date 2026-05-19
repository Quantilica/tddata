# Copyright (c) 2026 Komesu, D.K.
# Licensed under the MIT License.

"""Typer plugin for quantilica-cli integration."""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.logging import RichHandler
from rich.rule import Rule
from rich.table import Table

from tesouro_direto_fetcher import downloader
from tesouro_direto_fetcher.constants import (
    DATASET_BUYBACKS,
    DATASET_INVESTORS,
    DATASET_MINT_STOCK,
    DATASET_OPERATIONS,
    DATASET_PRICES_RATES,
    DATASET_SALES,
)

app = typer.Typer(help="Dados do Tesouro Direto (preços, taxas, operações).")

_DEFAULT_OUTPUT = Path("/data/tesouro-direto")
console = Console()

_DATASET_MAP = {
    "prices": DATASET_PRICES_RATES,
    "operations": DATASET_OPERATIONS,
    "investors": DATASET_INVESTORS,
    "stock": DATASET_MINT_STOCK,
    "buybacks": DATASET_BUYBACKS,
    "sales": DATASET_SALES,
}
_DATASET_CHOICES = [*_DATASET_MAP, "all"]


def _setup_logging(verbose: bool) -> None:
    """Configura logging via RichHandler para não quebrar barras de progresso.

    verbose=False → WARNING apenas; verbose=True → DEBUG via Rich console.
    """
    level = logging.DEBUG if verbose else logging.WARNING
    logging.basicConfig(
        level=level,
        format="%(message)s",
        datefmt="[%X]",
        handlers=[RichHandler(console=console, show_path=False)],
        force=True,
    )


def _resolve_ids(name: str) -> list[str]:
    if name == "all":
        return list(_DATASET_MAP.values())
    return [_DATASET_MAP[name]]


def _print_info(info_list: list[dict]) -> None:
    t = Table(show_header=True, header_style="bold")
    t.add_column("Arquivo", style="cyan")
    t.add_column("Tamanho", justify="right")
    t.add_column("Download?", justify="center")

    for info in info_list:
        size_str = (
            f"{info['size']:,} bytes" if info["size"] else "desconhecido"
        )
        flag = (
            "[green]Sim[/green]"
            if info["would_download"]
            else "[dim]Não (atualizado)[/dim]"
        )
        t.add_row(info["filename"], size_str, flag)

    console.print(f"Encontrados [bold]{len(info_list)}[/bold] recursos:")
    console.print(t)


@app.command("sync")
def cmd_sync(
    output: Annotated[
        Path, typer.Option("-o", "--output", help="Diretório de saída")
    ] = _DEFAULT_OUTPUT,
    dataset: Annotated[
        str,
        typer.Option(
            "--dataset",
            help=f"Dataset ({', '.join(_DATASET_CHOICES)})",
        ),
    ] = "all",
    dry_run: Annotated[
        bool, typer.Option("--dry-run", help="Listar sem baixar")
    ] = False,
    verbose: Annotated[
        bool, typer.Option("--verbose", help="Logs detalhados")
    ] = False,
) -> None:
    """Sincronizar datasets do Tesouro Direto."""
    _setup_logging(verbose)
    if dataset not in _DATASET_CHOICES:
        console.print(
            f"[red]Erro:[/red] dataset inválido '{dataset}'."
            f" Opções: {', '.join(_DATASET_CHOICES)}"
        )
        raise typer.Exit(1)

    if dry_run:

        async def _dry() -> None:
            if dataset == "all":
                for ds_name, ds_id in _DATASET_MAP.items():
                    console.rule(
                        f"[bold cyan]{ds_name}[/bold cyan]",
                        style="cyan dim",
                    )
                    info_list = await downloader.get_download_info(
                        output, dataset_id=ds_id
                    )
                    _print_info(info_list)
            else:
                info_list = await downloader.get_download_info(
                    output, dataset_id=_DATASET_MAP[dataset]
                )
                _print_info(info_list)

        asyncio.run(_dry())
        return

    async def _run() -> None:
        for dataset_id in _resolve_ids(dataset):
            await downloader.download(output, dataset_id=dataset_id)

    try:
        with console.status(f"[cyan]Sincronizando {dataset}...[/cyan]"):
            asyncio.run(_run())
    except KeyboardInterrupt:
        console.print("[yellow]Download cancelado.[/yellow]")
        raise typer.Exit(code=130) from None
    console.print(
        f"[green]✓[/green] [bold]{dataset}[/bold] sincronizado em"
        f" [dim]{output}[/dim]"
    )


@app.command("convert")
def cmd_convert(
    data_dir: Annotated[
        Path,
        typer.Argument(
            help="Diretório de dados (raiz da árvore <dataset_id>/)"
        ),
    ],
    verbose: Annotated[
        bool, typer.Option("--verbose", help="Logs detalhados")
    ] = False,
) -> None:
    """Converter CSVs mais recentes para Parquet (requer extras de análise)."""
    _setup_logging(verbose)
    _convert_dir(data_dir)


def _convert_dir(data_dir: Path) -> None:
    """Converter os CSVs mais recentes de ``data_dir`` para Parquet."""
    try:
        from tesouro_direto_fetcher import converter
        from tesouro_direto_fetcher.storage import DataRepository
    except ImportError:
        console.print(
            "[red]Erro:[/red] convert requer extras de análise:"
            " pip install tesouro-direto-fetcher[analysis]"
        )
        raise typer.Exit(1) from None

    if not data_dir.is_dir():
        console.print(
            f"[red]Erro:[/red] diretório '{data_dir}' não existe."
        )
        raise typer.Exit(1)

    repo = DataRepository(data_dir)
    for dataset_id in repo.list_datasets():
        for fp in repo.get_all_latest_files(dataset_id):
            output_path = converter.convert_to_parquet(fp)
            console.print(
                f"  [green]✓[/green] {fp.name} → {output_path.name}"
            )


@app.command("pipeline")
def cmd_pipeline(
    output: Annotated[
        Path, typer.Option("-o", "--output", help="Diretório de saída")
    ] = _DEFAULT_OUTPUT,
    dataset: Annotated[
        str,
        typer.Option(
            "--dataset",
            help=f"Dataset ({', '.join(_DATASET_CHOICES)})",
        ),
    ] = "all",
    verbose: Annotated[
        bool, typer.Option("--verbose", help="Logs detalhados")
    ] = False,
) -> None:
    """Pipeline completo do Tesouro Direto (sync → convert)."""
    _setup_logging(verbose)
    if dataset not in _DATASET_CHOICES:
        console.print(
            f"[red]Erro:[/red] dataset inválido '{dataset}'."
            f" Opções: {', '.join(_DATASET_CHOICES)}"
        )
        raise typer.Exit(1)

    console.print(Rule("[bold]Passo 1/2: Sincronização[/bold]"))

    async def _run() -> None:
        for dataset_id in _resolve_ids(dataset):
            await downloader.download(output, dataset_id=dataset_id)

    try:
        with console.status(f"[cyan]Sincronizando {dataset}...[/cyan]"):
            asyncio.run(_run())
    except KeyboardInterrupt:
        console.print("[yellow]Download cancelado.[/yellow]")
        raise typer.Exit(code=130) from None
    console.print("[green]✓[/green] Sincronização concluída.")

    console.print(Rule("[bold]Passo 2/2: Conversão[/bold]"))
    _convert_dir(output)
    console.print("[green]✓[/green] Conversão concluída.")
