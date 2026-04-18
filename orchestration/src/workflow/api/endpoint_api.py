"""Dynamic API endpoint management.

Management (JWT required):
  POST   /workflows/{id}/endpoints             — bind a custom path to a workflow
  GET    /workflows/{id}/endpoints             — list bindings for a workflow
  GET    /workflows/{id}/endpoints/{ep_id}     — get single binding
  PUT    /workflows/{id}/endpoints/{ep_id}     — update binding
  DELETE /workflows/{id}/endpoints/{ep_id}     — delete binding

Dynamic execution (public prefix /run):
  ANY    /run/{path:path}                      — execute the bound workflow
      • workflow.is_published=True  → no auth required
      • workflow.is_published=False → JWT required
      Body (POST/PUT/PATCH): JSON object → workflow input_data
      Query params (GET/DELETE):       → workflow input_data
"""

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session

from src.auth.api.auth_api import get_current_user
from src.auth.services.auth_service import verify_token
from src.common.logging import logger
from src.common.services.database import database_service
from src.user.models.user_model import User
from src.workflow.schemas.endpoint_schema import EndpointCreate, EndpointResponse, EndpointUpdate
from src.workflow.services.executor.engine import workflow_engine

router = APIRouter()       # mounted at /workflows
run_router = APIRouter()   # mounted at /run

_bearer = HTTPBearer(auto_error=False)


def _get_db():
    with Session(database_service.engine) as session:
        yield session


def _owned_workflow(workflow_id: str, user: User, db: Session):
    workflow = database_service.get_workflow(db, workflow_id)
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")
    if workflow.user_id != user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    return workflow


# ── Management endpoints ──────────────────────────────────────────────────────

@router.post(
    "/{workflow_id}/endpoints",
    response_model=EndpointResponse,
    status_code=201,
    summary="동적 API 엔드포인트 생성",
)
async def create_endpoint(
    workflow_id: str,
    body: EndpointCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(_get_db),
):
    """Bind a custom HTTP path to a workflow.

    The resulting public URL will be:
        {method} /api/v1/run/{body.path}
    """
    _owned_workflow(workflow_id, user, db)

    try:
        endpoint = database_service.create_endpoint(
            db,
            workflow_id=workflow_id,
            user_id=user.id,
            path=body.path,
            method=body.method,
            description=body.description,
            is_active=body.is_active,
        )
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail=f"{body.method} /{body.path} is already bound to another workflow",
        )

    logger.info("endpoint_created", workflow_id=workflow_id, path=body.path, method=body.method)
    return endpoint


@router.get(
    "/{workflow_id}/endpoints",
    response_model=list[EndpointResponse],
    summary="동적 API 엔드포인트 목록",
)
async def list_endpoints(
    workflow_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(_get_db),
):
    _owned_workflow(workflow_id, user, db)
    return database_service.list_endpoints(db, workflow_id)


@router.get(
    "/{workflow_id}/endpoints/{endpoint_id}",
    response_model=EndpointResponse,
    summary="동적 API 엔드포인트 상세",
)
async def get_endpoint(
    workflow_id: str,
    endpoint_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(_get_db),
):
    _owned_workflow(workflow_id, user, db)
    ep = database_service.get_endpoint(db, endpoint_id)
    if not ep or ep.workflow_id != workflow_id:
        raise HTTPException(status_code=404, detail="Endpoint not found")
    return ep


@router.put(
    "/{workflow_id}/endpoints/{endpoint_id}",
    response_model=EndpointResponse,
    summary="동적 API 엔드포인트 수정",
)
async def update_endpoint(
    workflow_id: str,
    endpoint_id: str,
    body: EndpointUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(_get_db),
):
    _owned_workflow(workflow_id, user, db)
    ep = database_service.get_endpoint(db, endpoint_id)
    if not ep or ep.workflow_id != workflow_id:
        raise HTTPException(status_code=404, detail="Endpoint not found")

    try:
        updated = database_service.update_endpoint(
            db,
            ep,
            **{k: v for k, v in body.model_dump().items() if v is not None},
        )
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Path/method combination already exists")

    return updated


@router.delete(
    "/{workflow_id}/endpoints/{endpoint_id}",
    status_code=204,
    summary="동적 API 엔드포인트 삭제",
)
async def delete_endpoint(
    workflow_id: str,
    endpoint_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(_get_db),
):
    _owned_workflow(workflow_id, user, db)
    ep = database_service.get_endpoint(db, endpoint_id)
    if not ep or ep.workflow_id != workflow_id:
        raise HTTPException(status_code=404, detail="Endpoint not found")
    database_service.delete_endpoint(db, ep)


# ── Dynamic execution handler ─────────────────────────────────────────────────

async def _resolve_user_optional(
    credentials: HTTPAuthorizationCredentials | None,
    db: Session,
) -> User | None:
    """Return a User if valid JWT is present, else None."""
    if not credentials:
        return None
    try:
        payload = verify_token(credentials.credentials)
        if not payload:
            return None
        user_id = payload.get("sub")
        if not user_id:
            return None
        return await database_service.get_user(int(user_id))
    except Exception:
        return None


@run_router.api_route(
    "/{path:path}",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    summary="동적 API 엔드포인트 실행",
)
async def run_dynamic_endpoint(
    path: str,
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    db: Session = Depends(_get_db),
):
    """Execute the workflow bound to the requested path + HTTP method.

    Input data is collected from:
    - Request JSON body  (POST / PUT / PATCH)
    - Query parameters   (GET / DELETE)
    """
    method = request.method.upper()
    normalized_path = path.strip("/").lower()

    ep = database_service.get_endpoint_by_path(db, normalized_path, method)
    if not ep:
        raise HTTPException(status_code=404, detail=f"No active endpoint for {method} /{path}")

    workflow = database_service.get_workflow(db, ep.workflow_id)
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")

    # Auth: published workflows are public; unpublished require JWT
    if not workflow.is_published:
        user = await _resolve_user_optional(credentials, db)
        if not user:
            raise HTTPException(status_code=401, detail="Authentication required (workflow is not published)")
        if workflow.user_id != user.id:
            raise HTTPException(status_code=403, detail="Access denied")

    # Collect input_data
    if method in ("POST", "PUT", "PATCH"):
        try:
            input_data = await request.json()
            if not isinstance(input_data, dict):
                input_data = {"body": input_data}
        except Exception:
            input_data = {}
    else:
        input_data = dict(request.query_params)

    logger.info("dynamic_endpoint_triggered", path=normalized_path, method=method, workflow_id=workflow.id)

    try:
        execution = await workflow_engine.execute(
            workflow=workflow,
            input_data=input_data,
            user_id=workflow.user_id,
            db=db,
        )
    except Exception as exc:
        logger.error("dynamic_endpoint_failed", path=normalized_path, error=str(exc), exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))

    return {
        "execution_id": execution.id,
        "status": execution.status,
        "output_data": execution.output_data,
    }
