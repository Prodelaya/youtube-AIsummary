# Script: scripts/change_admin_password.py
from src.core.database import SessionLocal
from src.core.security import hash_password
from src.repositories.user_repository import UserRepository

db = SessionLocal()
user_repo = UserRepository(db)

admin = user_repo.get_by_username("admin")
admin.hashed_password = hash_password("NUEVA_PASSWORD_SEGURA_AQUI")  # type: ignore

db.commit()
print("✅ Password de admin actualizado")
db.close()
