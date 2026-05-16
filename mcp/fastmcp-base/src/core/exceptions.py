class MCPServerError(Exception):
    pass


class DatabaseConnectionError(MCPServerError):
    pass


class ResourceNotFoundError(MCPServerError):
    pass


class ExternalAPIError(MCPServerError):
    pass


class ValidationError(MCPServerError):
    pass
