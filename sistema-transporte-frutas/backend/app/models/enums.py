from enum import StrEnum


class UserRole(StrEnum):
    ADMIN = "admin"
    OPERATOR = "operador"
    DRIVER = "chofer"
    CLIENT = "cliente"


class LoadStatus(StrEnum):
    PENDING = "pendiente"
    ASSIGNED = "asignada"
    IN_TRANSIT = "en_transito"
    DELIVERED = "entregada"
    CANCELED = "cancelada"


class TripStatus(StrEnum):
    SCHEDULED = "programado"
    IN_PROGRESS = "en_curso"
    COMPLETED = "entregado"
    CANCELED = "cancelado"
    INCIDENT = "incidencia"


class Priority(StrEnum):
    LOW = "baja"
    NORMAL = "normal"
    HIGH = "alta"
    URGENT = "urgente"


class QuotationStatus(StrEnum):
    DRAFT = "borrador"
    SENT = "enviada"
    APPROVED = "aprobada"
    REJECTED = "rechazada"
    CONVERTED = "convertida_a_carga"
