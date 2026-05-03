# Return Calculations in tddata

This document describes the return calculation functions added to the tddata package, inspired by the tddata-db returns module.

## Overview

The return calculation functions in `tddata.analytics` provide Polars-friendly implementations of:

1. **Simple Returns** - Basic percentage return calculations
2. **Annualized Returns** - Compound Annual Growth Rate (CAGR)
3. **Holding Period** - Days held for each position
4. **Operation Returns** - FIFO-matched buy/sell returns with coupon income
5. **Portfolio Returns** - Modified Dietz method for time-weighted returns with coupon distributions

**Key Features:**
- **Coupon Support**: Handles semiannual coupon payments for bonds with "Juros Semestrais"
- **FIFO Matching**: Proper first-in, first-out matching of buy/sell operations
- **Modified Dietz**: Time-weighted returns that account for cash flow timing
- **Data Quality**: Filters out zero-value operations and handles edge cases

## Core Functions

### Simple Return Calculation

```python
calculate_simple_return(current_value, initial_value, min_denominator=0.01)
```

Calculates simple percentage returns for Polars Series.

**Formula:** `((current_value / initial_value) - 1) * 100`

**Example:**
```python
import polars as pl
from tddata.analytics import calculate_simple_return

prices = pl.DataFrame({
    'buy_price': [10000, 20000, 5000],
    'sell_price': [11000, 18000, 5500]
})

returns = calculate_simple_return(prices['sell_price'], prices['buy_price'])
# Returns: [10.0, -10.0, 10.0]
```

### Holding Period Calculation

```python
calculate_holding_period_days(start_date, end_date=None)
```

Calculates holding period in days for positions.

**Example:**
```python
import polars as pl

operations = pl.DataFrame({
    'buy_date': pl.to_datetime(['2024-01-01', '2024-06-01']),
    'sell_date': pl.to_datetime(['2024-07-01', '2024-12-01'])
})

days = calculate_holding_period_days(
    operations['buy_date'],
    operations['sell_date']
)
# Returns: [182, 183]
```

### Annualized Return Calculation

```python
calculate_annualized_return(
    current_value,
    initial_value,
    holding_days,
    min_days=30,
    min_denominator=0.01
)
```

Calculates Compound Annual Growth Rate (CAGR).

**Formula:** `((current_value / initial_value) ^ (365 / holding_days) - 1) * 100`

**Example:**
```python
import polars as pl

positions = pl.DataFrame({
    'buy_value': [10000, 10000],
    'current_value': [11000, 11000],
    'holding_days': [365, 182]
})

annualized = calculate_annualized_return(
    positions['current_value'],
    positions['buy_value'],
    positions['holding_days']
)
# Returns: [10.0, 21.0] (10% over 1 year, ~21% annualized for 6 months)
```

## Advanced Functions

### Operation-Level Returns

```python
calculate_operations_returns(operations, prices, current_date=None, coupons=None)
```

Calculates returns for individual buy/sell operations using FIFO matching.
Supports semiannual coupon payments for bonds with "Juros Semestrais".

**Parameters:**
- `operations`: DataFrame with operation_date, bond_type, maturity_date, quantity, bond_value, operation_value, operation_type
- `prices`: DataFrame with reference_date, bond_type, maturity_date, sell_price
- `current_date`: Optional date for calculating returns (defaults to today)
- `coupons`: Optional DataFrame with coupon payment data (from `read_interest_coupons`). Expected columns: bond_type, maturity_date, buyback_date, unit_price. If provided, coupon income is included in return calculations.

**Returns:** DataFrame with:
- All original operation columns
- `status`: 'open' or 'closed'
- `holding_days`: Days held
- `sell_date`: Date sold (for closed positions)
- `sell_value`: Sale value (for closed positions)
- `current_value`: Current market value (for open positions)
- `total_coupons`: Total coupon income received for this position
- `end_value`: Final value (sell_value + current_value + total_coupons)
- `simple_return`: Simple percentage return including coupons
- `annualized_return`: Annualized return (CAGR) including coupons

**Coupon Handling:**
- Coupons are accumulated per lot during the holding period
- Only coupons received between buy date and sell/end date are included
- Coupon income is added to the final position value before calculating returns
- For bonds without coupons, `total_coupons` will be 0.0

**Example:**
```python
from tddata import reader, analytics
from tddata.constants import Column as C

# Read operations, prices, and coupons
operations = reader.read_operations('operations.csv')
prices = reader.read_prices('prices.csv')
coupons = reader.read_interest_coupons('interest_coupons.csv')  # Optional

# Calculate returns with coupon support
returns = analytics.calculate_operations_returns(operations, prices, coupons=coupons)

# View closed positions with positive returns (Polars)
profitable = returns.filter(
    (returns['status'] == 'closed') & (returns['simple_return'] > 0)
).sort('annualized_return', reverse=True)

print(profitable.select([
    C.BOND_TYPE.value,
    C.OPERATION_DATE.value,
    'sell_date',
    'holding_days',
    'total_coupons',
    'simple_return',
    'annualized_return'
]))
```

**Example Output:**
```
                bond_type operation_date  sell_date  holding_days  total_coupons  simple_return  annualized_return
12  Tesouro IPCA+ com Juros Semestrais     2024-01-01 2024-07-01           182         250.00          15.25             8.12
8           Tesouro Prefixado             2024-02-01 2024-08-01           182           0.00          12.50             6.65
15          Tesouro Selic                 2024-03-01 2024-09-01           184           0.00          10.00             5.28
```

### Portfolio Monthly Returns (Modified Dietz)

```python
calculate_portfolio_monthly_returns(
    operations,
    prices,
    start_date=None,
    end_date=None,
    coupons=None
)
```

Calculates monthly portfolio returns using the Modified Dietz method, which properly accounts for the timing of cash flows.
Supports semiannual coupon payments for bonds with "Juros Semestrais".

**Modified Dietz Formula:**
```
Return = (EMV - BMV - Net_CF) / (BMV + Weighted_CF)

Where:
- EMV = Ending Market Value
- BMV = Beginning Market Value
- Net_CF = Net Cash Flow (positive for deposits, negative for withdrawals/distributions)
- Weighted_CF = Time-weighted cash flows
```

**Cash Flow Weighting:**
```
Weight = days_remaining_in_period / total_days_in_period
```

A deposit early in the month has a weight close to 1.0, while a deposit at the end has a weight close to 0.0, properly reflecting its impact on returns.

**Parameters:**
- `operations`: DataFrame with operation_date, bond_type, maturity_date, quantity, bond_value, operation_value, operation_type columns
- `prices`: DataFrame with reference_date, bond_type, maturity_date, sell_price columns
- `start_date`: Start date for calculations (defaults to first operation)
- `end_date`: End date (defaults to today)
- `coupons`: Optional DataFrame with coupon payment data (from `read_interest_coupons`). Expected columns: bond_type, maturity_date, buyback_date, unit_price. If provided, coupons are treated as distributions (negative cash flows) in the Modified Dietz formula.

**Returns:** DataFrame with:
- `month`: Month start date
- `monthly_return`: Return for that month (%)
- `cumulative_return`: Cumulative return from start (%)
- `portfolio_value`: Portfolio value at end of month
- `net_cash_flow`: Net cash flows during month (including coupon distributions)

**Example:**
```python
# Calculate monthly returns for entire portfolio with coupon support
import altair as alt
from datetime import date
from tddata.analytics import calculate_portfolio_monthly_returns

monthly = calculate_portfolio_monthly_returns(
    operations,
    prices,
    start_date=date(2024, 1, 1),
    end_date=date(2024, 12, 31),
    coupons=coupons,  # Include coupon distributions
)

# Plot cumulative returns
chart = (
    alt.Chart(monthly.to_pandas())
    .mark_line()
    .encode(
        x=alt.X("month:T", title="Month"),
        y=alt.Y("cumulative_return:Q", title="Cumulative Return (%)"),
    )
    .properties(title="Portfolio Cumulative Return (with Coupons)", width=720, height=320)
)
chart.save("portfolio_cumulative_return.html")

# Summary statistics
print(f"Best month: {monthly['monthly_return'].max():.2f}%")
print(f"Worst month: {monthly['monthly_return'].min():.2f}%")
last_cum = monthly['cumulative_return'].to_numpy()[-1]
print(f"Total return: {last_cum:.2f}%")

# Analyze coupon impact
total_coupons = monthly.filter(monthly['net_cash_flow'] < 0)['net_cash_flow'].sum()
print(f"Total coupon distributions: {abs(total_coupons):.2f}")
```

## Comparison with tddata-db Returns Module

The tddata implementation differs from tddata-db in the following ways:

| Feature | tddata-db | tddata |
|---------|-----------|--------|
| **Paradigm** | Object-oriented (classes) | Functional (Polars expressions) |
| **FIFO Tracking** | `LotTracker` class with state | Function-based matching in operations DataFrame |
| **Portfolio** | `PortfolioTracker` class | `calculate_portfolio_monthly_returns` function |
| **Price Lookup** | `PriceLookup` class with caching | DataFrame merge operations |
| **Dependencies** | SQLAlchemy, dateutil | Polars only (lighter) |
| **Use Case** | Database-backed application | Data analysis and plotting |

### Key Design Differences

**tddata-db approach:**
```python
# Stateful, object-oriented
tracker = LotTracker()
for operation in operations:
    tracker.process_operation(...)
summary = tracker.calculate_summary(price_provider)
```

**tddata approach:**
```python
# Stateless, functional
returns = calculate_operations_returns(operations_df, prices_df)
summary = returns.groupby('status').agg({'simple_return': 'mean', ...})
```

## Usage Patterns

### Pattern 1: Analyze Investor Returns

```python
from pathlib import Path
from tddata import reader, analytics

# Load data
data_dir = Path("~/data/tddata")
operations = reader.read_operations(data_dir / "operations.csv")
prices = reader.read_prices(data_dir / "prices.csv")
coupons = reader.read_interest_coupons(data_dir / "interest_coupons.csv")  # Optional

# Calculate returns for all operations with coupon support
returns = analytics.calculate_operations_returns(operations, prices, coupons=coupons)

# Group by investor
investor_returns = returns.groupby('investor_id').agg({
    'operation_value': 'sum',
    'end_value': 'sum',
    'total_coupons': 'sum',
    'simple_return': 'mean',
    'annualized_return': 'mean'
}).reset_index()

# Find best performers
top_investors = investor_returns.nlargest(10, 'annualized_return')

# Analyze coupon impact
print(f"Total coupon income across all investors: {investor_returns['total_coupons'].sum():.2f}")
```

### Pattern 2: Compare Bond Types

```python
# Calculate returns by bond type
by_type = returns.groupby('bond_type').agg({
    'simple_return': ['mean', 'median', 'std'],
    'annualized_return': ['mean', 'median'],
    'total_coupons': ['sum', 'mean'],
    'holding_days': 'mean'
}).reset_index()

# Flatten column names
by_type.columns = ['_'.join(col).strip('_') for col in by_type.columns]

# Compare coupon vs non-coupon bonds
coupon_bonds = by_type[by_type['bond_type'].str.contains('Juros Semestrais')]
non_coupon_bonds = by_type[~by_type['bond_type'].str.contains('Juros Semestrais')]

print("Coupon Bonds Performance:")
print(coupon_bonds[['bond_type', 'annualized_return_mean', 'total_coupons_sum']])
print("\nNon-Coupon Bonds Performance:")
print(non_coupon_bonds[['bond_type', 'annualized_return_mean']])
```

### Pattern 3: Time-Series Analysis

```python
# Monthly portfolio returns with coupon support
monthly = analytics.calculate_portfolio_monthly_returns(
    operations,
    prices,
    coupons=coupons
)

# Rolling 12-month return
monthly['rolling_12m'] = monthly['monthly_return'].rolling(12).sum()

# Volatility (standard deviation of monthly returns)
volatility = monthly['monthly_return'].std()
print(f"Monthly volatility: {volatility:.2f}%")

# Analyze seasonal coupon patterns
monthly['coupon_distributions'] = monthly['net_cash_flow'].where(monthly['net_cash_flow'] < 0, 0).abs()
monthly.groupby(monthly['month'].dt.month)['coupon_distributions'].mean().plot(kind='bar')
plt.title('Average Monthly Coupon Distributions')
plt.xlabel('Month')
plt.ylabel('Average Coupon Amount')
plt.show()
```

### Pattern 4: Risk-Adjusted Returns

```python
# Calculate Sharpe-like ratio (simplified)
monthly = analytics.calculate_portfolio_monthly_returns(operations, prices)

avg_return = monthly['monthly_return'].mean()
std_return = monthly['monthly_return'].std()

if std_return > 0:
    risk_adj_return = avg_return / std_return
    print(f"Risk-adjusted return: {risk_adj_return:.2f}")
```

## Implementation Notes

### Performance Considerations

1. **Vectorized Operations**: All calculations use Polars vectorized operations for performance
2. **Memory Efficiency**: Functions return new DataFrames without modifying input data
3. **Large Datasets**: For very large datasets, consider chunking operations

### Error Handling

The functions include safeguards:
- Division by zero protection (min_denominator parameter)
- Return capping (-100% to 1000%) to handle data anomalies
- Invalid value handling (returns 0.0 for invalid inputs)

### Coupon Calculations

**Operation-Level Returns:**
- Coupons are accumulated per lot during the holding period
- Only coupons received between buy date and sell/end date are counted
- Total coupon income is added to position value before return calculation
- Formula: `end_value = sell_value + current_value + total_coupons`

**Portfolio-Level Returns:**
- Coupons are treated as distributions (negative cash flows)
- Time-weighted like other cash flows in Modified Dietz formula
- Early-month coupons have higher weight than late-month coupons
- Reduces portfolio value but represents income to investors

**Data Filtering:**
- Zero bond value operations are automatically filtered out
- Invalid coupon data is handled gracefully (missing coupons = 0.0)

### Data Quality

For accurate results, ensure:
- **Date Columns**: Properly parsed as Polars datetime
- **Numeric Columns**: Values are float/numeric types
- **Price Data**: Complete monthly price coverage
- **Operation Types**: Correctly coded ('C'/'D' for buys, 'V'/'R' for sells)
- **Coupon Data** (optional): When using coupons parameter, ensure:
  - `bond_type` and `maturity_date` match operations and prices data
  - `buyback_date` represents coupon payment dates
  - `unit_price` is the coupon amount per bond unit
  - Data covers the full holding period for accurate calculations

## Future Enhancements

Possible additions:
1. Tax-adjusted returns (accounting for Brazilian IR on bond gains and coupon income)
2. Benchmark comparison (CDI, IPCA, etc.)
3. Drawdown calculations and maximum drawdown analysis
4. Multi-currency support
5. Performance attribution (contribution by bond type and coupon yield)
6. Coupon reinvestment analysis
7. Yield-to-maturity calculations including coupons
8. Scenario analysis (stress testing with different coupon rates)

## References

- Modified Dietz Method: [CFA Institute](https://www.cfainstitute.org/)
- FIFO Accounting: [IRS Publication 550](https://www.irs.gov/publications/p550)
- tddata-db returns module: `src/tddata_db/returns/`
