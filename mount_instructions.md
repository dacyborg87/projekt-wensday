# Dashboard Mount Instructions

Add these lines to the existing FastAPI application file, such as `wensday_web.py` or a future `app.py`/`main.py`.

```python
from fastapi.staticfiles import StaticFiles
from dashboard_routes import router as dashboard_router

app.mount("/static", StaticFiles(directory="static"), name="static")
app.include_router(dashboard_router, prefix="")
```

If `/static` is already mounted, keep the existing mount and add only:

```python
from dashboard_routes import router as dashboard_router

app.include_router(dashboard_router, prefix="")
```
