from typing import Dict, List, Optional
from fastapi import FastAPI, HTTPException, Path, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
import httpx, uvicorn, json
from fastapi.middleware.cors import CORSMiddleware
from fastapi.templating import Jinja2Templates

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_methods=["*"],
    allow_headers=["*"],
)

API_HOST = "https://demo23.megaplan.ru/api/v3"
TOKEN = "ODI0MjZmZGM0Yzg0NzFiODVmMDMwYWZlN2YxZjMyODM5NzFmNzgzMzVkMDNkMzM4MGU3MmNlNmViYzJkM2Y3Mg"

# Для удобства - дефолтный ID сделки
DEFAULT_DEAL_ID = 2916

headers = {
    "Authorization": f"Bearer {TOKEN}",
    "Content-Type": "application/json"
}

# Данные для двухуровневого мультисписка
car_brands = {
    "Audi": ["A1", "A3", "Q5", "Q7"],
    "Volvo": ["XC60", "XC90", "V40", "C30"],
    "Lada": ["Vesta", "Granta", "Aura", "Priora"]
}
timeout = httpx.Timeout(20.0)
templates = Jinja2Templates(directory="templates")

# Название кастомного поля в сделке, нужно подставить из вашего API!
# В вашем примере похоже это "Category1000115CustomFieldMarkaModelAvto"
CUSTOM_FIELD_NAME = "Category1000115CustomFieldMarkaModelAvto"

async def get_deal_data(deal_id: int) -> dict:
    url = f"{API_HOST}/deal/{deal_id}"
    async with httpx.AsyncClient(timeout=timeout) as client:
        resp = await client.get(url, headers=headers)
        if resp.status_code != 200:
            print(resp.url)
            raise HTTPException(status_code=resp.status_code, detail=f"Deal load failed")
        return resp.json()["data"]  # берем корень "data"

async def update_deal_custom_field(deal_id: int, new_value: str):
    url = f"{API_HOST}/deal/{deal_id}"
    body = {
        "customFields": {
            CUSTOM_FIELD_NAME: new_value  # здесь просто строка, см. формат из ответа API
        }
    }
    async with httpx.AsyncClient() as client:
        resp = await client.put(url, json=body, headers=headers)
        if resp.status_code != 200:
            raise HTTPException(status_code=resp.status_code, detail=f"Deal update failed: {resp.text}")
        return resp.json()

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    # По дефолту редиректим на сделку DEFAULT_DEAL_ID
    return RedirectResponse(f"/deal/{DEFAULT_DEAL_ID}")

@app.get("/deal/{deal_id}", response_class=HTMLResponse)
async def show_deal(request: Request, deal_id: int = DEFAULT_DEAL_ID):
    data = await get_deal_data(deal_id)

    # Текущий кастомное поле как строка
    cur_field_value: str = data.get(CUSTOM_FIELD_NAME, "") or ""

    # Парсим для удобной формы
    selected = {}
    if cur_field_value:
        items = [item.strip() for item in cur_field_value.split(",")]
        for it in items:
            if ":" in it:
                brand, model = it.split(":", 1)
                selected.setdefault(brand.strip(), []).append(model.strip())

    return templates.TemplateResponse("deal.html", {
        "request": request,
        "deal": data,
        "car_brands": car_brands,
        "selected": selected,
        "deal_id": deal_id,
    })

@app.post("/deal/{deal_id}")
async def edit_deal(
    deal_id: int,
    request: Request,
    selected_models: Optional[List[str]] = Form(None)
):
    # Получаем полные данные сделки текущие
    deal_data = await get_deal_data(deal_id)
    # Как и ранее формируем строку значения поля
    if not selected_models:
        new_value = ""
    else:
        new_value = ", ".join(selected_models)
    # Обновляем кастомное поле в полной структуре сделки
    # Важно - копируем ключи и обсуждаем, что именно принимает API
    # if "customFields" not in deal_data or not isinstance(deal_data["customFields"], dict):
    #     deal_data["customFields"] = {}
    deal_data1 = {
        CUSTOM_FIELD_NAME: new_value
    }

    # Отправляем полностью обновленный объект сделки
    url = f"{API_HOST}/deal/{deal_id}"
    async with httpx.AsyncClient(timeout=timeout) as client:
        resp = await client.post(url, json=deal_data1, headers=headers)
        if resp.status_code != 200:
            raise HTTPException(status_code=resp.status_code, detail=f"Deal update failed: {resp.text}")

    return RedirectResponse(url=f"/deal/{deal_id}", status_code=303)


if __name__ == "__main__":
    uvicorn.run("main:app", host="localhost", port=8000, reload=True)# 37.46.133.130