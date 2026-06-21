# 1. Python-ning eng so'nggi va barqaror LTS versiyasidan foydalanamiz
FROM python:3.11-slim

# 2. Konteyner ichidagi ishchi katalogni belgilaymiz
WORKDIR /app

# 3. Tizim paketlarini yangilaymiz va kerakli qo'shimchalarni o'rnatamiz
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# 4. Bog'liqliklar ro'yxatini konteynerga nusxalaymiz
COPY requirements.txt .

# 5. Python kutubxonalarini o'rnatamiz
RUN pip install --no-cache-dir -r requirements.txt

# 6. Loyihadagi barcha fayllarni konteyner ichiga nusxalaymiz
COPY . .

# 7. Botni ishga tushirish buyrug'i
CMD ["python", "botsibrat.py"]
