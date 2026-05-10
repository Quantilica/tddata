import enum


# Columns' names are defined in the constants.py file, which is imported by the
# reader.py file. This is a good practice because it makes the code more
# maintainable. If the column names change, we only need to update the
# constants.py file, and the reader.py file will automatically use the new
# column names. This is a good example of the DRY (Don't Repeat Yourself)
# principle.
class Column(enum.Enum):
    """Column names for the Tesouro Direto data."""

    REFERENCE_DATE = "reference_date"
    BOND_TYPE = "bond_type"
    MATURITY_DATE = "maturity_date"
    BUY_YIELD = "buy_yield"
    SELL_YIELD = "sell_yield"
    BUY_PRICE = "buy_price"
    SELL_PRICE = "sell_price"
    BASE_PRICE = "base_price"

    # Stock (Estoque)
    STOCK_MONTH = "stock_month"
    QUANTITY = "quantity"
    STOCK_VALUE = "stock_value"

    # Investors (Investidores)
    INVESTOR_ID = "investor_id"
    JOIN_DATE = "join_date"
    MARITAL_STATUS = "marital_status"
    GENDER = "gender"
    PROFESSION = "profession"
    AGE = "age"
    STATE = "state"
    CITY = "city"
    COUNTRY = "country"
    ACCOUNT_STATUS = "account_status"
    TRADED_LAST_12_MONTHS = "traded_last_12_months"

    # Operations (Operacoes)
    OPERATION_DATE = "operation_date"
    BOND_VALUE = "bond_value"
    OPERATION_VALUE = "operation_value"
    OPERATION_TYPE = "operation_type"
    CHANNEL = "channel"

    # Common / Others
    BUYBACK_DATE = "buyback_date"
    VALUE = "value"
    SALE_DATE = "sale_date"
    UNIT_PRICE = "unit_price"


class BondType(enum.Enum):
    """Bond types for the Tesouro Direto data."""

    # Tesouro Prefixado (LTN)
    PREFIXED = "Tesouro Prefixado"

    # Tesouro Prefixado com Juros Semestrais (NTN-F)
    PREFIXED_WITH_SEMESTRAL_INTEREST = "Tesouro Prefixado com Juros Semestrais"

    # Tesouro IPCA+ (NTN-B Principal)
    IPCA = "Tesouro IPCA+"

    # Tesouro IPCA+ com Juros Semestrais (NTN-B)
    IPCA_WITH_SEMESTRAL_INTEREST = "Tesouro IPCA+ com Juros Semestrais"

    # Tesouro Selic (LFT)
    SELIC = "Tesouro Selic"

    # Tesouro IGPM+ com Juros Semestrais (NTN-C)
    IGPM_WITH_SEMESTRAL_INTEREST = "Tesouro IGPM+ com Juros Semestrais"

    # Tesouro RendA+ Aposentadoria Extra
    RENDA = "Tesouro RendA+ Aposentadoria Extra"

    # Tesouro EducA+
    EDUCA = "Tesouro EducA+"


class OperationType(enum.Enum):
    """Operation types for the Tesouro Direto data."""

    BUY = "C"
    SELL = "V"
    WITHDRAWAL = "R"
    DEPOSIT = "D"

    @classmethod
    def get_labels(cls):
        return {
            cls.BUY.value: "Compra",
            cls.SELL.value: "Venda",
            cls.WITHDRAWAL.value: "Retirada",
            cls.DEPOSIT.value: "Depósito",
        }


class Channel(enum.Enum):
    """Channel types for Tesouro Direto operations."""

    SITE = "S"
    HOMEBROKER = "H"

    @classmethod
    def get_labels(cls):
        return {
            cls.SITE.value: "Site",
            cls.HOMEBROKER.value: "Homebroker",
        }


class MaritalStatus(enum.Enum):
    """Marital status for Tesouro Direto investors."""

    SINGLE = "Solteiro(a)"
    SEPARATED = "Desquitado(a)"
    WIDOWED = "Viúvo(a)"
    DIVORCED = "Divorciado(a)"
    MARRIED_BRAZILIAN_NATIVE = "Casado(a) com brasileiro(a) nato(a)"
    MARRIED_BRAZILIAN_NATURALIZED = "Casado(a) com brasileiro(a) naturalizado(a)"
    MARRIED_FOREIGNER = "Casado(a) com estrangeiro(a)"
    STABLE_UNION = "União estável"
    LEGALLY_SEPARATED = "Separado judic."
    NOT_APPLICABLE = "Não se aplica"


class Gender(enum.Enum):
    """Gender for Tesouro Direto investors."""

    MALE = "M"
    FEMALE = "F"
    NOT_APPLICABLE = "N"

    @classmethod
    def get_labels(cls):
        return {
            cls.MALE.value: "Masculino",
            cls.FEMALE.value: "Feminino",
            cls.NOT_APPLICABLE.value: "Não se aplica",
        }


class AccountStatus(enum.Enum):
    """Account status for Tesouro Direto investors."""

    ACTIVE = "A"
    DEACTIVATED = "D"

    @classmethod
    def get_labels(cls):
        return {
            cls.ACTIVE.value: "Ativo",
            cls.DEACTIVATED.value: "Desativado",
        }


class TradedLast12Months(enum.Enum):
    """Traded in last 12 months for Tesouro Direto investors."""

    YES = "S"
    NO = "N"

    @classmethod
    def get_labels(cls):
        return {
            cls.YES.value: "Sim",
            cls.NO.value: "Não",
        }


CKAN_API_URL = "https://www.tesourotransparente.gov.br/ckan/api/3/action/package_show"

DATASET_PRICES_RATES = "taxas-dos-titulos-ofertados-pelo-tesouro-direto"
DATASET_OPERATIONS = "operacoes-do-tesouro-direto"
DATASET_INVESTORS = "investidores-do-tesouro-direto"
DATASET_MINT_STOCK = "estoque-do-tesouro-direto"
DATASET_BUYBACKS = "resgates-do-tesouro-direto"
DATASET_SALES = "vendas-do-tesouro-direto"

# Bond type name normalization mapping
# Maps various bond type names found in datasets to standardized names
BOND_TYPE_NORMALIZATION = {
    # Legacy code
    "NTN-B1": "Tesouro RendA+",
    # Case variations
    "Tesouro Renda+ Aposentadoria Extra": "Tesouro RendA+",
    "Tesouro Educa+": "Tesouro EducA+",
    # Already standardized (identity mapping for completeness)
    "Tesouro Selic": "Tesouro Selic",
    "Tesouro Prefixado": "Tesouro Prefixado",
    "Tesouro Prefixado com Juros Semestrais": "Tesouro Prefixado com Juros Semestrais",
    "Tesouro IPCA+": "Tesouro IPCA+",
    "Tesouro IPCA+ com Juros Semestrais": "Tesouro IPCA+ com Juros Semestrais",
    "Tesouro IGPM+ com Juros Semestrais": "Tesouro IGPM+ com Juros Semestrais",
    "Tesouro RendA+": "Tesouro RendA+",
    "Tesouro EducA+": "Tesouro EducA+",
}


def normalize_bond_type(bond_type_name: str) -> str | None:
    """
    Normalize bond type name to standardized format.

    Args:
        bond_type_name: The bond type name from the dataset

    Returns:
        Standardized bond type name, or the original if no mapping exists
    """
    if not bond_type_name:
        return

    # Try exact match first
    if bond_type_name in BOND_TYPE_NORMALIZATION:
        return BOND_TYPE_NORMALIZATION[bond_type_name]

    # Try case-insensitive match
    for key, value in BOND_TYPE_NORMALIZATION.items():
        if key.lower() == bond_type_name.lower():
            return value

    # Return original if no mapping found (with warning potential)
    return bond_type_name
