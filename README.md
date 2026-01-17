# ObeliskGemEV Calculator 🎮

Ein interaktives GUI-Tool zur Berechnung des **Erwartungswertes (EV)** für Freebies im Android-Spiel **Idle Obelisk Miner**.

## 📋 Übersicht

Der ObeliskGemEV Calculator hilft dir dabei, den optimalen Ertrag aus den verschiedenen Freebie-Mechanismen im Spiel zu berechnen. Das Tool berechnet automatisch den **Gem-Äquivalent-Wert pro Stunde** basierend auf allen aktiven Spielmechaniken wie Jackpots, Refresh-Chains, Skill Shards, Founder-Drops und mehr.

### Was wird berechnet?

- **Gesamt-EV pro Stunde** in Gems-Äquivalent
- **Individuelle Contributions** aller Freebie-Quellen
- **Gift-EV** (Erwartungswert pro geöffnetem Gift)
- **Multiplikatoren** (Rolls, Refresh, Gesamt)
- **Visuelle Darstellung** aller Contributions als Bar Chart

## 🎯 Hauptfunktionalitäten

### 🎁 **FREEBIE-Parameter**

Steuert die Basis-Freebie-Mechanik:
- **Freebie Gems (Basis)**: Basis-Gems pro Roll (Standard: 9.0)
- **Freebie Timer**: Zeit zwischen Freebies in Minuten (Standard: 7.0)
- **Skill Shards**: Chance (12%) und Wert (12.5 Gems) pro Shard
- **Stonks**: Aktivierung/Deaktivierung des Stonks-Bonus (1% Chance auf +200 Gems)
- **Jackpot**: Chance (5%) und Anzahl zusätzlicher Rolls (Standard: 5)
- **Instant Refresh**: Chance (5%) auf sofortiges Refresh (chainable)

### 📦 **FOUNDER SUPPLY DROP**

Berechnet den Ertrag aus Founder-Supply-Drops:
- **VIP Lounge Level** (1-7): Bestimmt automatisch:
  - Drop-Intervall: `60 - 2×(Level-1)` Minuten
  - Double Drop Chance: 12% bei Level 2, +6% pro Level
  - Triple Drop Chance: 16% bei Level 7
- **Obelisk Level**: Wird für Bonus-Gem-Berechnungen verwendet (Standard: 26)
- **Founder Gems**: Fix 10 Gems pro Drop + 1/100 Chance auf Bonus-Gems
- **Founder Speed Boost**: 2× Game Speed für 5 Minuten pro Drop (spart Zeit → mehr Freebies)
- **Gift-Chance**: 1/1234 Chance auf 10 Gifts pro Supply Drop

### 💣 **FOUNDER BOMB**

Berechnet den Speed-Boost durch Founder-Bombs:
- **Bomb Intervall**: Zeit zwischen Bombs in Sekunden (Standard: 87.0 = 1:27 min)
- **Bomb Speed**: 10% Chance auf 2× Game Speed für 10 Sekunden
- Rein zeitbasiert: Spart Zeit → erhöht effektiv die Anzahl der Freebies pro Stunde

## 🖥️ GUI-Features

### Live-Updates
- **Automatische Berechnung**: Alle Werte werden sofort aktualisiert, sobald du einen Parameter änderst
- **Echtzeit-Visualisierung**: Bar Chart zeigt alle Contributions in Echtzeit

### Interaktive Tooltips
- **❓ Icons**: Hover über die Fragezeichen-Icons für detaillierte Informationen zu jedem Bereich
- **Gift-EV Tooltip**: Zeigt detaillierte Breakdown aller Gift-Contributions beim Hover

### Visualisierung
- **Bar Chart**: Zeigt alle EV-Contributions visuell an (erfordert Matplotlib)
  - Horizontale Balken für jeden EV-Posten
  - Farbcodierung: Unterschiedliche Farben für Freebie (Blau), Founder (Grün) und Bomb (Rot)
  - Hilft beim schnellen Vergleich der relativen Wichtigkeit jeder Ertragsquelle

### Ergebnis-Übersicht
- **Multiplikatoren**: Erwartete Rolls, Refresh-Multiplikator, Gesamt-Multiplikator
- **EV-Contributions**: Detaillierter Breakdown aller einzelnen Ertragsquellen
- **Total-EV**: Gesamt-Gem-Äquivalent pro Stunde (fett hervorgehoben)
- **Gift-EV**: Separater Erwartungswert pro geöffnetem Gift

## 🚀 Installation & Start

### Voraussetzungen

```bash
cd ObeliskGemEV
pip install -r requirements.txt
```

### Starten der GUI

**Windows:**
```bash
cd ObeliskGemEV
start_gui.bat
```

**Linux/macOS:**
```bash
cd ObeliskGemEV
python gui.py
```

Oder direkt:
```bash
python ObeliskGemEV/gui.py
```

## 📊 Beispiel-Output

Bei Standard-Parametern erhältst du etwa:

```
Erwartete Rolls pro Claim:     1.2000
Refresh-Multiplikator:          1.0526
Gesamt-Multiplikator:           1.2632

TOTAL:                          148.0 Gems-Äq/h

Gift-EV (pro 1 geöffneten Gift):  XX.XX Gems-Äq
```

## 🔧 Technische Details

### Berechnete EV-Contributions

1. **Gems (Basis aus Rolls)**: Basis-9-Gems × Multiplikatoren
2. **Gems (Stonks EV)**: Erwartungswert aus Stonks (nur erste Roll)
3. **Skill Shards (Gem-Äq)**: Shard-Chance × Shard-Wert × Multiplikatoren
4. **Founder Speed Boost**: Zeitersparnis durch 2× Speed → mehr Freebies → Gem-Äquivalent
5. **Founder Gems**: Direkte Gem-Drops aus Supply Drops (inkl. Double/Triple Drops)
6. **Founder Bomb Boost**: Zeitersparnis durch Bomb-Speed-Boosts

### Multiplikatoren

- **Jackpot**: Durchschnittlich 1.2 Rolls pro Claim (95% × 1 + 5% × 5)
- **Refresh**: Geometrische Reihe → 1/(1-0.05) = 1.0526 Claims pro Start-Freebie
- **Gesamt**: Jackpot × Refresh = 1.2632

### Speed-Boost-Berechnung

Speed-Boosts sparen Zeit, was effektiv mehr Freebies pro Stunde ermöglicht:
- **Founder Speed**: 2× Speed für 5-15 Minuten (je nach Single/Double/Triple Drop)
- **Bomb Speed**: 2× Speed für 10 Sekunden bei 10% Chance

Die Zeitersparnis wird in zusätzliche Freebies umgerechnet und als Gem-Äquivalent dargestellt.

## 📝 Hinweise

- Alle Werte sind **pro Stunde** und in **Gems-Äquivalent**
- Die Berechnungen basieren auf den aktuellen Spielmechaniken (Stand: siehe Code)
- Parameter können jederzeit angepasst werden, falls sich Spielwerte ändern
- **Stonks** kann über Checkbox aktiviert/deaktiviert werden (für Tests/Vergleiche)

## 📄 Lizenz

Für den persönlichen Gebrauch beim Spielen von Idle Obelisk Miner.

---

**Viel Erfolg beim Optimieren deines Freebie-Ertrags! 🎉**
