from datetime import datetime
from typing import Any, Dict, List, Optional

from fideslang.models import Cookies, PrivacyDeclaration, System
from pydantic import Field
from pydantic.main import BaseModel

from fides.api.schemas.connection_configuration.connection_config import (
    ConnectionConfigurationResponse,
)
from fides.api.schemas.user import UserResponse


class PrivacyDeclarationResponse(PrivacyDeclaration):
    """Extension of base pydantic model to include DB `id` field in the response"""

    id: str = Field(
        description="The database-assigned ID of the privacy declaration on the system. This is meant to be a read-only field, returned only in API responses"
    )
    cookies: Optional[List[Cookies]] = []


class SystemResponse(System):
    """Extension of base pydantic model to include additional fields like `privacy_declarations`, connection_config fields
    and cookies in responses"""

    privacy_declarations: List[PrivacyDeclarationResponse] = Field(
        description=PrivacyDeclarationResponse.__doc__,
    )

    connection_configs: Optional[ConnectionConfigurationResponse] = Field(
        description=ConnectionConfigurationResponse.__doc__,
    )

    data_stewards: Optional[List[UserResponse]] = Field(
        description="System managers of the current system",
    )

    cookies: Optional[List[Cookies]] = []

    created_at: datetime

    created_by: Optional[str] = Field(
        description="The username of the user who created the system"
    )


class SystemHistoryResponse(BaseModel):
    """Response schema for a single system history entry"""

    edited_by: Optional[str]
    system_key: str
    before: Dict[str, Any]
    after: Dict[str, Any]
    created_at: datetime

    class Config:
        orm_mode = True
