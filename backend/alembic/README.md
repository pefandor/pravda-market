# Database Migrations with Alembic

This directory contains database migration scripts managed by Alembic.

## 🚀 Quick Start

```bash
# Apply all migrations (upgrade to latest)
alembic upgrade head

# Rollback one migration
alembic downgrade -1

# Show current migration status
alembic current

# Show migration history
alembic history --verbose
```

## 📝 Creating New Migrations

### Auto-generate from model changes:
```bash
# After modifying models in app/db/models.py:
alembic revision --autogenerate -m "Add user email field"
```

### Manual migration:
```bash
alembic revision -m "Add custom index"
# Then edit the generated file in versions/
```

## ⚠️ Important Notes

1. **Always review auto-generated migrations** before applying them
   - Alembic may not detect all changes correctly
   - Some operations (like data migrations) must be written manually

2. **Test migrations on staging before production**
   ```bash
   # Apply migration
   alembic upgrade head
   
   # Verify it works
   python -m pytest
   
   # If issues, rollback
   alembic downgrade -1
   ```

3. **Never edit applied migrations**
   - Once a migration is in production, create a new migration instead
   - Editing applied migrations breaks version history

4. **Coordinate with team**
   - Pull latest migrations before creating new ones
   - Avoid migration conflicts

## 📦 Deployment

```bash
# In production, run migrations before starting the app:
alembic upgrade head
uvicorn app.main:app
```

## 🔍 Current Schema

Initial schema (revision: 5fa554c56c45) includes:
- Performance indexes for trade queries
  - idx_trades_yes_order
  - idx_trades_no_order
  - idx_orders_matching

## 🛠️ Troubleshooting

### "Target database is not up to date"
```bash
alembic upgrade head
```

### "Can't locate revision identified by ..."
```bash
# Reset to clean state (DESTRUCTIVE!)
alembic stamp head
```

### Migration fails halfway
```bash
# Rollback to previous working state
alembic downgrade -1

# Fix the migration file
# Try again
alembic upgrade head
```
