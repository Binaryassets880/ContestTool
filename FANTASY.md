# Grand Arena Fantasy Point System

## Overview

This document explains the fantasy point scoring system used in Grand Arena contests. Players build lineups of 4 champions + 1 scheme card, and total fantasy points determine contest placement.

## Scoring Formula

| Stat | Points |
|------|--------|
| **Eliminations** | 80 pts each |
| **Deposits** | 50 pts each |
| **Wart Distance** | 45 pts per 80 units (0.5625 pts/unit) |
| **Victory** | 300 pts |

**Total Fantasy Points** = (Elims × 80) + (Deps × 50) + (Wart × 0.5625) + (300 if won)

## Key Concepts

### Only Champions Score

Only the 4 champions in your lineup score fantasy points. Supporters do NOT directly contribute to your fantasy score.

However, supporters are crucial because:
- They help your champion WIN (worth 300 pts!)
- They can eliminate opponent champions
- They contribute to gacha deposits and wart distance

### The Victory Bonus is Huge

The 300-point victory bonus is often the largest single contributor to a champion's fantasy score. This means:

- A champion with 70% win probability (MS 70) expects ~210 pts from wins alone
- A champion with 50% win probability (MS 50) expects ~150 pts from wins
- Prioritizing high Matchup Scores directly boosts expected fantasy output

### Projected vs Actual

| Type | Description |
|------|-------------|
| **Projected FP** | Based on career averages + win probability from Matchup Score |
| **Actual FP** | Based on actual game performance |

**Projection Formula:**
```
Projected FP = (Avg Elims × 80) + (Avg Deps × 50) + (Avg Wart × 0.5625) + (MS/100 × 300)
```

## Fantasy Point Tiers

| Tier | FP Range | Description |
|------|----------|-------------|
| **Elite** | 500+ | Outstanding performance with a win |
| **Strong** | 400-499 | Above average game |
| **Average** | 300-399 | Typical performance (often a win + moderate stats) |
| **Below Avg** | <300 | Likely a loss or very low stats |

## Lineup Strategy

### 1. Prioritize Win Probability

Since the victory bonus is 300 pts, focus on champions with high Matchup Scores:
- MS 60+ = "Favorable" matchups (60%+ win chance)
- MS 50-59 = "Even" matchups (coin flip)
- MS <40 = "Tough" matchups (uphill battle)

### 2. Look for Stat Monsters

Some champions consistently score high eliminations or deposits regardless of win/loss. These provide floor value even in losses.

### 3. Balance Risk and Reward

- **Safe plays**: Champions with high base win rates and consistent stats
- **Upside plays**: Champions in favorable matchups who could pop off
- **Avoid**: Champions in tough matchups unless their stat floor is high

### 4. Consider Number of Games

Champions with more scheduled games = more opportunities to score. A champion with 10 games at MS 55 may outscore one with 5 games at MS 65.

### 5. Target Lineup Win Rate

For contests, aim for ~60% lineup win rate across your 4 champions:
- Average MS of 60+ across champions
- Expected 2.4+ wins per contest block
- This balances floor (stat points) with ceiling (win bonuses)

## Example Calculation

**Champion: "Striker Steve"**
- Career Avg: 1.5 elims, 2.0 deps, 60 wart distance
- Matchup Score: 65 (65% win probability)

**Projected FP:**
```
Stats: (1.5 × 80) + (2.0 × 50) + (60 × 0.5625) = 120 + 100 + 33.75 = 253.75
Wins:  (65/100) × 300 = 195
Total: 253.75 + 195 = 448.75 projected FP
```

**If Steve wins with 2 elims, 3 deps, 80 wart:**
```
Actual: (2 × 80) + (3 × 50) + (80 × 0.5625) + 300 = 160 + 150 + 45 + 300 = 655 FP
```

## Data Sources

- **Career averages**: From cumulative stats feed (updated hourly)
- **Win probability**: From Matchup Score calculation
- **Historical performance**: From match partition feed
