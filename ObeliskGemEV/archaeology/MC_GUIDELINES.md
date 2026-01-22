# Monte Carlo Simulation Guidelines

Dieses Dokument beschreibt die Regeln, Prinzipien und Best Practices für Monte Carlo Simulationen im Archaeology Simulator.

## Grundprinzipien

### 1. Was ist eine Monte Carlo Simulation?

Eine Monte Carlo Simulation verwendet **Zufall** und **Wiederholung**, um die **Varianz** und **Verteilung** von Ergebnissen zu verstehen, die durch RNG (Random Number Generation) beeinflusst werden.

**Wichtig**: MC Simulationen sind NICHT für deterministische Berechnungen gedacht. Sie sind für:
- ✅ Vergleich von Strategien mit unterschiedlichen Skillungen
- ✅ Verstehen der Varianz (wie stark schwanken die Ergebnisse?)
- ✅ Statistische Signifikanz-Tests (ist Unterschied A vs. B zufällig oder real?)
- ❌ NICHT für: "Wie viele Floors schaffe ich genau?" (dafür gibt es die deterministische Berechnung)

### 2. Wann MC verwenden?

**Verwende MC Simulationen wenn:**
- Du zwei verschiedene Builds/Strategien vergleichen willst (z.B. mit vs. ohne Crit)
- Du die Varianz verstehen willst (wie konsistent sind die Ergebnisse?)
- Du statistische Tests brauchst (ist ein Unterschied signifikant?)

**Verwende NICHT MC wenn:**
- Du nur die erwartete Performance wissen willst (dafür: deterministische Berechnung)
- Du eine schnelle Antwort brauchst (MC braucht Zeit für 1000+ Simulationen)
- Die Frage deterministisch beantwortet werden kann

## MC Stage Pusher - Spezifische Regeln

### 3. Zwei Simulationen für Vergleich

**Regel**: Der MC Stage Pusher führt IMMER zwei Simulationen durch:
1. **Ohne Crit**: Skillung basierend auf `calculate_forecast()` mit `crit_calc_enabled=False`
2. **Mit Crit**: Skillung basierend auf `calculate_forecast()` mit `crit_calc_enabled=True`

**Warum?**
- Die optimale Skillung ändert sich je nachdem, ob Crit berücksichtigt wird
- Mit Crit: Mehr Luck/Agility (für Crit Chance)
- Ohne Crit: Mehr Strength (für direkten Damage)

**Wichtig**: Beide Simulationen verwenden die **gleichen** Settings:
- Gleicher `starting_floor` (immer 1 für Stage Pusher)
- Gleiche `enrage_enabled` und `flurry_enabled` Settings
- Gleiche `block_cards` (falls vorhanden)
- Gleiche Anzahl Simulationen (1000)

### 4. Starting Floor = 1

**Regel**: MC Stage Pusher startet IMMER bei Floor 1.

**Warum?**
- Unbiased: Jeder Build startet bei den gleichen Bedingungen
- Vergleichbar: Unterschiede kommen nur von Build-Unterschieden, nicht von unterschiedlichen Startpunkten
- Realistisch: Stage Pusher bedeutet "wie weit kommst du von Anfang an?"

**NICHT verwenden**: `self.current_stage` oder andere dynamische Startpunkte für Stage Pusher.

### 5. Rohdaten sammeln

**Regel**: Sammle IMMER die Rohdaten (Liste von max_stage Werten), nicht nur aggregierte Counts.

**Warum?**
- Für statistische Tests brauchst du die Rohdaten
- Histogramme können aus Rohdaten erstellt werden
- Aggregierte Counts reichen nicht für Tests

**Implementierung:**
```python
raw_data_no_crit = []  # Liste von max_stage Werten
raw_data_with_crit = []

for i in range(1000):
    result = simulator.simulate_run(...)
    max_stage = int(result['max_stage_reached'])
    raw_data_no_crit.append(max_stage)  # Rohdaten speichern
    stage_counts_no_crit[max_stage] += 1  # Für Histogramm
```

### 6. Keine Debug-Prints

**Regel**: MC Simulationen sollen KEINE Debug-Prints haben.

**Warum?**
- MC läuft im Hintergrund-Thread
- Prints blockieren die UI nicht, aber sind unnötig
- Ergebnisse werden im GUI angezeigt

**Ausnahme**: Nur wenn explizit Debug-Modus aktiviert ist (z.B. für Entwicklung).

## Statistische Tests

### 7. Mann-Whitney U-Test

**Regel**: Verwende den Mann-Whitney U-Test für Vergleiche.

**Warum?**
- Nicht-parametrisch: Funktioniert auch bei nicht-normalverteilten Daten
- Robust: Weniger anfällig für Ausreißer
- Geeignet für: Vergleich von zwei unabhängigen Gruppen

**Interpretation:**
- **p < 0.001**: Hoch signifikant (`***`)
- **p < 0.01**: Sehr signifikant (`**`)
- **p < 0.05**: Signifikant (`*`)
- **p >= 0.05**: Kein signifikanter Unterschied

**Wichtig**: Signifikanz bedeutet NICHT "großer Unterschied", sondern "Unterschied ist wahrscheinlich nicht zufällig".

### 8. Deskriptive Statistiken anzeigen

**Regel**: Zeige IMMER Mean, Median und Differenz an.

**Warum?**
- **Mean**: Durchschnitt (kann durch Ausreißer beeinflusst werden)
- **Median**: Robust gegen Ausreißer
- **Differenz**: Praktische Relevanz (wie viel besser ist es wirklich?)

**Beispiel:**
```
Mean Stage Reached:
  No Crit:    5.2 (median: 5.0)
  With Crit:  5.8 (median: 6.0)
  Difference: 0.6 stages (+11.5%)
```

## Code-Organisation

### 9. Threading

**Regel**: MC Simulationen laufen IMMER in einem separaten Thread.

**Warum?**
- UI bleibt responsiv
- Lange Simulationen blockieren nicht die Anwendung
- Benutzer kann andere Dinge tun während Simulation läuft

**Implementierung:**
```python
def run_mc_stage_pusher(self):
    def run_in_thread():
        # Lange Simulation hier
        ...
        # Ergebnis im Main-Thread anzeigen
        self.window.after(0, lambda: self._show_results(...))
    
    thread = threading.Thread(target=run_in_thread, daemon=True)
    thread.start()
```

### 10. Ergebnis-Anzeige

**Regel**: Ergebnisse werden im Main-Thread angezeigt (via `window.after()`).

**Warum?**
- Tkinter ist nicht thread-safe
- GUI-Updates müssen im Main-Thread passieren
- `window.after(0, ...)` führt Code im Main-Thread aus

### 11. Fehlerbehandlung

**Regel**: Handle fehlende Dependencies gracefully.

**Implementierung:**
```python
try:
    from scipy import stats
    SCIPY_AVAILABLE = True
except ImportError:
    SCIPY_AVAILABLE = False
    # Zeige Nachricht, aber crashe nicht
```

**Warum?**
- Nicht alle Benutzer haben scipy installiert
- App soll auch ohne optional Dependencies funktionieren
- Zeige hilfreiche Nachricht statt Crash

## Histogramm-Darstellung

### 12. Zwei Histogramme nebeneinander

**Regel**: Zeige beide Simulationen nebeneinander für direkten Vergleich.

**Warum?**
- Visueller Vergleich ist einfacher
- Gleiche Y-Achsen-Skalierung für fairen Vergleich
- Unterschiede sind sofort sichtbar

### 13. Gleiche Y-Achsen-Skalierung

**Regel**: Beide Histogramme verwenden die gleiche Y-Achsen-Skalierung.

**Warum?**
- Fairer Vergleich
- Unterschiede in der Höhe sind echte Unterschiede, nicht Skalierungs-Artefakte

**Implementierung:**
```python
max_count = max(all_counts)  # Max aus beiden Datensätzen
ax1.set_ylim(0, max_count * 1.1)
ax2.set_ylim(0, max_count * 1.1)  # Gleiche Skalierung
```

### 14. Labels auf Bars

**Regel**: Zeige Count und Prozent auf jedem Bar.

**Warum?**
- Präzise Information
- Prozent macht relative Häufigkeit klar
- Count zeigt absolute Anzahl

## Häufige Fehler vermeiden

### 15. ❌ Falsch: Starting Floor aus current_stage

```python
# FALSCH für Stage Pusher:
starting_floor = self.current_stage  # ❌
```

**Warum falsch?**
- Verschiedene Builds würden bei verschiedenen Floors starten
- Vergleich ist nicht fair
- Stage Pusher bedeutet "von Anfang an"

**✅ Richtig:**
```python
starting_floor = 1  # ✅ Immer 1 für Stage Pusher
```

### 16. ❌ Falsch: Nur Counts, keine Rohdaten

```python
# FALSCH:
stage_counts[stage] += 1  # Nur Counts
# Keine Rohdaten für statistische Tests
```

**✅ Richtig:**
```python
raw_data.append(max_stage)  # Rohdaten
stage_counts[max_stage] += 1  # Für Histogramm
```

### 17. ❌ Falsch: Gleiche Skillung für beide Simulationen

```python
# FALSCH:
forecast = self.calculate_forecast(num_points)  # Nur einmal
# Verwende gleiche Skillung für beide
```

**✅ Richtig:**
```python
# Ohne Crit:
self.crit_calc_enabled.set(False)
forecast_no_crit = self.calculate_forecast(num_points)

# Mit Crit:
self.crit_calc_enabled.set(True)
forecast_with_crit = self.calculate_forecast(num_points)
```

### 18. ❌ Falsch: Debug-Prints in Production

```python
# FALSCH:
print(f"Running simulation {i}...")  # ❌
```

**✅ Richtig:**
```python
# Keine Prints, oder nur bei Debug-Modus:
if debug:
    print(f"Running simulation {i}...")
```

## Zusammenfassung: Checkliste

Wenn du eine neue MC Simulation implementierst:

- [ ] Läuft in separatem Thread?
- [ ] Ergebnisse werden im Main-Thread angezeigt?
- [ ] Rohdaten werden gesammelt (nicht nur Counts)?
- [ ] Starting Floor ist konsistent (1 für Stage Pusher)?
- [ ] Beide Simulationen verwenden korrekte Skillungen?
- [ ] Statistische Tests werden durchgeführt (falls scipy verfügbar)?
- [ ] Histogramme haben gleiche Y-Achsen-Skalierung?
- [ ] Keine Debug-Prints (außer Debug-Modus)?
- [ ] Fehlerbehandlung für fehlende Dependencies?
- [ ] Deskriptive Statistiken werden angezeigt?

## Weitere Ressourcen

- `monte_carlo_crit.py`: Implementierung der MC Simulation Engine
- `simulator.py`: MC Stage Pusher GUI Integration
- `README.md`: Allgemeine Archaeology Dokumentation
