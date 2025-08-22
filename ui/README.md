# BlackSwan Credit Intelligence Platform - Frontend

This is the Next.js frontend for the BlackSwan Credit Intelligence Platform.

## Quick Start

### Option 1: Using Docker (Recommended)
```bash
# From the root directory
./start_dashboard.sh
```

Then visit: http://localhost:3000

### Option 2: Local Development
```bash
cd ui
npm install
npm run dev
```

Then visit: http://localhost:3000

## Features

- **Real-time Dashboard**: Live credit scores for all tracked issuers
- **Score Breakdown**: Detailed component analysis (Base, Market, Events, Macro)
- **Event Timeline**: Recent news and events affecting credit scores
- **Interactive Charts**: Visual representation of score trends
- **Responsive Design**: Works on desktop, tablet, and mobile

## Pages

- **Dashboard** (`/`): Overview of all issuers with current scores
- **Issuer Detail** (`/issuer/[id]`): Detailed view of individual issuer

## API Integration

The frontend connects to the FastAPI backend at `http://localhost:8000` and polls for updates every 30 seconds.

## Tech Stack

- **Next.js 14** with App Router
- **TypeScript** for type safety
- **TailwindCSS** for styling
- **Recharts** for data visualization
- **Lucide React** for icons
- **SWR** for data fetching

## Development

```bash
# Install dependencies
npm install

# Run development server
npm run dev

# Build for production
npm run build

# Run tests
npm test

# Lint code
npm run lint
```

## Environment Variables

- `NEXT_PUBLIC_API_URL`: Backend API URL (default: http://localhost:8000)





