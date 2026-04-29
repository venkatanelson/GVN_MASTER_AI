web: gunicorn app:app --workers 1 --threads 2 --worker-class gthread --timeout 120
release: python -c "from app import app, db; app.app_context().push(); db.create_all()"
