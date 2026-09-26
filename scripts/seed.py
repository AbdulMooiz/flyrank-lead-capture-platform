from sqlalchemy import select

from app.core.security import hash_password
from app.db.models import Tenant, User, Widget
from app.db.session import SessionLocal


def seed() -> None:
    db = SessionLocal()
    try:
        if db.scalar(select(User).where(User.email == "demo@flyrank.local")):
            print("Demo data already exists")
            return
        first = Tenant(name="Demo Agency")
        second = Tenant(name="Second Demo Tenant")
        db.add_all([first, second])
        db.flush()
        db.add_all([
            User(email="demo@flyrank.local", password_hash=hash_password("DemoPass123!"), tenant_id=first.id),
            User(email="second@flyrank.local", password_hash=hash_password("DemoPass123!"), tenant_id=second.id),
            Widget(tenant_id=first.id, type="signup", title="Join the list", description="Get product updates.", fields=[{"name":"name","label":"Name","type":"text","required":True},{"name":"email","label":"Email","type":"email","required":True}], button_text="Subscribe", display_options={}),
            Widget(tenant_id=second.id, type="contact", title="Contact us", description="Send a message.", fields=[{"name":"email","label":"Email","type":"email","required":True},{"name":"message","label":"Message","type":"text","required":True}], button_text="Send", display_options={}),
        ])
        db.commit()
        print("Seeded demo@flyrank.local and second@flyrank.local with password DemoPass123!")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
