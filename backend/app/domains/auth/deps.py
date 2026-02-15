from __future__ import annotations

from typing import Annotated

from fastapi import Depends

from app.core.deps import get_current_user
from app.domains.auth.models import User

# Typed dependency that resolves to a User instance.
# Use this in route signatures: `user: CurrentUser`
CurrentUser = Annotated[User, Depends(get_current_user)]
