"""API contract design for System Architect Agent."""

from codeforge.artifacts.prd import PRD
from codeforge.artifacts.tech_spec import APIEndpoint, DataEntity


class APIContractDesigner:
    """Creates REST-style endpoint contracts from entities."""

    def design(self, prd: PRD, entities: list[DataEntity]) -> list[APIEndpoint]:
        endpoints = [
            APIEndpoint("GET", "/health", "Health check", response_schema={"status": "string"}),
        ]

        for entity in entities:
            resource = entity.name.lower() + "s"
            if entity.name == "User":
                continue
            endpoints.extend(
                [
                    APIEndpoint("GET", f"/{resource}", f"List {resource}", auth_required=True),
                    APIEndpoint(
                        "POST",
                        f"/{resource}",
                        f"Create {entity.name}",
                        request_schema={
                            field.name: field.type
                            for field in entity.fields
                            if field.name != "id"
                        },
                        response_schema={field.name: field.type for field in entity.fields},
                        auth_required=True,
                    ),
                    APIEndpoint(
                        "GET", f"/{resource}/{{id}}", f"Get {entity.name}", auth_required=True
                    ),
                    APIEndpoint(
                        "PUT",
                        f"/{resource}/{{id}}",
                        f"Update {entity.name}",
                        auth_required=True,
                    ),
                    APIEndpoint(
                        "DELETE",
                        f"/{resource}/{{id}}",
                        f"Delete {entity.name}",
                        auth_required=True,
                    ),
                ]
            )

        if any("export" in feature for feature in prd.scope.in_scope):
            endpoints.append(
                APIEndpoint(
                    "GET",
                    "/export",
                    "Export user data",
                    response_schema={"csv": "string"},
                    auth_required=True,
                )
            )
        return endpoints
