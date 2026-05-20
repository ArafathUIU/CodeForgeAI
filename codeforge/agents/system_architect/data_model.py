"""Data model design for System Architect Agent."""

import re

from codeforge.artifacts.prd import PRD
from codeforge.artifacts.tech_spec import DataEntity, DataField


class DataModelDesigner:
    """Derives simple entities from product requirements."""

    def design(self, prd: PRD) -> list[DataEntity]:
        entities = [
            DataEntity(
                name="User",
                fields=[
                    DataField("id", "integer", indexed=True, description="Primary key"),
                    DataField("email", "string", indexed=True, description="Unique user email"),
                    DataField("created_at", "datetime", description="Creation timestamp"),
                ],
            )
        ]

        feature_names = [self._entity_name(story.capability) for story in prd.user_stories]
        for name in sorted(set(feature_names)):
            if name == "User":
                continue
            entities.append(
                DataEntity(
                    name=name,
                    fields=[
                        DataField("id", "integer", indexed=True, description="Primary key"),
                        DataField("user_id", "integer", indexed=True, description="Owner user ID"),
                        DataField("title", "string", description="Human-readable label"),
                        DataField(
                            "metadata",
                            "json",
                            required=False,
                            description="Feature-specific data",
                        ),
                        DataField("created_at", "datetime", description="Creation timestamp"),
                    ],
                    relationships=["belongs_to User"],
                )
            )
        return entities

    def _entity_name(self, capability: str) -> str:
        words = re.findall(r"[A-Za-z0-9]+", capability)
        if not words:
            return "Item"
        core = words[-1] if words[-1].lower() not in {"workflow", "view"} else words[0]
        return core.rstrip("s").capitalize() or "Item"
