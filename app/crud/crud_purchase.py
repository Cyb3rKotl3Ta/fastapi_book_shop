from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import update, delete, and_, func
from sqlalchemy.orm import joinedload

from app.crud.base import CRUDBase
from app.db.models import Purchase, PurchaseStatus, Book, User
from app.schemas import CartItemCreate # Use specific schema if needed, else handled in logic

class CRUDPurchase: # Not inheriting CRUDBase as logic is more specific

    async def add_item_to_cart(self, db: AsyncSession, *, book: Book, user: User) -> Purchase:
        """ Adds a book to the user's cart (creates a Purchase record with IN_CART status). """
        # Check if already in cart (optional, maybe allow multiple?)
        # existing_cart_item = await self.get_cart_item_by_book(db, user_id=user.id, book_id=book.id)
        # if existing_cart_item:
        #    # Handle update quantity or just return existing? For now, let's assume one item per book in cart.
        #    return existing_cart_item # Or raise an error?

        cart_item = Purchase(
            user_id=user.id,
            book_id=book.id,
            status=PurchaseStatus.IN_CART,
            cost_at_purchase=book.cost # Store current book cost
        )
        db.add(cart_item)
        await db.commit()
        await db.refresh(cart_item, ['book']) # Refresh to load book details if needed immediately
        return cart_item

    async def get_cart_items(self, db: AsyncSession, user_id: int) -> List[Purchase]:
        """ Gets all items currently in the user's cart. """
        result = await db.execute(
            select(Purchase)
            .options(joinedload(Purchase.book)) # Eager load book details
            .filter(Purchase.user_id == user_id, Purchase.status == PurchaseStatus.IN_CART)
            .order_by(Purchase.purchase_date.asc()) # Or any other relevant order
        )
        return result.scalars().all()

    async def get_cart_item(self, db: AsyncSession, user_id: int, cart_item_id: int) -> Optional[Purchase]:
         """ Gets a specific item from the user's cart by its ID. """
         result = await db.execute(
             select(Purchase)
             .filter(Purchase.user_id == user_id, Purchase.id == cart_item_id, Purchase.status == PurchaseStatus.IN_CART)
         )
         return result.scalars().first()

    async def remove_item_from_cart(self, db: AsyncSession, *, cart_item: Purchase) -> None:
        """ Removes a specific item (Purchase record with IN_CART status). """
        await db.delete(cart_item)
        await db.commit()

    async def clear_cart(self, db: AsyncSession, user_id: int) -> int:
        """ Removes all items from a user's cart. Returns the number of items deleted. """
        stmt = (
            delete(Purchase)
            .where(Purchase.user_id == user_id, Purchase.status == PurchaseStatus.IN_CART)
        )
        result = await db.execute(stmt)
        await db.commit()
        return result.rowcount # Number of rows deleted


    async def checkout_cart(self, db: AsyncSession, user: User) -> List[Purchase]:
        """
        Processes the checkout:
        1. Gets cart items.
        2. Calculates total cost.
        3. Checks user balance.
        4. (Transaction starts)
        5. Updates purchase statuses to COMPLETED.
        6. Deducts balance from user.
        7. (Transaction ends)
        Returns the list of completed purchases.
        Raises ValueError on insufficient funds or other errors.
        """
        cart_items = await self.get_cart_items(db, user_id=user.id)
        if not cart_items:
            raise ValueError("Cart is empty")

        total_cost = sum(item.cost_at_purchase for item in cart_items)

        if user.balance < total_cost:
            # Update status to FAILED? Or just raise error? Let's raise for now.
            # We could potentially update items to FAILED status here.
             raise ValueError(f"Insufficient balance. Required: {total_cost}, Available: {user.balance}")

        # --- Transaction block ---
        async with db.begin(): # Use session.begin() for automatic commit/rollback
            # 1. Update purchase statuses
            cart_item_ids = [item.id for item in cart_items]
            update_stmt = (
                update(Purchase)
                .where(Purchase.id.in_(cart_item_ids), Purchase.status == PurchaseStatus.IN_CART) # Ensure status is still IN_CART
                .values(status=PurchaseStatus.COMPLETED, purchase_date=func.now()) # Update status and timestamp
                .execution_options(synchronize_session="fetch") # Strategy for session sync after UPDATE
            )
            await db.execute(update_stmt)

            # 2. Deduct balance (using crud_user helper method)
            # Note: crud_user.update_balance should *not* commit itself if used within this transaction
            # Let's implement the balance update directly here to ensure it's part of the same transaction.
            new_balance = user.balance - total_cost
            user_update_stmt = (
                update(User)
                .where(User.id == user.id)
                .values(balance=new_balance)
                 # Ensure we don't go below zero due to concurrent actions (optional optimistic lock)
                #.where(User.balance >= total_cost)
            )
            result = await db.execute(user_update_stmt)

            # Check if user balance update was successful (e.g., if optimistic lock was added)
            if result.rowcount == 0:
                 # This means the balance was already less than total_cost when the update ran
                 # Rollback will happen automatically due to the exception
                raise ValueError("Failed to update balance, possibly due to concurrent transaction or check failure.")

        # --- Transaction end ---

        # Refresh objects outside the transaction if needed (status already updated)
        # For returning, fetch the updated items again
        completed_purchases_result = await db.execute(
            select(Purchase)
            .options(joinedload(Purchase.book))
            .filter(Purchase.id.in_(cart_item_ids))
        )
        completed_purchases = completed_purchases_result.scalars().all()

        return completed_purchases


purchase = CRUDPurchase()