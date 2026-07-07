from __future__ import annotations



import uuid

from pathlib import Path



from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile

from sqlalchemy.orm import Session



from ..deps import get_current_user, get_db, require_admin

from ..models import Template, TemplateSource, TemplateType

from ..schemas import TemplateCreate, TemplateOut, TemplateUpdate

from ..config import settings

from ..services import ai as ai_service

from ..services.builtin_templates import BUILTIN_TEMPLATES

from ..services.template_cleanup import cleanup_duplicate_templates, is_copy_name

from ..services import storage as storage_service



router = APIRouter(

    prefix="/api/templates",

    tags=["templates"],

    dependencies=[Depends(get_current_user)],

)



_CANONICAL_BUILTIN = {(s["name"], s["type"]) for s in BUILTIN_TEMPLATES}





def _is_protected_builtin(t: Template, db: Session) -> bool:

    """Only the original built-in (oldest per name+type) cannot be deleted."""

    if is_copy_name(t.name):

        return False

    if t.source != TemplateSource.builtin:

        return False



    siblings = (

        db.query(Template)

        .filter(Template.name == t.name, Template.type == t.type)

        .order_by(Template.created_at.asc())

        .all()

    )

    if len(siblings) > 1:

        return siblings[0].id == t.id



    return (t.name, t.type) in _CANONICAL_BUILTIN





def _to_template_out(t: Template, db: Session) -> TemplateOut:

    return TemplateOut.model_validate(t).model_copy(

        update={"can_delete": not _is_protected_builtin(t, db)}

    )





def _source_from_filename(name: str) -> TemplateSource:

    lower = name.lower()

    if lower.endswith(".docx"):

        return TemplateSource.docx

    if lower.endswith(".pdf"):

        return TemplateSource.pdf

    return TemplateSource.markdown





@router.get("", response_model=list[TemplateOut])

def list_templates(

    type: TemplateType | None = None,

    db: Session = Depends(get_db),

) -> list[TemplateOut]:

    q = db.query(Template)

    if type:

        q = q.filter(Template.type == type)

    rows = q.order_by(Template.is_default.desc(), Template.name).all()

    return [_to_template_out(t, db) for t in rows]





@router.get("/{template_id}", response_model=TemplateOut)

def get_template(template_id: str, db: Session = Depends(get_db)) -> TemplateOut:

    t = db.get(Template, template_id)

    if not t:

        raise HTTPException(404, "Template not found")

    return _to_template_out(t, db)





@router.post("", response_model=TemplateOut, status_code=201)

def create_template(

    body: TemplateCreate,

    db: Session = Depends(get_db),

    _admin=Depends(require_admin),

) -> Template:

    if body.is_default:

        db.query(Template).filter(Template.type == body.type).update(

            {"is_default": False}

        )

    t = Template(

        name=body.name,

        type=body.type,

        content=body.content,

        is_default=body.is_default,

    )

    db.add(t)

    db.commit()

    db.refresh(t)

    return _to_template_out(t, db)





@router.post("/upload", response_model=TemplateOut, status_code=201)

async def upload_template(

    name: str,

    type: TemplateType,

    file: UploadFile = File(...),

    db: Session = Depends(get_db),

    _admin=Depends(require_admin),

) -> Template:

    if not file.filename:

        raise HTTPException(400, "Filename required")

    ext = Path(file.filename).suffix.lower()

    if ext not in (".docx", ".pdf", ".md", ".markdown", ".txt"):

        raise HTTPException(400, "Extensão não permitida (.docx, .pdf, .md, .txt)")

    try:

        dest = storage_service.save_template_upload(file.filename, file.file)

    except ValueError as exc:

        raise HTTPException(400, str(exc)) from exc

    source = _source_from_filename(file.filename)



    structure = await ai_service.parse_template_structure(dest, source.value)

    content = ai_service.extract_template_text(dest, source.value)



    t = Template(

        name=name,

        type=type,

        source=source,

        content=content,

        structure=structure,

        original_file_path=str(dest),

    )

    db.add(t)

    db.commit()

    db.refresh(t)

    return _to_template_out(t, db)





@router.patch("/{template_id}", response_model=TemplateOut)

def update_template(

    template_id: str,

    body: TemplateUpdate,

    db: Session = Depends(get_db),

    _admin=Depends(require_admin),

) -> Template:

    t = db.get(Template, template_id)

    if not t:

        raise HTTPException(404, "Template not found")

    data = body.model_dump(exclude_unset=True)

    if data.get("is_default"):

        db.query(Template).filter(Template.type == t.type).update(

            {"is_default": False}

        )

    for k, v in data.items():

        setattr(t, k, v)

    db.commit()

    db.refresh(t)

    return _to_template_out(t, db)





@router.post("/cleanup-copies")

def cleanup_copy_templates(

    db: Session = Depends(get_db),

    _admin=Depends(require_admin),

) -> dict:

    """Remove accidental copies and duplicate rows (keeps oldest per name+type)."""

    removed = cleanup_duplicate_templates(db)

    return {"ok": True, "removed": removed}





@router.post("/{template_id}/refresh-content", response_model=TemplateOut)

def refresh_template_content(

    template_id: str,

    db: Session = Depends(get_db),

    _admin=Depends(require_admin),

) -> TemplateOut:

    """Re-lê o ficheiro original (útil após melhorias na extração DOCX)."""

    t = db.get(Template, template_id)

    if not t:

        raise HTTPException(404, "Template not found")

    if not t.original_file_path:

        raise HTTPException(400, "Este template não tem ficheiro original para reimportar.")

    path = Path(t.original_file_path)

    if not path.exists():

        raise HTTPException(404, "Ficheiro original do template não encontrado.")

    t.content = ai_service.extract_template_text(path, t.source.value)

    db.commit()

    db.refresh(t)

    return _to_template_out(t, db)





@router.post("/{template_id}/set-default", response_model=TemplateOut)

def set_default(

    template_id: str,

    db: Session = Depends(get_db),

    _admin=Depends(require_admin),

) -> Template:

    t = db.get(Template, template_id)

    if not t:

        raise HTTPException(404, "Template not found")

    db.query(Template).filter(Template.type == t.type).update({"is_default": False})

    t.is_default = True

    db.commit()

    db.refresh(t)

    return _to_template_out(t, db)





@router.delete("/{template_id}", status_code=204, response_class=Response)

def delete_template(

    template_id: str,

    db: Session = Depends(get_db),

    _admin=Depends(require_admin),

) -> Response:

    t = db.get(Template, template_id)

    if not t:

        raise HTTPException(404, "Template not found")

    if _is_protected_builtin(t, db):

        raise HTTPException(

            400,

            "Só o template pré-definido original (o mais antigo) não pode ser apagado",

        )

    db.delete(t)

    db.commit()

    return Response(status_code=204)


