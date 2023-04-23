from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend import models, schemas, crud
from backend.api import deps
from backend.core import logger
from backend.utils import calendar_template_utils

router = APIRouter()


@router.post('/', response_model=schemas.CalendarTemplate)
def create_new_calendar_template(calendar_template: schemas.CalendarTemplateCreate,
                                 db: Session = Depends(deps.get_db),
                                 current_user: models.User = Depends(deps.get_current_active_user)):
    existing_template: Optional[models.CalendarTemplate] = \
        crud.calendar_template.get_template_by_type(db, current_user.id, calendar_template.type)

    if existing_template is not None:
        logger.error(f'Failed to update calendar template {calendar_template} for user: {current_user.id} because '
                     f'the user already has a template of type: {calendar_template.type} '
                     f'here: {existing_template}')
        raise HTTPException(status_code=400, detail="Failed to create new template. Template type already exists.")

    _validate_template(calendar_template)

    template = crud.calendar_template.create_and_add_to_user(db, current_user.id, calendar_template)
    return template


@router.post('/{id}', response_model=schemas.CalendarTemplate)
def update_calendar_template(template_updates: schemas.CalendarTemplateUpdate,
                             id: str,
                             db: Session = Depends(deps.get_db),
                             current_user: models.User = Depends(deps.get_current_active_user)):
    existing_template: Optional[models.CalendarTemplate] = crud.calendar_template.get(db=db, id=id)

    if existing_template is None:
        raise HTTPException(status_code=400, detail="Invalid template id.")

    if existing_template.user_id != current_user.id:
        raise HTTPException(status_code=401, detail="You do not have the permission to modify this template.")

    _validate_template(template_updates)
    template = crud.calendar_template.update(db=db, db_obj=existing_template, obj_in=template_updates)
    return template


def _validate_template(template: schemas.CalendarTemplateBase) -> [Optional[str]]:
    invalid_title_keys: [str] = []
    invalid_body_keys: [str] = []

    if template.title_template:
        invalid_title_keys = calendar_template_utils.verify_template(template.title_template, template.type)
    if template.body_template:
        invalid_body_keys = calendar_template_utils.verify_template(template.body_template, template.type)

    if invalid_title_keys or invalid_body_keys:
        errs: [str] = ["Failed to create new calendar template."]
        errs.append(f"Invalid title keys: {', '.join(invalid_title_keys)}.") if invalid_title_keys else None
        errs.append(f"Invalid calendar template keys: {', '.join(invalid_body_keys)}.") if invalid_body_keys else None
        raise HTTPException(status_code=400, detail=" ".join(errs))
