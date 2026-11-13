from typing import Any
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from src.api.dependencies import require_admin
from src.models.user import Admin
from src.services.product_service import ProductService


router = APIRouter(prefix="/products", tags=["Products"])

product_service: ProductService | None = None


def get_product_service() -> ProductService:
    global product_service
    if product_service is None:
        product_service = ProductService()
    return product_service


class CreateProductRequest(BaseModel):
    name: Any = ""
    brand: Any = ""
    category: Any = ""
    price: Any = None
    stock_quantity: Any = None
    stock: Any = None
    image: Any = None
    attributes: Any = None
    description: Any = None


class UpdateProductRequest(BaseModel):
    name: Any = None
    brand: Any = None
    category: Any = None
    price: Any = None
    stock_quantity: Any = None
    stock: Any = None
    image: Any = None
    attributes: Any = None
    description: Any = None


@router.get("")
def list_products(
    category: str | None = None,
    brand: list[str] | None = Query(default=None),
    max_price: float | None = None,
    search: str | None = None,
    service: ProductService = Depends(get_product_service),
):
    try:
        return service.get_all_products(
            category=category,
            brand=brand,
            max_price=max_price,
            search=search,
        )
    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error),
        )


@router.get("/{product_id}")
def get_product(
    product_id: int,
    service: ProductService = Depends(get_product_service),
):
    product = service.get_product_by_id(product_id)
    if product is None:
        raise HTTPException(
            status_code=404,
            detail="Product not found",
        )
    return product


@router.post("", status_code=201)
def create_product(
    request: CreateProductRequest,
    _admin: Admin = Depends(require_admin),
    service: ProductService = Depends(get_product_service),
):
    stock_value = (
        request.stock_quantity
        if request.stock_quantity is not None
        else request.stock
    )

    try:
        return service.create_product(
            name=request.name,
            brand=request.brand,
            category=request.category,
            price=request.price,
            stock_quantity=stock_value,
            image=request.image,
            attributes=request.attributes,
            description=request.description,
        )
    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error),
        )


@router.put("/{product_id}")
@router.patch("/{product_id}")
def update_product(
    product_id: int,
    request: UpdateProductRequest,
    _admin: Admin = Depends(require_admin),
    service: ProductService = Depends(get_product_service),
):
    fields_set = getattr(request, "model_fields_set", set())
    stock_value = (
        request.stock_quantity
        if "stock_quantity" in fields_set or request.stock_quantity is not None
        else request.stock
    )

    try:
        updated = service.update_product(
            product_id=product_id,
            name=request.name if "name" in fields_set else None,
            brand=request.brand if "brand" in fields_set else None,
            category=request.category if "category" in fields_set else None,
            price=request.price if "price" in fields_set else None,
            stock_quantity=(
                stock_value
                if ("stock_quantity" in fields_set or "stock" in fields_set)
                else None
            ),
            image=request.image if "image" in fields_set else None,
            attributes=request.attributes if "attributes" in fields_set else None,
            description=request.description if "description" in fields_set else None,
            replace_image="image" in fields_set,
            replace_description="description" in fields_set,
        )
    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error),
        )

    if updated is None:
        raise HTTPException(
            status_code=404,
            detail="Product not found",
        )

    return updated


@router.delete("/{product_id}")
def delete_product(
    product_id: int,
    _admin: Admin = Depends(require_admin),
    service: ProductService = Depends(get_product_service),
):
    deleted = service.delete_product(product_id)
    if not deleted:
        raise HTTPException(
            status_code=404,
            detail="Product not found",
        )
    return {
        "message": "Product deleted successfully",
        "id": product_id,
    }
