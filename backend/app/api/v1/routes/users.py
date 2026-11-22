from fastapi import APIRouter, HTTPException, Response, status

from app.api.v1.cookies import clear_refresh_cookie, set_refresh_cookie
from app.api.v1.deps import CurrentUser, DbSession
from app.core.security import hash_password, verify_password
from app.models import User
from app.schemas.user import AccountDelete, PasswordChange, UserOut, UserUpdate
from app.services import auth_service, document_service

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserOut)
def read_me(current_user: CurrentUser) -> User:
    return current_user


@router.patch("/me", response_model=UserOut)
def update_me(payload: UserUpdate, current_user: CurrentUser, db: DbSession) -> User:
    # exclude_unset: only change the fields the client actually sent
    for field, value in payload.model_dump(exclude_unset=True, exclude_none=True).items():
        setattr(current_user, field, value)
    db.commit()
    db.refresh(current_user)
    return current_user


@router.post("/me/password", status_code=status.HTTP_204_NO_CONTENT)
def change_password(payload: PasswordChange, response: Response, current_user: CurrentUser, db: DbSession) -> None:
    if not verify_password(payload.current_password, current_user.hashed_password):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Current password is incorrect")

    current_user.hashed_password = hash_password(payload.new_password)
    # Log out every other device, then give this browser a fresh session.
    auth_service.revoke_all_refresh_tokens(db, current_user.id)
    set_refresh_cookie(response, auth_service.issue_refresh_token(db, current_user.id))


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
def delete_account(payload: AccountDelete, response: Response, current_user: CurrentUser, db: DbSession) -> None:
    """Permanently delete the account and everything in it (files, extracted images, vectors, chats)."""
    if not verify_password(payload.password, current_user.hashed_password):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Password is incorrect")
    # Delete documents one by one so their files and vectors are removed too;
    # a plain cascade would only remove database rows and leave files behind.
    for document in document_service.list_documents(db, current_user.id):
        document_service.delete_document(db, document)
    db.delete(current_user)
    db.commit()
    clear_refresh_cookie(response)
