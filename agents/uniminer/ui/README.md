# UniMiner UI

University research application with data validation, gap-filling, and ES ingestion.

## Development

```bash
npm install
npm run dev
```

## Build & Deploy

```bash
npm run build
firebase deploy --only hosting
```

## Features

- Research any university using the collector agent
- Data quality report with field-level validation
- Gap filling via College Scorecard API
- ES comparison with existing data
- Approval workflow for ingestion
