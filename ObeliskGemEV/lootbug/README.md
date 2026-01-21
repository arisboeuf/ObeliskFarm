# Option Analyzer (Lootbug)

Analyzes whether specific gem purchases are worth it based on your current EV/h in Idle Obelisk Miner.

## Features

- **Purchase Analysis**: Calculate if gem purchases provide positive returns
- **Real-Time EV Integration**: Uses your current EV/h from the main calculator
- **Detailed Breakdown**: Shows affected income sources, gains, and net profit

## Module Structure

```
lootbug/
├── __init__.py    # Module exports
├── README.md      # This documentation
└── analyzer.py    # Option analysis window
```

## Currently Supported Options

### 2x Game Speed

**Cost**: 15 Gems
**Duration**: 10 minutes

With 2x Game Speed active, you effectively collect 20 minutes worth of affected income in 10 real minutes.

**Affected by 2x Speed**:
- Gems (Base) - freebie timer runs 2x faster
- Stonks - freebie-based
- Skill Shards - freebie-based
- Gem Bomb - recharge time halved
- Founder Bomb - recharge time halved

**NOT affected**:
- Founder Supply Drop - time-based, independent of game speed

### Calculation

```
additional_gain = affected_ev_per_hour x (20/60 - 10/60)
                = affected_ev_per_hour x (10/60)
                = affected_ev_per_hour / 6

profit = additional_gain - 15 gems

worth_it = profit > 0
```

This means 2x Speed is worth it when your affected EV/h > 90 Gems/h.

## Usage

1. Configure your parameters in the main ObeliskGemEV Calculator
2. Click the Lootbug button to open the Option Analyzer
3. View the analysis for each purchase option

The analyzer automatically uses your current EV values, so results update as you change parameters in the main calculator.

## Technical Notes

The analyzer receives a reference to the FreebieEVCalculator from the main GUI, allowing it to access all current EV calculations without duplicating logic.

## Future Options

Additional purchase options may be added as they become relevant:
- Other gem shop items
- Event-specific purchases
- Premium upgrades
