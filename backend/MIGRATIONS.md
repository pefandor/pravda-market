# Database Migrations Guide

## Current State

**Development:** Tables created via `Base.metadata.create_all()` (includes all indexes)  
**Migration:** `5fa554c56c45` - Performance indexes for trade queries

## For Development (SQLite)

Tables are created automatically with all indexes on startup.
No migration needed.

## For Production (PostgreSQL)

### First Deployment:
```bash
# Option A: Create from scratch (recommended for new DB)
alembic upgrade head

# Option B: Mark existing DB as up-to-date (if tables already exist)
alembic stamp head
```

### Adding New Migrations:
```bash
# After modifying models:
alembic revision --autogenerate -m "Description of changes"

# Review the generated migration file
# Apply the migration
alembic upgrade head
```

## Important Notes

1. **Development uses init_db()** which calls `Base.metadata.create_all()`  
   - All indexes are created automatically
   - Alembic not required for local development

2. **Production should use Alembic** for schema versioning  
   - Better control over schema changes
   - Rollback capability
   - Team coordination

3. **Current Migration** adds these indexes:
   - `idx_trades_yes_order` on `trades(yes_order_id)`
   - `idx_trades_no_order` on `trades(no_order_id)`  
   - `idx_orders_matching` on `orders(market_id, side, price_bp, created_at)`

These indexes are already in models.py, so dev environment has them.
