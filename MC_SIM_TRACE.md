# Monte Carlo Simulation Run - Schritt-für-Schritt Ablauf

## Beispiel: Stage Rushing Simulation bei starting_floor = 5

### 1. Initialisierung in `run_sim()` (simulator.py ~5035)
```
starting_floor = self.current_stage  # z.B. 5
num_simulations = 1000
results_with_crit = []
results_without_crit = []
```

### 2. Für jede Simulation (1000x):
```
for i in range(num_simulations):  # z.B. i=0
```

### 3. WITH CRIT Simulation - Ein Run:
```
max_stage_reached_crit = starting_floor  # = 5
runs_per_hour = 60  # Beispiel

for run in range(runs_per_hour):  # z.B. run=0
    floors = simulator.simulate_run(
        mc_stats_with_crit, 
        starting_floor=5,  # <-- WICHTIG: Jeder Run startet bei 5!
        use_crit=True,
        enrage_enabled=enrage_enabled,
        flurry_enabled=flurry_enabled
    )
```

### 4. In `simulate_run()` (monte_carlo_crit.py ~147):
```
current_floor = starting_floor  # = 5
floors_cleared = 0
stamina_remaining = max_stamina  # z.B. 100

# Loop über Floors:
for _ in range(1000):  # Max safety
    # Floor 5 simulieren:
    spawn_rates = get_normalized_spawn_rates(5)
    block_mix = get_block_mix_for_floor(5)
    
    stamina_for_floor = 0
    for _ in range(BLOCKS_PER_FLOOR):  # 15 Blöcke
        # Zufällig Block spawnen basierend auf spawn_rates
        # Block töten, hits berechnen
        stamina_for_floor += hits
    
    # Kann ich Floor 5 schaffen?
    if stamina_remaining >= stamina_for_floor:
        stamina_remaining -= stamina_for_floor
        floors_cleared += 1  # = 1
        current_floor += 1   # = 6
        # Weiter mit Floor 6...
    else:
        # Partial floor
        floors_cleared += stamina_remaining / stamina_for_floor
        break

return floors_cleared  # z.B. 1.0 (wenn Floor 5 geschafft)
```

### 5. Zurück in `run_sim()` - Max Stage berechnen:
```
floors = 1.0  # Beispiel: Floor 5 wurde geschafft

# Berechnung:
if floors >= 1.0:
    floors_cleared_int = int(math.floor(floors))  # = 1
    current_stage_after_run = starting_floor + floors_cleared_int
    # = 5 + 1 = 6
else:
    current_stage_after_run = starting_floor  # = 5

max_stage_reached_crit = max(max_stage_reached_crit, current_stage_after_run)
# = max(5, 6) = 6
```

### 6. Problem-Identifikation:

**PROBLEM 1: Jeder Run startet bei starting_floor**
- Wenn `starting_floor = 5` und man gerade erst Stage 5 erreicht hat
- Dann sollte man in den meisten Runs 0 Floors schaffen (bleibt bei 5)
- Aber die Simulation zeigt fast immer Stage 6, was bedeutet, dass fast immer 1 Floor geschafft wird

**Mögliche Ursachen:**
1. `simulate_run` ist zu optimistisch (Stats zu gut?)
2. Block-Schwierigkeit bei Stage 5 ist zu niedrig
3. `starting_floor` wird falsch gesetzt (sollte vielleicht `starting_floor - 1` sein?)
4. Die Berechnung `starting_floor + floors_cleared` ist falsch

**PROBLEM 2: Logik-Frage**
- Wenn man bei Stage 5 startet und 1 Floor schafft:
  - Hat man Floor 5 geschafft → ist jetzt bei Stage 6 ✓
  - Oder hat man Floor 6 geschafft → ist jetzt bei Stage 7 ✗

**Die aktuelle Logik:**
- `current_floor = starting_floor` (5)
- Wenn man Floor 5 schafft: `current_floor += 1` (6)
- `floors_cleared = 1`
- Return: `floors_cleared = 1`
- Berechnung: `max_stage = 5 + 1 = 6` ✓

**Das sollte korrekt sein!**

### 7. Debugging-Strategie:

**Ich habe Debug-Ausgaben hinzugefügt, die in der Konsole erscheinen:**
- Zeigt die ersten 3 Runs der ersten Simulation
- Zeigt: `starting_floor`, `floors_returned`, `calculated_max_stage`

**Mögliche Probleme:**

1. **`simulate_run` gibt zu hohe Werte zurück:**
   - Wenn `starting_floor = 5` und man gerade erst Stage 5 erreicht hat
   - Sollte `floors_cleared` meist 0 sein, nicht 1
   - **Ursache könnte sein:** Stats zu gut, Block-Schwierigkeit zu niedrig

2. **Stats zu optimistisch:**
   - `max_stamina` zu hoch?
   - `total_damage` zu hoch?
   - `crit_chance` zu hoch?
   - **Prüfe:** Werden die Stats vom Planner korrekt übernommen?

3. **Block-Schwierigkeit:**
   - Sind die Blöcke bei Stage 5 zu leicht?
   - Wird `get_block_mix_for_floor(5)` korrekt aufgerufen?
   - **Prüfe:** Welche Block-Types spawnen bei Stage 5?

4. **Berechnung:**
   - Wird `starting_floor` korrekt gesetzt?
   - Ist `self.current_stage` korrekt?
   - **Prüfe:** Was ist der Wert von `self.current_stage`?

5. **Logik-Fehler:**
   - Wenn man bei Stage 5 startet und 1 Floor schafft:
     - Aktuelle Logik: `max_stage = 5 + 1 = 6` ✓
     - Aber vielleicht sollte es sein: `max_stage = 5` (weil man nur Floor 5 geschafft hat, nicht Floor 6)?
   - **Frage:** Was bedeutet "Stage 5 erreicht"? 
     - Hat man Floor 5 geschafft und ist jetzt bei Stage 6?
     - Oder ist man gerade bei Stage 5 angekommen?

**Nächste Schritte:**
1. Führe die Simulation aus und schaue die Debug-Ausgaben in der Konsole
2. Prüfe, was `floors_returned` tatsächlich ist
3. Prüfe, ob die Stats realistisch sind
4. Prüfe, ob die Block-Schwierigkeit korrekt ist
