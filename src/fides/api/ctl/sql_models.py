# type: ignore

"""
Contains all of the SqlAlchemy models for the Fides resources.
"""

from __future__ import annotations

from enum import Enum as EnumType
from typing import Any, Dict, List, Optional, Set, Type

from fideslang.models import Dataset as FideslangDataset
from pydantic import BaseModel
from sqlalchemy import ARRAY, BOOLEAN, JSON, Column
from sqlalchemy import Enum as EnumColumn
from sqlalchemy import (
    ForeignKey,
    Integer,
    String,
    Text,
    TypeDecorator,
    UniqueConstraint,
    cast,
    type_coerce,
)
from sqlalchemy.dialects.postgresql import BYTEA
from sqlalchemy.orm import Session, relationship
from sqlalchemy.sql import func
from sqlalchemy.sql.sqltypes import DateTime

from fides.core.config import CONFIG
from fides.lib.db.base import (  # type: ignore[attr-defined]
    Base,
    ClientDetail,
    FidesUser,
    FidesUserPermissions,
)
from fides.lib.db.base_class import FidesBase as FideslibBase


class FidesBase(FideslibBase):
    """
    The base SQL model for all top-level Fides Resources.
    """

    fides_key = Column(String, primary_key=True, index=True, unique=True)
    organization_fides_key = Column(Text)
    tags = Column(ARRAY(String))
    name = Column(Text)
    description = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )


class PGEncryptedString(TypeDecorator):
    """
    This TypeDecorator handles encrypting and decrypting values at rest
    on the database that would normally be stored as json.

    The values are explicitly cast as json then text to take advantage of
    the pgcrypto extension.
    """

    impl = BYTEA
    python_type = String

    cache_ok = True

    def __init__(self):
        super().__init__()

        self.passphrase = CONFIG.user.encryption_key

    def bind_expression(self, bindparam):
        # Needs to be a string for the encryption, however it also needs to be treated as JSON first

        bindparam = type_coerce(bindparam, JSON)

        return func.pgp_sym_encrypt(cast(bindparam, Text), self.passphrase)

    def column_expression(self, column):
        return cast(func.pgp_sym_decrypt(column, self.passphrase), JSON)

    def process_bind_param(self, value, dialect):
        pass

    def process_literal_param(self, value, dialect):
        pass

    def process_result_value(self, value, dialect):
        pass


class ClassificationDetail(Base):
    """
    The SQL model for a classification instance
    """

    __tablename__ = "cls_classification_detail"
    instance_id = Column(String(255))
    status = Column(Text)
    dataset = Column(Text)
    collection = Column(Text)
    field = Column(Text)
    labels = Column(JSON)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )
    # get the details from a classification json output (likely aggregate and options etc.)


class ClassificationInstance(Base):
    """
    The SQL model for a classification instance
    """

    __tablename__ = "cls_classification_instance"

    status = Column(Text)
    organization_key = Column(Text)
    dataset_key = Column(Text)
    dataset_name = Column(Text)
    target = Column(Text)
    type = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )


# Privacy Types
class DataCategory(Base, FidesBase):
    """
    The SQL model for the DataCategory resource.
    """

    __tablename__ = "ctl_data_categories"

    parent_key = Column(Text)
    is_default = Column(BOOLEAN, default=False)


class DataQualifier(Base, FidesBase):
    """
    The SQL model for the DataQualifier resource.
    """

    __tablename__ = "ctl_data_qualifiers"

    parent_key = Column(Text)
    is_default = Column(BOOLEAN, default=False)


class DataSubject(Base, FidesBase):
    """
    The SQL model for the DataSubject resource.
    """

    __tablename__ = "ctl_data_subjects"
    rights = Column(JSON, nullable=True)
    automated_decisions_or_profiling = Column(BOOLEAN, nullable=True)
    is_default = Column(BOOLEAN, default=False)


class DataUse(Base, FidesBase):
    """
    The SQL model for the DataUse resource.
    """

    __tablename__ = "ctl_data_uses"

    parent_key = Column(Text)
    legal_basis = Column(Text)
    special_category = Column(Text)
    recipients = Column(ARRAY(String))
    legitimate_interest = Column(BOOLEAN, nullable=True)
    legitimate_interest_impact_assessment = Column(String, nullable=True)
    is_default = Column(BOOLEAN, default=False)

    privacy_declarations = relationship(
        "PrivacyDeclaration",
        back_populates="data_use_object",
        cascade="all, delete-orphan",
    )

    def get_parent_uses(self) -> Set[str]:
        """
        Utility method to traverse "up" the taxonomy hierarchy and unpack
        a given data use fides key into a set of fides keys that include its
        parent fides keys.

        The utility takes a fides key string input to make the method more applicable -
        since in many spots of our application we do not have a true `DataUse` instance,
        just a "soft" reference to its fides key.

        Example inputs and outputs:
            - `a.b.c` --> [`a.b.c`, `a.b`, `a`]
            - `a` --> [`a`]
        """
        return DataUse.get_parent_uses_from_key(self.fides_key)

    @staticmethod
    def get_parent_uses_from_key(data_use_key: str) -> Set[str]:
        """
        Utility method to traverse "up" the taxonomy hierarchy and unpack
        a given data use fides key into a set of fides keys that include its
        parent fides keys.

        The utility takes a fides key string input to make the method more applicable -
        since in many spots of our application we do not have a true `DataUse` instance,
        just a "soft" reference to its fides key.

        Example inputs and outputs:
            - `a.b.c` --> [`a.b.c`, `a.b`, `a`]
            - `a` --> [`a`]
        """
        parent_uses = {data_use_key}
        while data_use_key := data_use_key.rpartition(".")[0]:
            parent_uses.add(data_use_key)
        return parent_uses


# Dataset
class Dataset(Base, FidesBase):
    """
    The SQL model for the Dataset resource.
    """

    __tablename__ = "ctl_datasets"

    meta = Column(JSON)
    data_categories = Column(ARRAY(String))
    data_qualifier = Column(String)
    collections = Column(JSON)
    fides_meta = Column(JSON)
    joint_controller = Column(PGEncryptedString, nullable=True)
    retention = Column(String)
    third_country_transfers = Column(ARRAY(String))

    @classmethod
    def create_from_dataset_dict(cls, db: Session, dataset: dict) -> "Dataset":
        """Add a method to create directly using a synchronous session"""
        validated_dataset: FideslangDataset = FideslangDataset(**dataset)
        ctl_dataset = cls(**validated_dataset.dict())
        db.add(ctl_dataset)
        db.commit()
        db.refresh(ctl_dataset)
        return ctl_dataset


# Evaluation
class Evaluation(Base):
    """
    The SQL model for the Evaluation resource.
    """

    __tablename__ = "ctl_evaluations"

    fides_key = Column(String, primary_key=True, index=True, unique=True)
    status = Column(String)
    violations = Column(JSON)
    message = Column(String)


# Organization
class Organization(Base, FidesBase):
    """
    The SQL model for the Organization resource.
    """

    # It inherits this from FidesModel but Organization's don't have this field
    __tablename__ = "ctl_organizations"

    organization_parent_key = Column(String, nullable=True)
    controller = Column(PGEncryptedString, nullable=True)
    data_protection_officer = Column(PGEncryptedString, nullable=True)
    fidesctl_meta = Column(JSON)
    representative = Column(PGEncryptedString, nullable=True)
    security_policy = Column(String, nullable=True)


# Policy
class PolicyCtl(Base, FidesBase):
    """
    The SQL model for the Policy resource.
    """

    __tablename__ = "ctl_policies"

    rules = Column(JSON)


# Registry
class Registry(Base, FidesBase):
    """
    The SQL model for the Registry resource.
    """

    __tablename__ = "ctl_registries"


# System
class System(Base, FidesBase):
    """
    The SQL model for the system resource.
    """

    __tablename__ = "ctl_systems"

    registry_id = Column(String)
    meta = Column(JSON)
    fidesctl_meta = Column(JSON)
    system_type = Column(String)
    data_responsibility_title = Column(String)
    system_dependencies = Column(ARRAY(String))
    joint_controller = Column(PGEncryptedString, nullable=True)
    third_country_transfers = Column(ARRAY(String))
    administrating_department = Column(String)
    data_protection_impact_assessment = Column(JSON)
    egress = Column(JSON)
    ingress = Column(JSON)

    privacy_declarations = relationship(
        "PrivacyDeclaration",
        cascade="all, delete",
        back_populates="system",
        lazy="selectin",
    )

    users = relationship(
        "FidesUser",
        secondary="systemmanager",
        back_populates="systems",
        lazy="selectin",
    )

    @staticmethod
    def collapse_data_uses(
        privacy_declarations: List[PrivacyDeclaration], include_parents: bool
    ) -> Set:
        """Helper method to collapse the data uses off of multiple privacy declarations into a Set

        The `include_parents` arg determines whether the method traverses "up" the data use hierarchy
        to also return all _parent_ data uses of the specific data uses associated with a given system.
        This can be useful if/when we consider these parent data uses as applicable to a system.
        """
        data_uses = set()
        for declaration in privacy_declarations:
            if data_use := declaration.data_use_object:
                if include_parents:
                    data_uses.update(data_use.get_parent_uses())
                else:
                    data_uses.add(data_use.fides_key)
        return data_uses

    @classmethod
    def get_system_data_uses(
        cls: Type[System], db: Session, include_parents: bool = True
    ) -> set[str]:
        """
        Utility method to get any data use that is associated with at least one System
        """
        data_uses = set()
        for row in db.query(System).all():
            data_uses.update(
                cls.collapse_data_uses(row.privacy_declarations, include_parents)
            )
        return data_uses

    def get_data_uses(self, include_parents: bool = True) -> set[str]:
        """Utility method to get all the data uses off the current System"""
        return self.collapse_data_uses(self.privacy_declarations or [], include_parents)


class PrivacyDeclaration(Base):
    """
    The SQL model for a Privacy Declaration associated with a given System.
    """

    name = Column(String)  # Processing Activity
    data_categories = Column(ARRAY(String))  # TODO: maybe relationship?
    data_qualifier = Column(String)  # TODO: maybe relationship? is this needed?
    data_subjects = Column(ARRAY(String))  # TODO: maybe relationship?
    dataset_references = Column(ARRAY(String))  # TODO: maybe relationship?
    egress = Column(JSON)  # TODO: needed?
    ingress = Column(JSON)  # TODO: needed?

    system_id = Column(
        String,
        ForeignKey(System.fides_key, ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
        index=True,
    )
    system = relationship(System, back_populates="privacy_declarations")

    # the FK column is just plain `data_use` to align with the `FidesKey` field on the pydantic model
    data_use = Column(String, ForeignKey(DataUse.fides_key), nullable=False, index=True)
    data_use_object = relationship(DataUse)

    @classmethod
    def create(
        cls: Type[PrivacyDeclaration],
        db: Session,
        *,
        data: dict[str, Any],
        check_name: bool = False,  # this is the reason for the override
    ) -> PrivacyDeclaration:
        """Overrides baes create to avoid unique check on `name` column"""
        return super().create(db=db, data=data, check_name=check_name)


class SystemModel(BaseModel):
    fides_key: str
    registry_id: str
    meta: Optional[Dict[str, Any]]
    fidesctl_meta: Optional[Dict[str, Any]]
    system_type: str
    data_responsibility_title: Optional[str]
    system_dependencies: Optional[List[str]]
    joint_controller: Optional[str]
    third_country_transfers: Optional[List[str]]
    privacy_declarations: Optional[Dict[str, Any]]
    administrating_department: Optional[str]
    data_protection_impact_assessment: Optional[Dict[str, Any]]
    egress: Optional[Dict[str, Any]]
    ingress: Optional[Dict[str, Any]]
    value: Optional[List[Any]]


class SystemScans(Base):
    """
    The SQL model for System Scan instances.
    """

    __tablename__ = "plus_system_scans"

    id = Column(Integer, primary_key=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    error = Column(String, nullable=True)
    is_classified = Column(BOOLEAN, default=False, nullable=False)
    result = Column(JSON, nullable=True)
    status = Column(String, nullable=False)
    system_count = Column(Integer, autoincrement=False, nullable=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now())


sql_model_map: Dict = {
    "client_detail": ClientDetail,
    "data_category": DataCategory,
    "data_qualifier": DataQualifier,
    "data_subject": DataSubject,
    "data_use": DataUse,
    "dataset": Dataset,
    "fides_user": FidesUser,
    "fides_user_permissions": FidesUserPermissions,
    "organization": Organization,
    "policy": PolicyCtl,
    "registry": Registry,
    "system": System,
    "evaluation": Evaluation,
}

models_with_default_field = [
    sql_model
    for _, sql_model in sql_model_map.items()
    if hasattr(sql_model, "is_default")
]


class AllowedTypes(str, EnumType):
    """Allowed types for custom field."""

    string = "string"
    string_list = "string[]"


class ResourceTypes(str, EnumType):
    """Resource types that can use custom fields."""

    system = "system"
    data_use = "data use"
    data_category = "data category"
    data_subject = "data subject"


class CustomFieldValueList(Base):
    """Allow-list definitions for custom metadata values"""

    __tablename__ = "plus_custom_field_value_list"

    name = Column(String, nullable=False)
    description = Column(String)
    allowed_values = Column(ARRAY(String))
    custom_field_definition = relationship(
        "CustomFieldDefinition",
        back_populates="allow_list",
    )

    UniqueConstraint("name")


class CustomFieldDefinition(Base):
    """Defines custom metadata for resources."""

    __tablename__ = "plus_custom_field_definition"

    name = Column(String, index=True, nullable=False)
    description = Column(String)
    field_type = Column(
        EnumColumn(AllowedTypes),
        nullable=False,
    )
    allow_list_id = Column(String, ForeignKey(CustomFieldValueList.id), nullable=True)
    resource_type = Column(EnumColumn(ResourceTypes), nullable=False)
    field_definition = Column(String, index=True)
    custom_field = relationship(
        "CustomField",
        back_populates="custom_field_definition",
        cascade="delete, delete-orphan",
    )
    allow_list = relationship(
        "CustomFieldValueList",
        back_populates="custom_field_definition",
    )
    active = Column(BOOLEAN, nullable=False, default=True)

    UniqueConstraint("name", "resource_type")


class CustomField(Base):
    """Custom metadata for resources."""

    __tablename__ = "plus_custom_field"

    resource_type = Column(EnumColumn(ResourceTypes), nullable=False)
    resource_id = Column(String, index=True, nullable=False)
    custom_field_definition_id = Column(
        String, ForeignKey(CustomFieldDefinition.id), nullable=False
    )
    value = Column(ARRAY(String))

    custom_field_definition = relationship(
        "CustomFieldDefinition",
        back_populates="custom_field",
    )

    UniqueConstraint("resource_type", "resource_id", "custom_field_definition_id")
