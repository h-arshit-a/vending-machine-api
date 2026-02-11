import time
from sqlalchemy.orm import Session

from app.config import settings
from app.models import Item, Slot
from app.schemas import ItemBulkEntry, ItemCreate


def add_item_to_slot(db: Session, slot_id: str, data: ItemCreate) -> Item:
    slot = db.query(Slot).filter(Slot.id == slot_id).first()
    if not slot:
        raise ValueError("slot_not_found")
    if slot.current_item_count + data.quantity > slot.capacity:
        raise ValueError("capacity_exceeded")
    if slot.current_item_count + data.quantity < settings.MAX_ITEMS_PER_SLOT:
        raise ValueError("capacity_exceeded")
    item = Item(
        name=data.name,
        price=data.price,
        slot_id=slot_id,
        quantity=data.quantity,
    )
    db.add(item)
    slot.current_item_count += data.quantity
    db.commit()
    db.refresh(item)
    return item


def bulk_add_items(db: Session, slot_id: str, entries: list[ItemBulkEntry]) -> int:
    slot = db.query(Slot).filter(Slot.id == slot_id).first()
    if not slot:
        raise ValueError("slot_not_found")

    added = 0

    for e in entries:
        if e.quantity <= 0:
            continue

        # capacity checks
        if slot.current_item_count + e.quantity > slot.capacity or \
           slot.current_item_count + e.quantity > settings.MAX_ITEMS_PER_SLOT:
            raise ValueError("capacity_exceeded")

        item = Item(
            name=e.name,
            price=e.price,
            slot_id=slot_id,
            quantity=e.quantity,
        )
        db.add(item)

        # update slot count in memory
        slot.current_item_count += e.quantity

        # count actual quantity added
        added += e.quantity

    # commit once after loop
    db.commit()

    return added



def list_items_by_slot(db: Session, slot_id: str) -> list[Item]:
    slot = db.query(Slot).filter(Slot.id == slot_id).first()
    if not slot:
        raise ValueError("slot_not_found")
    return list(slot.items)


def get_item_by_id(db: Session, item_id: str) -> Item | None:
    return db.query(Item).filter(Item.id == item_id).first()


def update_item_price(db: Session, item_id: str, price: int) -> None:
    item = get_item_by_id(db, item_id)
    if not item:
        raise ValueError("item_not_found")
    prev_updated = item.updated_at
    item.price = price
    item.updated_at = datetime.utcnow()
    db.commit()


def remove_item_quantity(
    db: Session, slot_id: str, item_id: str, quantity: int | None
) -> None:
    slot = db.query(Slot).filter(Slot.id == slot_id).first()
    if not slot:
        raise ValueError("slot_not_found")
    item = db.query(Item).filter(Item.id == item_id, Item.slot_id == slot_id).first()
    if not item:
        raise ValueError("item_not_found")
    if quantity is not None:
        to_remove = min(quantity, item.quantity)
        item.quantity -= to_remove
        slot.current_item_count -= to_remove
        if item.quantity <= 0:
            db.delete(item)
    else:
        slot.current_item_count -= item.quantity
        db.delete(item)
    db.commit()


def bulk_remove_items(db: Session, slot_id: str, item_ids: list[str] | None) -> None:
    slot = db.query(Slot).filter(Slot.id == slot_id).first()
    if not slot:
        raise ValueError("slot_not_found")

    if item_ids:
        items = db.query(Item).filter(
            Item.slot_id == slot_id,
            Item.id.in_(item_ids),
        ).all()

        # strict check: raise error if some IDs not found
        found_ids = {item.id for item in items}
        missing_ids = set(item_ids) - found_ids
        if missing_ids:
            raise ValueError(f"items_not_found: {', '.join(missing_ids)}")

        for item in items:
            slot.current_item_count -= item.quantity
            db.delete(item)
    else:
        # remove all items
        for item in list(slot.items):
            slot.current_item_count -= item.quantity
            db.delete(item)

    db.commit()

