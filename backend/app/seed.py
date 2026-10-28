"""Idempotently create M0 demonstration accounts."""
from sqlalchemy import select

from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models.role import Role
from app.models.user import User

DEMO_PASSWORD = "M0DemoPass!2026"
DEMO_ACCOUNTS = (("admin", "平台管理员", "ADMIN"), ("teacher", "演示教师", "TEACHER"), ("student", "演示学生", "STUDENT"))
ROLE_NAMES = {"ADMIN": "管理员", "TEACHER": "教师", "STUDENT": "学生"}


def seed() -> None:
    with SessionLocal.begin() as db:
        roles: dict[str, Role] = {}
        for code, name in ROLE_NAMES.items():
            role = db.scalar(select(Role).where(Role.code == code))
            if role is None:
                role = Role(code=code, name=name)
                db.add(role)
                db.flush()
            roles[code] = role
        for username, display_name, role_code in DEMO_ACCOUNTS:
            user = db.scalar(select(User).where(User.username == username))
            if user is None:
                user = User(username=username, display_name=display_name, password_hash=hash_password(DEMO_PASSWORD))
                user.roles.append(roles[role_code])
                db.add(user)
            elif roles[role_code] not in user.roles:
                user.roles.append(roles[role_code])


if __name__ == "__main__":
    seed()
    print("Demo users are ready.")
