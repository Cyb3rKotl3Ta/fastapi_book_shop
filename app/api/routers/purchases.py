from typing import List, Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app import crud, schemas
from app.db.models.user import User
from app.db.models.book import BookAvailability
from app.api import deps

router = APIRouter()

# --- Cart Management ---

@router.post("/cart/items", response_model=schemas.CartItem, status_code=status.HTTP_201_CREATED)
async def add_book_to_cart(
    *,
    db: AsyncSession = Depends(deps.get_db),
    item_in: schemas.CartItemCreate, # Contains book_id
    current_user: User = Depends(deps.get_current_active_user),
):
    """
    Add a book to the current user's shopping cart.
    Creates a Purchase record with status 'IN_CART'.
    """
    book = await crud.book.get(db=db, id=item_in.book_id)
    if not book:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Book not found")

    if book.availability_status != BookAvailability.AVAILABLE:
         raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Book '{book.title}' is currently not available for purchase.")

    # Check if already in cart (using crud_purchase helper)
    existing_item = await crud.purchase.get_cart_item(db, user_id=current_user.id, book_id=item_in.book_id)
    if existing_item:
         raise HTTPException(
             status_code=status.HTTP_400_BAD_REQUEST,
             detail=f"Book '{book.title}' is already in your cart."
         )
         # Or update quantity if implementing quantity logic

    purchase_record = await crud.purchase.add_item_to_cart(db=db, book=book, user=current_user)

    # Map the Purchase record to CartItem schema
    cart_item_response = schemas.CartItem(
        id=purchase_record.id,
        book_id=purchase_record.book_id,
        cost_at_purchase=purchase_record.cost_at_purchase,
        added_at=purchase_record.purchase_date, # purchase_date serves as added_at for IN_CART
        book=purchase_record.book # Nested book details loaded by refresh/joinedload
    )
    return cart_item_response


@router.get("/cart", response_model=schemas.Cart)
async def view_cart(
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user),
):
    """
    View the items currently in the user's shopping cart.
    """
    purchase_records = await crud.purchase.get_cart_items(db, user_id=current_user.id)

    cart_items = []
    total_cost = 0.0
    for record in purchase_records:
        cart_items.append(schemas.CartItem(
            id=record.id,
            book_id=record.book_id,
            cost_at_purchase=record.cost_at_purchase,
            added_at=record.purchase_date,
            book=record.book # Assumes book relationship was loaded
        ))
        total_cost += record.cost_at_purchase

    return schemas.Cart(items=cart_items, total_cost=total_cost)


@router.delete("/cart/items/{item_id}", response_model=schemas.Message)
async def remove_book_from_cart(
    *,
    db: AsyncSession = Depends(deps.get_db),
    item_id: int, # This is the Purchase ID (cart item ID)
    current_user: User = Depends(deps.get_current_active_user),
):
    """
    Remove a specific item from the user's shopping cart.
    """
    cart_item = await crud.purchase.get_cart_item(db, user_id=current_user.id, cart_item_id=item_id)

    if not cart_item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cart item not found")

    # Ensure it belongs to the current user and is IN_CART (already checked by get_cart_item)

    await crud.purchase.remove_item_from_cart(db=db, cart_item=cart_item)
    return {"message": "Item removed from cart successfully"}

# --- Checkout ---

@router.post("/checkout", response_model=List[schemas.Purchase])
async def checkout(
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user),
):
    """
    Finalize the purchase of items in the cart.
    Checks balance, updates item statuses to 'COMPLETED', and deducts cost from user balance.
    """
    try:
        # Refresh user object to get the latest balance before checkout
        await db.refresh(current_user, ["balance"])
        completed_purchases = await crud.purchase.checkout_cart(db=db, user=current_user)
        return completed_purchases
    except ValueError as e:
        # Catch specific errors like "Insufficient balance" or "Cart is empty"
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        # Catch potential database errors during transaction
        # Log the error e
        print(f"Checkout error: {e}") # Replace with proper logging
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="An error occurred during checkout.")