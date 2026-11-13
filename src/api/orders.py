from typing import Any
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from src.api.dependencies import (
    get_current_user,
    get_optional_user,
    require_admin,
)
from src.models.user import Admin, User
from src.services.order_service import OrderService


router = APIRouter(prefix="/orders", tags=["Orders"])

order_service: OrderService | None = None


def get_order_service() -> OrderService:
    global order_service
    if order_service is None:
        order_service = OrderService()
    return order_service


class CreateOrderRequest(BaseModel):
    customer_name: Any = ""
    customer_email: Any = ""
    delivery_type: Any = ""
    delivery_address: Any = None
    distance_km: Any = None
    payment_type: Any = ""
    card_number: Any = None
    items: Any = None
    user_id: Any = None  # Ігнорується — власник визначається тільки за JWT


class UpdateOrderStatusRequest(BaseModel):
    status: Any = ""


@router.post("", status_code=201)
def create_order(
    request: CreateOrderRequest,
    current_user: User | None = Depends(get_optional_user),
    service: OrderService = Depends(get_order_service),
):
    authenticated_user_id = (
        current_user.get_user_id()
        if current_user is not None
        else None
    )

    try:
        return service.create_order(
            customer_name=request.customer_name,
            customer_email=request.customer_email,
            delivery_type=request.delivery_type,
            delivery_address=request.delivery_address,
            distance_km=request.distance_km,
            payment_type=request.payment_type,
            card_number=request.card_number,
            items=request.items,
            user_id=authenticated_user_id,
        )
    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error),
        )


@router.get("/my")
def get_my_orders(
    current_user: User = Depends(get_current_user),
    service: OrderService = Depends(get_order_service),
):
    return service.get_orders_by_user(current_user.get_user_id())


@router.get("")
def list_all_orders(
    _admin: Admin = Depends(require_admin),
    service: OrderService = Depends(get_order_service),
):
    return service.get_all_orders()


@router.get("/{order_id}")
def get_order_by_id(
    order_id: int,
    current_user: User = Depends(get_current_user),
    service: OrderService = Depends(get_order_service),
):
    order = service.get_order_by_id(order_id)
    if order is None:
        raise HTTPException(
            status_code=404,
            detail="Замовлення не знайдено.",
        )

    is_admin = (
        current_user.get_role() == "Admin"
        and isinstance(current_user, Admin)
    )
    if not is_admin:
        if (
            order["user_id"] is None
            or order["user_id"] != current_user.get_user_id()
        ):
            raise HTTPException(
                status_code=403,
                detail="Доступ до чужого замовлення заборонено.",
            )

    return order


@router.patch("/{order_id}/status")
def update_order_status(
    order_id: int,
    request: UpdateOrderStatusRequest,
    _admin: Admin = Depends(require_admin),
    service: OrderService = Depends(get_order_service),
):
    try:
        updated = service.update_order_status(order_id, request.status)
    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error),
        )

    if updated is None:
        raise HTTPException(
            status_code=404,
            detail="Замовлення не знайдено.",
        )

    return updated
