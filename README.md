# tesouro-direto-fetcher: Download, análise e visualização do Tesouro Direto

![License: GPL-3.0](https://img.shields.io/badge/license-GPL--3.0-blue.svg?style=flat-square) ![Python](https://img.shields.io/badge/python-3.12+-blue.svg?style=flat-square) [![Tests](https://github.com/Quantilica/tesouro-direto-fetcher/actions/workflows/run-tests.yml/badge.svg)](https://github.com/Quantilica/tesouro-direto-fetcher/actions/workflows/run-tests.yml)

Biblioteca Python para download, leitura e visualização de dados históricos do Tesouro Direto via API CKAN (Tesouro Transparente). Fornece leitores especializados por tipo de dataset e gráficos prontos com Altair.

## Instalação

Instalação mínima (apenas download):

```bash
pip install "git+https://github.com/Quantilica/tesouro-direto-fetcher#egg=tesouro-direto-fetcher"
```

Com análise e visualização (adiciona Polars e Altair):

```bash
pip install "git+https://github.com/Quantilica/tesouro-direto-fetcher#egg=tesouro-direto-fetcher[analysis]"
```

## Uso Rápido

```python
import asyncio
from pathlib import Path
from tesouro_direto_fetcher import downloader, reader

# Download dos dados de preços/taxas
asyncio.run(
    downloader.download(
        dest_dir=Path("./dados"),
        dataset_id="taxas-dos-titulos-ofertados-pelo-tesouro-direto",
    )
)

# Leitura
df_precos = reader.read_prices(
    Path("./dados/taxas-dos-titulos-ofertados-pelo-tesouro-direto@20251230T102010.csv")
)
```

## CLI

Consulte [docs/CLI.md](docs/CLI.md) para a referência completa de comandos, opções e exemplos.

## API Python

### Download assíncrono

```python
import asyncio
from pathlib import Path
from tesouro_direto_fetcher import downloader

asyncio.run(
    downloader.download(
        dest_dir=Path("./dados"),
        dataset_id="taxas-dos-titulos-ofertados-pelo-tesouro-direto",
        max_concurrency=3,
    )
)
```

### Leitura

```python
from pathlib import Path
from tesouro_direto_fetcher import reader

df_precos      = reader.read_prices(Path("./dados/taxas-...@....csv"))
df_estoque     = reader.read_stock(Path("./dados/estoque-...@....csv"))
df_investidores = reader.read_investors(Path("./dados/investidores-...@....csv"))
```

### Visualização

```python
from tesouro_direto_fetcher import plot

plot.plot_prices(df_precos, bond_type="Tesouro Selic").save("precos.html")
plot.plot_stock(df_estoque, by_bond_type=True).save("estoque.html")
plot.plot_investors_population_pyramid(df_investidores).save("piramide.html")
```

Helpers disponíveis: `plot_investors_evolution`, `plot_operations`, `plot_sales`, `plot_buybacks`, `plot_maturities`, `plot_interest_coupons`. Veja [docs/PLOTS.md](docs/PLOTS.md).

## Fontes de Dados

Todos os dados são obtidos via [API CKAN do Tesouro Transparente](https://www.tesourotransparente.gov.br/ckan/):

| Dataset | ID CKAN |
| :--- | :--- |
| Preços / Taxas | `taxas-dos-titulos-ofertados-pelo-tesouro-direto` |
| Estoque | `estoque-do-tesouro-direto` |
| Investidores | `investidores-do-tesouro-direto` |
| Operações | `operacoes-do-tesouro-direto` |
| Vendas | `vendas-do-tesouro-direto` |
| Recompras | `recompras-do-tesouro-direto` |

## Desenvolvimento

```bash
git clone https://github.com/Quantilica/tesouro-direto-fetcher.git
cd tesouro-direto-fetcher
uv sync --dev
uv run pytest
```

## Licença

MIT — veja [LICENSE](LICENSE).
