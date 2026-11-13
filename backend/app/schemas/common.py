from pydantic import BaseModel


class Page[T](BaseModel):
    """One page of a list. `total` counts all matching items across pages."""

    items: list[T]
    page: int
    page_size: int
    total: int
