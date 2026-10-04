"""Phase 3 project management. Ingestion is deliberately not implemented here."""
import secrets
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field
from app.auth import db, digest, me, same_origin

router = APIRouter(prefix='/api/v1/projects', tags=['projects'])


class ProjectCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra='forbid')
    name: str = Field(min_length=1, max_length=100)


def current_user(request: Request, connection=Depends(db)):
    # Only a live login cookie authorizes project reads; ingestion keys never do.
    return me(request, connection)['user']


def new_key(connection, project_id):
    plaintext = 'trc_' + secrets.token_urlsafe(32)
    key = connection.execute('''INSERT INTO project_keys(id,project_id,key_prefix,key_hash)
        VALUES (%s,%s,%s,%s) RETURNING id,key_prefix,created_at''',
        (uuid4(), project_id, plaintext[:12], digest(plaintext))).fetchone()
    return {**key, 'ingestion_key': plaintext}


@router.get('')
def list_projects(user=Depends(current_user), connection=Depends(db)):
    rows = connection.execute('''SELECT p.id,p.name,p.created_at,k.key_prefix,k.created_at AS key_created_at
        FROM projects p LEFT JOIN project_keys k ON k.project_id=p.id AND k.revoked_at IS NULL
        WHERE p.owner_id=%s ORDER BY p.created_at DESC,p.id''', (user['id'],)).fetchall()
    return {'projects': rows}


@router.post('', status_code=201, dependencies=[Depends(same_origin)])
def create_project(body: ProjectCreate, user=Depends(current_user), connection=Depends(db)):
    project = connection.execute('''INSERT INTO projects(id,owner_id,name) VALUES (%s,%s,%s)
        RETURNING id,name,created_at''', (uuid4(), user['id'], body.name)).fetchone()
    key = new_key(connection, project['id'])
    return {'project': project, **key}


@router.post('/{project_id}/keys/rotate', dependencies=[Depends(same_origin)])
def rotate_key(project_id: UUID, user=Depends(current_user), connection=Depends(db)):
    # Serialize concurrent rotations so revocation and replacement are atomic.
    project = connection.execute('SELECT id,name FROM projects WHERE id=%s AND owner_id=%s FOR UPDATE',
                                 (project_id, user['id'])).fetchone()
    if not project:
        raise HTTPException(404, 'Project not found')
    connection.execute('UPDATE project_keys SET revoked_at=now() WHERE project_id=%s AND revoked_at IS NULL', (project_id,))
    return {'project': project, **new_key(connection, project_id)}
