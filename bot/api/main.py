from fastapi import FastAPI
#from api.routes import geocoding
from api.routes import static_data

app = FastAPI(title="Geo API")

# Подключаем маршруты
#app.include_router(geocoding.router)

app.include_router(static_data.router, prefix="/api")
