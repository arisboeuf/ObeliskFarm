# ObeliskFarm Web

Web-based calculator toolkit for **Idle Obelisk Miner**, focused on **Monte Carlo simulators** that optimize skill point and upgrade distributions.

## Core Features

- **Archaeology Simulator**: MC optimizer for skill point distribution (max stage, XP/hour, fragments/hour)
- **Event Budget Optimizer**: Guided MC optimizer for event upgrade planning
- **Gem EV Calculator**: Gem-equivalent per hour from freebies
- **Stargazing Calculator**: Stars/hour calculations (online/offline)

## Local Development

Prerequisite: Install Node.js (LTS).

```bash
cd web
npm install
npm run dev
```

Then open the URL shown in the terminal (usually `http://localhost:5173`).

## Notes

- Saves are stored automatically in the browser (`localStorage`).
- All calculations run client-side (no server required).

