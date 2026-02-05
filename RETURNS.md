# Return Calculations in tddata

This document describes the return calculation functions added to the tddata package, inspired by the tddata-db returns module.

## Overview

The return calculation functions in `tddata.analytics` provide pandas-friendly implementations of:

1. **Simple Returns** - Basic percentage return calculations
2. **Annualized Returns** - Compound Annual Growth Rate (CAGR)
3. **Holding Period** - Days held for each position
4. **Operation Returns** - FIFO-matched buy/sell returns
5. **Portfolio Returns** - Modified Dietz method for time-weighted returns

## Core Functions

### Simple Return Calculation

```python
calculate_simple_return(current_value, initial_value, min_denominator=0.01)
```

Calculates simple percentage returns for pandas Series.

**Formula:** `((current_value / initial_value) - 1) * 100`

**Example:**
```python
import pandas as pd
from tddata.analytics import calculate_simple_return

prices = pd.DataFrame({
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
operations = pd.DataFrame({
    'buy_date': pd.to_datetime(['2024-01-01', '2024-06-01']),
    'sell_date': pd.to_datetime(['2024-07-01', '2024-12-01'])
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
positions = pd.DataFrame({
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
calculate_operations_returns(operations, prices, current_date=None)
```

Calculates returns for individual buy/sell operations using FIFO matching.

**Parameters:**
- `operations`: DataFrame with operation_date, bond_type, maturity_date, quantity, bond_value, operation_value, operation_type
- `prices`: DataFrame with reference_date, bond_type, maturity_date, sell_price
- `current_date`: Optional date for calculating returns (defaults to today)

**Returns:** DataFrame with:
- All original operation columns
- `status`: 'open' or 'closed'
- `holding_days`: Days held
- `sell_date`: Date sold (for closed positions)
- `sell_value`: Sale value (for closed positions)
- `current_value`: Current market value (for open positions)
- `end_value`: Final value (sell_value or current_value)
- `simple_return`: Simple percentage return
- `annualized_return`: Annualized return (CAGR)

**Example:**
```python
from tddata import reader, analytics
from tddata.constants import Column as C

# Read operations and prices
operations = reader.read_operations('operations.csv')
prices = reader.read_prices('prices.csv')

# Calculate returns
returns = analytics.calculate_operations_returns(operations, prices)

# View closed positions with positive returns
profitable = returns[
    (returns['status'] == 'closed') &
    (returns['simple_return'] > 0)
].sort_values('annualized_return', ascending=False)

print(profitable[[
    C.BOND_TYPE.value,
    C.OPERATION_DATE.value,
    'sell_date',
    'holding_days',
    'simple_return',
    'annualized_return'
]])
```

### Portfolio Monthly Returns (Modified Dietz)

```python
calculate_portfolio_monthly_returns(
    operations,
    prices,
    start_date=None,
    end_date=None
)
```

Calculates monthly portfolio returns using the Modified Dietz method, which properly accounts for the timing of cash flows.

**Modified Dietz Formula:**
```
Return = (EMV - BMV - Net_CF) / (BMV + Weighted_CF)

Where:
- EMV = Ending Market Value
- BMV = Beginning Market Value
- Net_CF = Net Cash Flow (positive for deposits, negative for withdrawals)
- Weighted_CF = Time-weighted cash flows
```

**Cash Flow Weighting:**
```
Weight = days_remaining_in_period / total_days_in_period
```

A deposit early in the month has a weight close to 1.0, while a deposit at the end has a weight close to 0.0, properly reflecting its impact on returns.

**Returns:** DataFrame with:
- `month`: Month start date
- `monthly_return`: Return for that month (%)
- `cumulative_return`: Cumulative return from start (%)
- `portfolio_value`: Portfolio value at end of month
- `net_cash_flow`: Net cash flows during month

**Example:**
```python
# Calculate monthly returns for entire portfolio
monthly = analytics.calculate_portfolio_monthly_returns(
    operations,
    prices,
    start_date=pd.Timestamp('2024-01-01'),
    end_date=pd.Timestamp('2024-12-31')
)

# Plot cumulative returns
import matplotlib.pyplot as plt

plt.figure(figsize=(12, 6))
plt.plot(monthly['month'], monthly['cumulative_return'])
plt.title('Portfolio Cumulative Return')
plt.xlabel('Month')
plt.ylabel('Cumulative Return (%)')
plt.grid(True)
plt.show()

# Summary statistics
print(f"Best month: {monthly['monthly_return'].max():.2f}%")
print(f"Worst month: {monthly['monthly_return'].min():.2f}%")
print(f"Total return: {monthly.iloc[-1]['cumulative_return']:.2f}%")
```

## Comparison with tddata-db Returns Module

The tddata implementation differs from tddata-db in the following ways:

| Feature | tddata-db | tddata |
|---------|-----------|--------|
| **Paradigm** | Object-oriented (classes) | Functional (pandas operations) |
| **FIFO Tracking** | `LotTracker` class with state | Function-based matching in operations DataFrame |
| **Portfolio** | `PortfolioTracker` class | `calculate_portfolio_monthly_returns` function |
| **Price Lookup** | `PriceLookup` class with caching | DataFrame merge operations |
| **Dependencies** | SQLAlchemy, dateutil | Pandas only (lighter) |
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

# Calculate returns for all operations
returns = analytics.calculate_operations_returns(operations, prices)

# Group by investor
investor_returns = returns.groupby('investor_id').agg({
    'operation_value': 'sum',
    'end_value': 'sum',
    'simple_return': 'mean',
    'annualized_return': 'mean'
}).reset_index()

# Find best performers
top_investors = investor_returns.nlargest(10, 'annualized_return')
```

### Pattern 2: Compare Bond Types

```python
# Calculate returns by bond type
by_type = returns.groupby('bond_type').agg({
    'simple_return': ['mean', 'median', 'std'],
    'annualized_return': ['mean', 'median'],
    'holding_days': 'mean'
}).reset_index()

print(by_type)
```

### Pattern 3: Time-Series Analysis

```python
# Monthly portfolio returns
monthly = analytics.calculate_portfolio_monthly_returns(
    operations,
    prices
)

# Rolling 12-month return
monthly['rolling_12m'] = monthly['monthly_return'].rolling(12).sum()

# Volatility (standard deviation of monthly returns)
volatility = monthly['monthly_return'].std()
print(f"Monthly volatility: {volatility:.2f}%")
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

1. **Vectorized Operations**: All calculations use pandas vectorized operations for performance
2. **Memory Efficiency**: Functions return new DataFrames without modifying input data
3. **Large Datasets**: For very large datasets, consider chunking operations

### Error Handling

The functions include safeguards:
- Division by zero protection (min_denominator parameter)
- Return capping (-100% to 1000%) to handle data anomalies
- Invalid value handling (returns 0.0 for invalid inputs)

### Data Quality

For accurate results, ensure:
- **Date Columns**: Properly parsed as pandas datetime
- **Numeric Columns**: Values are float/numeric types
- **Price Data**: Complete monthly price coverage
- **Operation Types**: Correctly coded ('C'/'D' for buys, 'V'/'R' for sells)

## Future Enhancements

Possible additions:
1. Tax-adjusted returns (accounting for Brazilian IR on bond gains)
2. Benchmark comparison (CDI, IPCA, etc.)
3. Drawdown calculations
4. Multi-currency support
5. Performance attribution (contribution by bond type)

## References

- Modified Dietz Method: [CFA Institute](https://www.cfainstitute.org/)
- FIFO Accounting: [IRS Publication 550](https://www.irs.gov/publications/p550)
- tddata-db returns module: `src/tddata_db/returns/`
