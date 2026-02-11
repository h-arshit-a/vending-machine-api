from sqlalchemy.orm import Session

from app.config import settings
from app.models import Slot
from app.schemas import SlotCreate, SlotFullView, SlotFullViewItem, SlotResponse


from sqlalchemy.exc import IntegrityError

def create_slot(db: Session, data: SlotCreate) -> Slot:
    try:
        # Check slot limit
        count = db.query(Slot).count()
        if count >= settings.MAX_SLOTS:
            raise ValueError("slot_limit_reached")

        # Create slot
        slot = Slot(code=data.code, capacity=data.capacity, current_item_count=0)
        db.add(slot)
        db.flush()  # flush changes to DB without committing

        db.commit()  # commit after all checks
        db.refresh(slot)
        return slot

    except IntegrityError as e:
        db.rollback()
        # This will catch unique constraint violation on code
        if "unique" in str(e.orig).lower():
            raise ValueError("slot_code_exists")
        raise


def list_slots(db: Session) -> list[Slot]:
    return db.query(Slot).all()


def get_slot_by_id(db: Session, slot_id: str) -> Slot | None:
    return db.query(Slot).filter(Slot.id == slot_id).first()


def delete_slot(db: Session, slot_id: str) -> None:
    slot = get_slot_by_id(db, slot_id)
    if not slot:
        raise ValueError("slot_not_found")
    db.delete(slot)
    db.commit()


def get_full_view(db: Session) -> list[SlotFullView]:
    slots = db.query(Slot).all()
    result = []
    for slot in slots:
        # slot.items loaded per slot (N+1)
        items = [
            SlotFullViewItem(
                id=item.id,
                name=item.name,
                price=item.price,
                quantity=item.quantity,
            )
            for item in slot.items
        ]
        result.append(
            SlotFullView(
                id=slot.id,
                code=slot.code,
                capacity=slot.capacity,
                items=items,
            )
        )
    return result
