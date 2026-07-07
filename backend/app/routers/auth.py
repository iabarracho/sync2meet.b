from __future__ import annotations



from fastapi import APIRouter, Depends, HTTPException, Request, Response

from fastapi.responses import JSONResponse

from sqlalchemy import func

from sqlalchemy.orm import Session



from ..config import settings

from ..deps import get_current_user, get_db

from ..models import User

from ..schemas import (
    AuthConfigOut,
    AuthSessionOut,
    LoginRequest,
    RegisterRequest,
    UserOut,
)

from ..services.auth import (

    allowed_domains_label,

    create_access_token,

    email_domain_allowed,

    hash_password,

    verify_password,

)

from ..services import audit as audit_service

from ..services import rate_limit as rate_limit_service



router = APIRouter(prefix="/api/auth", tags=["auth"])



MIN_PASSWORD_LENGTH = 8
MAX_PASSWORD_LENGTH = 128





def _users_count(db: Session) -> int:

    return db.query(func.count(User.id)).scalar() or 0





def _registration_open(db: Session) -> bool:

    if not settings.auth_enabled or not settings.allow_registration:

        return False

    return _users_count(db) < settings.max_team_users





@router.get("/config", response_model=AuthConfigOut)

def auth_config(db: Session = Depends(get_db)) -> AuthConfigOut:

    count = _users_count(db)

    return AuthConfigOut(

        auth_enabled=settings.auth_enabled,

        allow_registration=_registration_open(db),

        max_team_users=settings.max_team_users,

        users_count=None,

        allowed_email_domains=settings.allowed_email_domains_list,

    )





@router.post("/register", response_model=AuthSessionOut, status_code=201)

def register(

    body: RegisterRequest,

    request: Request,

    db: Session = Depends(get_db),

) -> Response:

    rate_limit_service.check_rate_limit(request, bucket="register")

    if not settings.auth_enabled:

        raise HTTPException(400, "Autenticação desativada neste servidor.")



    if not _registration_open(db):

        if _users_count(db) >= settings.max_team_users:

            raise HTTPException(

                403,

                f"Limite de {settings.max_team_users} utilizadores atingido. "

                "Contacta o administrador.",

            )

        raise HTTPException(403, "Registo de novas contas está fechado.")



    name = body.name.strip()

    if len(name) < 2:

        raise HTTPException(400, "Indica o teu nome (mínimo 2 caracteres).")



    email = body.email.lower().strip()

    if not email_domain_allowed(email, role="member"):

        raise HTTPException(

            400,

            f"Só emails {allowed_domains_label()} podem criar conta. "

            "Contacta o administrador se precisares de ajuda.",

        )



    if db.query(User).filter(User.email == email).first():

        raise HTTPException(400, "Email ou password incorretos.")



    count = _users_count(db)
    role = "member"



    if len(body.password) < MIN_PASSWORD_LENGTH:

        raise HTTPException(

            400,

            f"A password deve ter pelo menos {MIN_PASSWORD_LENGTH} caracteres.",

        )



    if len(body.password) > MAX_PASSWORD_LENGTH:

        raise HTTPException(400, "Password demasiado longa.")



    user = User(

        name=name,

        email=email,

        role=role,

        password_hash=hash_password(body.password),

    )

    db.add(user)

    db.commit()

    db.refresh(user)



    rate_limit_service.reset_rate_limit(request, bucket="register")

    audit_service.log_audit(

        db,

        action="auth.register",

        user_id=user.id,

        user_email=user.email,

        detail=f"role={role}",

    )

    token = create_access_token(user.id, user.token_version)

    return _token_response(user, token)





@router.post("/login", response_model=AuthSessionOut)

def login(body: LoginRequest, request: Request, db: Session = Depends(get_db)) -> Response:

    rate_limit_service.check_rate_limit(request, bucket="login")

    if not settings.auth_enabled:

        if settings.is_production:

            raise HTTPException(503, "Autenticação obrigatória em produção.")

        user = db.query(User).order_by(User.created_at.asc()).first()

        if not user:

            raise HTTPException(503, "Nenhum utilizador configurado.")

        token = create_access_token(user.id, user.token_version)

        return _token_response(user, token)



    user = db.query(User).filter(User.email == body.email.lower().strip()).first()

    if not user or not user.password_hash:

        audit_service.log_audit(

            db,

            action="auth.login_failed",

            user_email=body.email.lower().strip(),

            detail="invalid credentials",

        )

        raise HTTPException(401, "Email ou password incorretos.")

    if not verify_password(body.password, user.password_hash):

        audit_service.log_audit(

            db,

            action="auth.login_failed",

            user_email=user.email,

            detail="invalid credentials",

        )

        raise HTTPException(401, "Email ou password incorretos.")



    if user.role != "admin" and not email_domain_allowed(user.email, role=user.role):

        raise HTTPException(

            403,

            f"Apenas emails {allowed_domains_label()} podem iniciar sessão.",

        )



    rate_limit_service.reset_rate_limit(request, bucket="login")

    audit_service.log_audit(

        db,

        action="auth.login",

        user_id=user.id,

        user_email=user.email,

    )

    token = create_access_token(user.id, user.token_version)

    return _token_response(user, token)





@router.get("/me", response_model=UserOut)

def me(user: User = Depends(get_current_user)) -> User:

    return user





@router.post("/logout")

def logout(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> Response:

    audit_service.log_audit(
        db,
        action="auth.logout",
        user_id=user.id,
        user_email=user.email,
    )
    user.token_version += 1
    db.commit()
    response = JSONResponse({"ok": True})

    response.delete_cookie("sync2meet_token", path="/")

    return response





def _token_response(user: User, token: str) -> JSONResponse:
    body = AuthSessionOut(user=UserOut.model_validate(user))
    response = JSONResponse(content=body.model_dump())

    response.set_cookie(

        key="sync2meet_token",

        value=token,

        httponly=True,

        secure=settings.cookie_secure,

        samesite="lax",

        max_age=settings.auth_token_hours * 3600,

        path="/",

    )

    return response


