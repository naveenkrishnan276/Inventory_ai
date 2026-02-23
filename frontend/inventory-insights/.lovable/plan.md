
# Inventory Intelligence Dashboard

## Overview
A production-grade, data-heavy dashboard for operations users with 4 sidebar tabs: Home, Demand, Analytics, and Reorder. Enterprise SaaS design with strong visual hierarchy, card-based layouts, and real-time API integration.

## Global Layout & Navigation
- **Left sidebar** with app logo, 4 tab navigation (Home, Demand, Analytics, Reorder), and active route indicator — collapsible to icon-only mini mode
- **Top header** with page title, last refresh timestamp, model version badge, and refresh button
- **Global filter bar** (sticky) with store, product, date range, and risk level filters — synced across tabs
- Risk color system: LOW (green), MEDIUM (yellow), HIGH (orange), CRITICAL (red)

## Tab 1: Home
- **4 KPI cards**: Total Inventory Units, At-Risk Products, Today Sales Revenue, Stockout Risk %
- **Inventory Health table** with columns: store, product, current stock, predicted daily demand, days of cover, risk level — with sticky headers
- **Risk Snapshot** donut chart showing distribution across risk levels
- **Top At-Risk Products** mini table
- **"Update Stock" quick action** button opening a modal form

## Tab 2: Demand
- **Demand trend line chart** comparing predicted vs actual demand
- **Searchable, paginated data table** of demand predictions
- **"Retrain Model" button** with optimistic spinner UI, toast notifications, and auto-polling of retrain status every 5s until completion
- **Retrain status panel** showing status, last run, model version, RMSE, R²

## Tab 3: Analytics
- **4 charts**: Sales rate trend (area), Demand rate trend (area), Reorder trend (bar), Risk distribution (donut)
- **Metric strip**: Avg Daily Sales, Avg Daily Demand, Reorder Events (7d), Critical SKU count
- **"Top Movers" table** showing fast-moving products
- **Date range switcher**: 7d / 14d / 30d toggle mapped to API query param

## Tab 4: Reorder
- **Filtered table** showing only HIGH + CRITICAL rows by default
- Columns: store, product, risk level, recommended reorder qty, seller name, seller contact, action, auto-confirm eligible, status
- **Row actions**: "Create Draft PO" (always), "Auto Confirm PO" (when eligible)
- **Bulk Draft PO** action for multi-selected rows
- **Status badges**: pending, created, confirmed, failed
- **Detail drawer** on row click with full reorder context

## Stock Update Modal (shared)
- Form fields: store_id, product_id, current_stock
- Validation for required fields and non-negative stock
- On success: close modal, toast, refresh relevant data across tabs

## API Integration
- Centralized typed API client with base URL and token configured as constants (hardcoded for frontend use)
- `x-api-token` header on every request
- React Query for caching, background refresh, and request deduplication
- All API response types defined with TypeScript interfaces
- Mock data fallback when backend is unavailable

## Design & Polish
- Enterprise SaaS aesthetic: rounded-xl cards, subtle shadows, soft borders, Tailwind design tokens only
- Skeleton loaders for all data sections, empty states, error states
- Success/error toast notifications via Sonner
- Debounced search inputs
- Keyboard-accessible controls with ARIA labels
- Desktop-optimized layout (12-column grid)

## Reusable Components
- KPI Card, Chart Card, Filter Bar, Status Badge, Risk Badge, Data Table, Empty State, Error State, Modal Form
