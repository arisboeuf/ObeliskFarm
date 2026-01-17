
# ObeliskGemEV – Freebie EV README

Diese Datei dokumentiert vollständig die Erwartungswert‑Berechnung (EV) für **Freebies** im Spiel *Obelisk Idle Miner*,
inklusive aller aktuell aktiven Perks, Multiplikatoren und Sonderregeln.

Ziel: Diese README dient als **saubere Ausgangsbasis** für Weiterarbeit in einem anderen Developer‑Environment.

---

## 1. Aktuelle Spielparameter

| Parameter | Wert |
|---|---:|
| Freebie Gems (Basis) | 9 |
| Freebie Timer | 7 Minuten |
| Skill Shard Chance | 12 % |
| Skill Shard Wert | 12,5 Gems |
| Gem‑Stonks | 1 % Chance auf +200 Gems |
| Jackpot | 5 % Chance auf **5 Rolls total** |
| Jackpot‑Sonderregel | **Zusatz‑Rolls können KEINE Stonks triggern** |
| Instant Refresh | 5 %, chainable |
| Founder Drop Intervall | 60 - 2×(VIP_Lounge_Level-1) Minuten (z.B. Level 2 = 58 Minuten) |
| Founder Gems Base | 10 (immer, pro Drop) |
| Founder Gems Bonus | 1/100 Chance auf 50 + 10 × Obelisk Level |
| Obelisk Level | 26 (konfigurierbar) |
| Founder Speed | 2× für 5 Minuten (pro Drop) |
| VIP Lounge Double Drop Chance | 12% bei Level 2, +6% pro Level (Level 3 = 18%, Level 4 = 24%, etc.) |
| VIP Lounge Triple Drop Chance | 16% bei Level 7 |
| Founder Supply Drop Gift Chance | 1/1234 Chance auf 10 Gifts pro Supply Drop |
| Founder Bomb Intervall | 87 Sekunden (1:27 min) |
| Founder Bomb Speed Chance | 10 % |
| Founder Bomb Speed | 2× für 10 Sekunden |

---

## 2. Roll‑ und Claim‑Logik

### 2.1 Rolls
- Normaler Freebie‑Claim erzeugt **1 Roll**
- Jackpot: 5 % Chance → **insgesamt 5 Rolls**
- Erwartete Rolls pro Claim:
  - 0,95 × 1 + 0,05 × 5 = **1,2 Rolls**
- **Stonks nur auf der ersten Roll eines Claims**

### 2.2 Refresh‑Kette
- 5 % Chance, dass ein Claim sofort ein weiteres Freebie erzeugt
- Kann erneut refreshen (geometrische Reihe)
- Erwartete Claims pro Start‑Freebie:
  - 1 / (1 − 0,05) = **1,0526**

### 2.3 Effektiver Multiplikator
| Effekt | Faktor |
|---|---:|
| Jackpot | ×1,2 |
| Refresh | ×1,0526 |
| **Gesamt** | **×1,2632** |

---

## 3. Founder Speed‑Effekt

- Alle 58 Minuten (oder abhängig von VIP Lounge Level):
  - +10 Gems (pro Drop)
  - 2× Game Speed für 5 Minuten (pro Drop)
  
**WICHTIG: Game Speed ist immer 2× (fix)**

Bei Double/Triple Supply Drops verlängert sich nur die **Dauer** des Speed Boosts, NICHT der Speed-Multiplikator:
- Single Drop: 2× Speed für 5 Minuten
- Double Drop: 2× Speed für 10 Minuten (2 × 5 Minuten)
- Triple Drop: 2× Speed für 15 Minuten (3 × 5 Minuten)

Zeitersparnis-Berechnung:
- Bei 2× Speed: Zeitersparnis = Dauer / 2
- Single: 5 / 2 = 2,5 Minuten Zeitersparnis
- Double: 10 / 2 = 5 Minuten Zeitersparnis
- Triple: 15 / 2 = 7,5 Minuten Zeitersparnis

Der Speed‑Effekt wird **separat** als eigener EV‑Posten gerechnet.

---

## 4. EV‑Contribution pro Stunde (Gem‑Äquivalent)

Alle Werte beinhalten:
- Jackpot
- Refresh
- korrekte Stonks‑Regel
- Skill Shard‑Umrechnung
- Founder‑Effekte separat (Drop, Speed, Bomb)

| EV‑Posten | Gem‑Äq / h |
|---|---:|
| Gems (Basis aus Rolls) | 101,8 |
| Gems (Stonks EV) | 18,9 |
| Skill Shards (Gem‑Äq) | 17,0 |
| (2× Game Speed 5 min founder drop) | 5,9 |
| Founder Gems | 10,3 |
| Founder Bomb Speed Boost | [wird berechnet] |
| **Total** | **148,0+** |

---

## 5. Interpretation der Posten

### Gems (Basis)
- Fixe 9 Gems pro Roll
- Skaliert mit Jackpot + Refresh

### Gems (Stonks EV)
- Erwartungswert aus 1 % Chance auf +200 Gems
- **Nur 1 Roll pro Claim erlaubt**
- Skaliert mit Refresh, nicht mit Jackpot‑Zusatzrolls

### Skill Shards
- 12 % Chance pro Roll
- Alle Rolls inkl. Jackpot‑Rolls zählen
- Umgerechnet mit 12,5 Gems pro Shard

### (2× Game Speed 5 min founder drop)
- Reiner Zeitgewinn
- Erhöht effektiv die Anzahl Freebies pro Stunde
- Kein direkter Gem‑Drop

### Founder Gems (Supply Drop)
- Direkter Gem‑Drop alle X Minuten (abhängig von VIP Lounge Level)
- Intervall: 60 - 2×(VIP_Lounge_Level-1) Minuten
- Immer: 10 Gems pro Drop
- 1/100 Chance auf zusätzliche Gems: 50 + 10 × Obelisk Level
- Berücksichtigt Double/Triple Drops (mehr Drops = mehr Gems)
- 1/1234 Chance: 10 Gifts pro Supply Drop (mit eigenem GemEV)
- Linear auf Stundenbasis umgerechnet
- Abhängig vom Obelisk Level (konfigurierbar im GUI)

### Founder Speed Boost (vom Supply Drop)
- Kommt vom Founder Supply Drop
- 2× Game Speed für 5 Minuten **pro Drop**
- Bei Double Drop: 2× Speed für 10 Minuten (Dauer verlängert sich, Speed bleibt 2×)
- Bei Triple Drop: 2× Speed für 15 Minuten (Dauer verlängert sich, Speed bleibt 2×)
- Zeitersparnis = (Dauer mit Speed) / 2

### Founder Bomb Speed Boost
- 1 Bomb alle 87 Sekunden (1:27 min)
- 10% Chance auf 2× Game Speed für 10 Sekunden
- Reiner Zeitgewinn durch Speed-Boost
- Erhöht effektiv die Anzahl Freebies pro Stunde
- Kein direkter Gem‑Drop

---

## 6. Ergebnis

Aktueller Gesamt‑Ertrag:
- **≈ 148,0 Gems‑Äquivalent pro Stunde**
- Unter Annahme: konsequentes Claiming

Diese Datei bildet die **Referenzversion** für alle weiteren Optimierungs‑,
Upgrade‑ oder Vergleichsrechnungen.

---
