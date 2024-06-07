from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from app.db import SessionLocal, get_db
from app.schemas import post as schemas
from app.services import post as services
from app.services import auth
from app.cache import cache

router = APIRouter()

MAX_PAYLOAD_SIZE = 1 * 1024 * 1024  # 1 MB

@router.post("/posts", response_model=schemas.PostOut)
async def add_post(request: Request, post: schemas.PostCreate, token: str = Depends(auth.get_current_user), db: Session = Depends(get_db)):
    # Validate payload size
    content_length = request.headers.get('content-length')
    if content_length and int(content_length) > MAX_PAYLOAD_SIZE:
        raise HTTPException(status_code=413, detail="Payload too large")
    
    user = auth.get_user_by_email(db, email=token.sub)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    return services.create_post(db=db, post=post, user_id=user.id)

@router.get("/posts", response_model=List[schemas.PostOut])
def get_posts(token: str = Depends(auth.get_current_user), db: Session = Depends(get_db)):
    user = auth.get_user_by_email(db, email=token.sub)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid token")
    cached_posts = cache.get(f"user_posts_{user.id}")
    if cached_posts:
        return cached_posts
    posts = services.get_posts(db=db, user_id=user.id)
    cache.set(f"user_posts_{user.id}", posts, ttl=300)
    return posts

@router.delete("/posts/{post_id}")
def delete_post(post_id: int, token: str = Depends(auth.get_current_user), db: Session = Depends(get_db)):
    user = auth.get_user_by_email(db, email=token.sub)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid token")
    if not services.delete_post(db=db, post_id=post_id, user_id=user.id):
        raise HTTPException(status_code=404, detail="Post not found")
    return {"detail": "Post deleted"}
