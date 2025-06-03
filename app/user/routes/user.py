from fastapi import APIRouter, Depends, HTTPException, Path
from app.user.model.user import User
from pydantic import BaseModel, Field
from typing import Optional, List

router = APIRouter()

@router.get("/")
async def get_users():
    return await User.all()


class UserItem(BaseModel):
    id: Optional[int] = None
    name: Optional[str] = None
    email: Optional[str] = None
    last_name: Optional[str] = None


class UserOut(BaseModel):
    id: int
    name: str
    email: str

    class Config:
        orm_mode = True


@router.get("/users", response_model=List[UserOut])
async def filter_user(params: UserItem = Depends()):
    t = params.model_dump(exclude_unset=True, exclude_none=True)
    return await User.filter(**t)


class PostUserItem(BaseModel):
    name: Optional[str] = Field(default=None, description='name')
    email: Optional[str] = Field(default=None, description='email')
    last_name: Optional[str] = Field(default=None, description='last_name')
    

@router.post("/users/{user_id}")
async def update_user_by_id(user_id: int=Path(..., description="User ID to update"),  user_item: PostUserItem=None):
    user = await User.filter(id = user_id).first()
    if not user:
        raise HTTPException(status_code=400, detail='Uesr not found')
    
    update_data = user_item.model_dump(exclude_unset=True, exclude_none=True)
    for field, value in update_data.items():
        setattr(user, field, value)
    await user.save()
    return user