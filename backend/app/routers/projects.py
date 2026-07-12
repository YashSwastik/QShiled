"""
Projects, Organizations, and Applications router.

Phase 1 endpoints (implemented):
  POST   /api/projects              — create project (creates org if needed)
  GET    /api/projects              — list projects
  GET    /api/projects/{id}         — project detail
  POST   /api/applications          — create application with business context
  GET    /api/applications          — list applications (filter by project_id)
  GET    /api/applications/{id}     — application detail
  PATCH  /api/applications/{id}     — update application business context
"""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.organization import Organization
from app.models.project import Project
from app.models.application import Application
from app.models.base import new_uuid
from app.schemas.project import (
    OrganizationCreate,
    OrganizationResponse,
    ProjectCreate,
    ProjectUpdate,
    ProjectResponse,
    ProjectListResponse,
    ApplicationCreate,
    ApplicationUpdate,
    ApplicationResponse,
    ApplicationListResponse,
)

router = APIRouter(tags=["projects"])


# ── Helpers ───────────────────────────────────────────────────────────────────

def _get_org_or_404(db: Session, org_id: str) -> Organization:
    org = db.get(Organization, org_id)
    if not org:
        raise HTTPException(status_code=404, detail=f"Organization '{org_id}' not found")
    return org


def _get_project_or_404(db: Session, project_id: str) -> Project:
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail=f"Project '{project_id}' not found")
    return project


def _get_app_or_404(db: Session, app_id: str) -> Application:
    app = db.get(Application, app_id)
    if not app:
        raise HTTPException(status_code=404, detail=f"Application '{app_id}' not found")
    return app


# ── Organization endpoints ────────────────────────────────────────────────────

@router.post(
    "/organizations",
    response_model=OrganizationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create organization",
)
def create_organization(payload: OrganizationCreate, db: Session = Depends(get_db)):
    # Check slug uniqueness
    existing = db.query(Organization).filter(Organization.slug == payload.slug).first()
    if existing:
        raise HTTPException(
            status_code=409,
            detail=f"Organization with slug '{payload.slug}' already exists",
        )
    org = Organization(
        id=new_uuid(),
        name=payload.name,
        slug=payload.slug,
        description=payload.description,
    )
    db.add(org)
    db.commit()
    db.refresh(org)
    return org


@router.get(
    "/organizations",
    response_model=list[OrganizationResponse],
    summary="List organizations",
)
def list_organizations(db: Session = Depends(get_db)):
    return db.query(Organization).order_by(Organization.created_at.desc()).all()


# ── Project endpoints ─────────────────────────────────────────────────────────

@router.post(
    "/projects",
    response_model=ProjectResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create project",
)
def create_project(payload: ProjectCreate, db: Session = Depends(get_db)):
    _get_org_or_404(db, payload.organization_id)
    project = Project(
        id=new_uuid(),
        organization_id=payload.organization_id,
        name=payload.name,
        description=payload.description,
        status=payload.status,
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


@router.get(
    "/projects",
    response_model=ProjectListResponse,
    summary="List projects",
)
def list_projects(
    organization_id: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    q = db.query(Project)
    if organization_id:
        q = q.filter(Project.organization_id == organization_id)
    total = q.count()
    items = q.order_by(Project.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()
    return ProjectListResponse(total=total, items=items)


@router.get(
    "/projects/{project_id}",
    response_model=ProjectResponse,
    summary="Get project detail",
)
def get_project(project_id: str, db: Session = Depends(get_db)):
    return _get_project_or_404(db, project_id)


@router.patch(
    "/projects/{project_id}",
    response_model=ProjectResponse,
    summary="Update project",
)
def update_project(project_id: str, payload: ProjectUpdate, db: Session = Depends(get_db)):
    project = _get_project_or_404(db, project_id)
    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(project, field, value)
    db.commit()
    db.refresh(project)
    return project


@router.delete(
    "/projects/{project_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete project and all child data",
)
def delete_project(project_id: str, db: Session = Depends(get_db)):
    project = _get_project_or_404(db, project_id)
    db.delete(project)
    db.commit()


# ── Application endpoints ─────────────────────────────────────────────────────

@router.post(
    "/applications",
    response_model=ApplicationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create application with business context",
)
def create_application(payload: ApplicationCreate, db: Session = Depends(get_db)):
    _get_project_or_404(db, payload.project_id)
    app = Application(id=new_uuid(), **payload.model_dump())
    db.add(app)
    db.commit()
    db.refresh(app)
    return app


@router.get(
    "/applications",
    response_model=ApplicationListResponse,
    summary="List applications",
)
def list_applications(
    project_id: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    q = db.query(Application)
    if project_id:
        q = q.filter(Application.project_id == project_id)
    total = q.count()
    items = q.order_by(Application.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()
    return ApplicationListResponse(total=total, items=items)


@router.get(
    "/applications/{app_id}",
    response_model=ApplicationResponse,
    summary="Get application detail",
)
def get_application(app_id: str, db: Session = Depends(get_db)):
    return _get_app_or_404(db, app_id)


@router.patch(
    "/applications/{app_id}",
    response_model=ApplicationResponse,
    summary="Update application business context",
)
def update_application(app_id: str, payload: ApplicationUpdate, db: Session = Depends(get_db)):
    app = _get_app_or_404(db, app_id)
    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(app, field, value)
    db.commit()
    db.refresh(app)
    return app


@router.delete(
    "/applications/{app_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete application",
)
def delete_application(app_id: str, db: Session = Depends(get_db)):
    app = _get_app_or_404(db, app_id)
    db.delete(app)
    db.commit()
