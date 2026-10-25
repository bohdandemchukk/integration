import os
from pathlib import Path


def read_secret(name: str) -> str:
    # без fallback на env (R3.1): немає файлу - падаємо при старті
    path = Path(f"/run/secrets/{name}")
    try:
        return path.read_text().strip()
    except FileNotFoundError:
        raise RuntimeError(f"Required secret '{name}' not found at {path}")


JWT_SECRET_KEY = read_secret("jwt_secret_key")   # виконається при імпорті -> fail-fast
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))