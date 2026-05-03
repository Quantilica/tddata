import shutil
import tempfile
import unittest
from pathlib import Path

import polars as pl

from tddata import reader
from tddata.constants import Column


class TestReader(unittest.TestCase):
    def setUp(self):
        self.test_dir = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def create_csv_file(self, filename, content):
        filepath = self.test_dir / filename
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
        return filepath

    def test_read_stock(self):
        content = (
            "Tipo Titulo;Vencimento do Titulo;Mes Estoque;PU;Quantidade;Valor Estoque\n"
            "Tesouro Prefixado;01/01/2026;12/2024;800,50;1000,00;800500,00"
        )
        filepath = self.create_csv_file("stock.csv", content)
        df = reader.read_stock(filepath)

        self.assertEqual(df.height, 1)
        self.assertIn(Column.STOCK_MONTH.value, df.columns)
        self.assertIn(Column.BOND_TYPE.value, df.columns)
        self.assertEqual(df[Column.UNIT_PRICE.value][0], 800.50)
        self.assertEqual(df[Column.QUANTITY.value][0], 1000.00)
        self.assertEqual(df[Column.MATURITY_DATE.value].dtype, pl.Date)
        self.assertEqual(df[Column.STOCK_MONTH.value].dtype, pl.Date)

    def test_read_investors(self):
        content = (
            "Codigo do Investidor;Data de Adesao;Estado Civil;Genero;Profissao;Idade;UF do Investidor;Cidade do Investidor;Pais do Investidor;Situacao da Conta;Operou 12 Meses\n"
            "123;01/01/2024;Solteiro;M;Engenheiro;30;SP;Sao Paulo;BR;Ativa;S"
        )
        filepath = self.create_csv_file("investors.csv", content)
        df = reader.read_investors(filepath)

        self.assertEqual(df.height, 1)
        self.assertIn(Column.INVESTOR_ID.value, df.columns)
        self.assertEqual(df[Column.INVESTOR_ID.value][0], 123)
        self.assertEqual(df[Column.JOIN_DATE.value].dtype, pl.Date)

    def test_read_operations(self):
        content = (
            "Codigo do Investidor;Data da Operacao;Tipo Titulo;Vencimento do Titulo;Quantidade;Valor do Titulo;Valor da Operacao;Tipo da Operacao;Canal da Operacao\n"
            "456;15/05/2024;Tesouro Selic;01/03/2029;1,5;1000,00;1500,00;C;Site"
        )
        filepath = self.create_csv_file("operations.csv", content)
        df = reader.read_operations(filepath)

        self.assertEqual(df.height, 1)
        self.assertEqual(df[Column.QUANTITY.value][0], 1.5)
        self.assertEqual(df[Column.OPERATION_VALUE.value][0], 1500.0)
        self.assertIn(Column.OPERATION_TYPE.value, df.columns)
        self.assertEqual(df[Column.OPERATION_DATE.value].dtype, pl.Date)

    def test_read_sales(self):
        content = (
            "Tipo Titulo;Vencimento do Titulo;Data Venda;PU;Quantidade;Valor\n"
            "Tesouro IPCA+;15/08/2026;02/01/2024;3000,00;2,0;6000,00"
        )
        filepath = self.create_csv_file("sales.csv", content)
        df = reader.read_sales(filepath)

        self.assertEqual(df.height, 1)
        self.assertEqual(df[Column.VALUE.value][0], 6000.0)
        self.assertEqual(df[Column.SALE_DATE.value].dtype, pl.Date)

    def test_read_buybacks(self):
        content = (
            "Tipo Titulo;Vencimento do Titulo;Data Resgate;Quantidade;Valor\n"
            "Tesouro Prefixado;01/01/2025;10/01/2024;5,0;4500,50"
        )
        filepath = self.create_csv_file("buybacks.csv", content)
        df = reader.read_buybacks(filepath)

        self.assertEqual(df.height, 1)
        self.assertEqual(df[Column.VALUE.value][0], 4500.50)
        self.assertEqual(df[Column.BUYBACK_DATE.value].dtype, pl.Date)

    def test_read_maturities(self):
        content = (
            "Tipo Titulo;Vencimento do Titulo;Data Resgate;PU;Quantidade;Valor\n"
            "Tesouro IPCA+;15/05/2024;15/05/2024;4000,00;1,0;4000,00"
        )
        filepath = self.create_csv_file("maturities.csv", content)
        df = reader.read_maturities(filepath)

        self.assertEqual(df.height, 1)
        self.assertEqual(df[Column.UNIT_PRICE.value][0], 4000.00)
        self.assertEqual(df[Column.BUYBACK_DATE.value].dtype, pl.Date)

    def test_read_prices(self):
        content = (
            "Tipo Titulo;Data Vencimento;Data Base;Taxa Compra Manha;Taxa Venda Manha;PU Compra Manha;PU Venda Manha;PU Base Manha\n"
            "Tesouro Selic;01/03/2025;02/01/2024;0,01;0,02;12000,00;12005,00;12002,50"
        )
        filepath = self.create_csv_file("prices.csv", content)
        df = reader.read_prices(filepath)

        self.assertEqual(df.height, 1)
        self.assertEqual(df[Column.BUY_YIELD.value][0], 0.01)
        self.assertEqual(df[Column.BASE_PRICE.value][0], 12002.50)
        self.assertEqual(df[Column.REFERENCE_DATE.value].dtype, pl.Date)

    def test_read_chunked(self):
        content = (
            "Codigo do Investidor;Data de Adesao;Estado Civil;Genero;Profissao;Idade;UF do Investidor;Cidade do Investidor;Pais do Investidor;Situacao da Conta;Operou 12 Meses\n"
            "1;01/01/2024;Solteiro;M;Engenheiro;30;SP;Sao Paulo;BR;Ativa;S\n"
            "2;02/01/2024;Casado;F;Advogada;35;RJ;Rio de Janeiro;BR;Ativa;N"
        )
        filepath = self.create_csv_file("investors_chunked.csv", content)

        # Read with chunksize=1
        iterator = reader.read_investors(filepath, chunksize=1)
        # Check if it is an iterator (generator)
        self.assertTrue(iter(iterator) is iterator)

        chunks = list(iterator)
        self.assertEqual(len(chunks), 2)

        # New: assert each chunk is a Polars DataFrame and contains expected processed data
        for idx, chunk in enumerate(chunks, start=1):
            self.assertIsInstance(chunk, pl.DataFrame)
            self.assertEqual(chunk.height, 1)
            self.assertIn(Column.INVESTOR_ID.value, chunk.columns)
            # Check investor id value is correct in each chunk
            self.assertEqual(chunk[Column.INVESTOR_ID.value][0], idx)
            # Check date column was processed in chunk
            self.assertEqual(chunk[Column.JOIN_DATE.value].dtype, pl.Date)

        df = pl.concat(chunks)
        self.assertEqual(df.height, 2)
        self.assertEqual(df[Column.INVESTOR_ID.value][0], 1)
        self.assertEqual(df[Column.INVESTOR_ID.value][1], 2)

        # Verify processing happened on combined DataFrame as well
        self.assertIn(Column.INVESTOR_ID.value, df.columns)
        self.assertEqual(df[Column.JOIN_DATE.value].dtype, pl.Date)


if __name__ == "__main__":
    unittest.main()
