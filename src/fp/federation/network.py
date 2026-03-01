"""Network discovery and remote call helpers for federated FP deployments."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from threading import RLock
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from uuid import uuid4

from fp.protocol import FPError, FPErrorCode


@dataclass(slots=True)
class FPServerCard:
    card_id: str
    entity_id: str
    fp_version: str
    rpc_url: str
    well_known_url: str
    capabilities: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.card_id.strip():
            raise FPError(FPErrorCode.INVALID_ARGUMENT, "card_id must be non-empty")
        if not self.entity_id.strip():
            raise FPError(FPErrorCode.INVALID_ARGUMENT, "entity_id must be non-empty")
        if not self.fp_version.strip():
            raise FPError(FPErrorCode.INVALID_ARGUMENT, "fp_version must be non-empty")
        if not self.rpc_url.strip():
            raise FPError(FPErrorCode.INVALID_ARGUMENT, "rpc_url must be non-empty")
        if not self.well_known_url.strip():
            raise FPError(FPErrorCode.INVALID_ARGUMENT, "well_known_url must be non-empty")

    def to_dict(self) -> dict[str, Any]:
        return {
            "card_id": self.card_id,
            "entity_id": self.entity_id,
            "fp_version": self.fp_version,
            "rpc_url": self.rpc_url,
            "well_known_url": self.well_known_url,
            "capabilities": dict(self.capabilities),
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "FPServerCard":
        if not isinstance(value, dict):
            raise FPError(FPErrorCode.INVALID_ARGUMENT, "server card payload must be an object")
        return cls(
            card_id=str(value["card_id"]),
            entity_id=str(value["entity_id"]),
            fp_version=str(value["fp_version"]),
            rpc_url=str(value["rpc_url"]),
            well_known_url=str(value["well_known_url"]),
            capabilities=dict(value.get("capabilities", {})),
            metadata=dict(value.get("metadata", {})),
        )


class InMemoryDirectory:
    """Simple directory for publishing and discovering FP server cards by entity."""

    def __init__(self) -> None:
        self._lock = RLock()
        self._cards_by_entity: dict[str, FPServerCard] = {}

    def publish(self, card: FPServerCard) -> None:
        with self._lock:
            if card.entity_id in self._cards_by_entity:
                raise FPError(FPErrorCode.ALREADY_EXISTS, f"server already published for entity: {card.entity_id}")
            self._cards_by_entity[card.entity_id] = FPServerCard.from_dict(card.to_dict())

    def resolve(self, entity_id: str) -> FPServerCard:
        with self._lock:
            card = self._cards_by_entity.get(entity_id)
        if card is None:
            raise FPError(FPErrorCode.NOT_FOUND, f"server card not found for entity: {entity_id}")
        return FPServerCard.from_dict(card.to_dict())

    def list(self) -> list[FPServerCard]:
        with self._lock:
            return [FPServerCard.from_dict(card.to_dict()) for card in self._cards_by_entity.values()]


class RemoteFPClient:
    """HTTP JSON-RPC client for remote FP servers."""

    def __init__(self, rpc_url: str, *, timeout_seconds: float = 10.0, headers: dict[str, str] | None = None) -> None:
        if not rpc_url:
            raise FPError(FPErrorCode.INVALID_ARGUMENT, "rpc_url must be non-empty")
        self._rpc_url = rpc_url
        self._timeout = timeout_seconds
        self._headers = {"Content-Type": "application/json", **(headers or {})}

    @property
    def rpc_url(self) -> str:
        return self._rpc_url

    def call(self, method: str, params: dict[str, Any] | None = None) -> Any:
        request_id = f"req-{uuid4().hex}"
        payload = {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": method,
            "params": params or {},
        }
        raw = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        request = Request(self._rpc_url, data=raw, headers=self._headers, method="POST")
        try:
            with urlopen(request, timeout=self._timeout) as response:
                response_body = response.read()
        except HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise FPError(
                FPErrorCode.INTERNAL_ERROR,
                message="remote FP server returned HTTP error",
                details={"status": exc.code, "url": self._rpc_url, "detail": detail},
            ) from exc
        except URLError as exc:
            raise FPError(
                FPErrorCode.INTERNAL_ERROR,
                message="failed to reach remote FP server",
                details={"url": self._rpc_url, "detail": str(exc.reason)},
                retryable=True,
            ) from exc

        if not response_body:
            return None
        try:
            decoded = json.loads(response_body.decode("utf-8"))
        except json.JSONDecodeError as exc:
            raise FPError(FPErrorCode.INTERNAL_ERROR, "remote FP server returned non-JSON response") from exc

        if not isinstance(decoded, dict):
            raise FPError(FPErrorCode.INTERNAL_ERROR, "remote FP server returned malformed response")
        if "error" in decoded and isinstance(decoded["error"], dict):
            raise self._map_remote_error(decoded["error"])
        return decoded.get("result")

    def ping(self) -> dict[str, Any]:
        result = self.call("fp/ping", {})
        if not isinstance(result, dict):
            raise FPError(FPErrorCode.INTERNAL_ERROR, "remote ping response is malformed")
        return result

    @staticmethod
    def _map_remote_error(error_payload: dict[str, Any]) -> FPError:
        data = error_payload.get("data")
        if isinstance(data, dict):
            fp = data.get("fp")
            if isinstance(fp, dict):
                code_raw = fp.get("code")
                if isinstance(code_raw, str) and code_raw in {code.value for code in FPErrorCode}:
                    code = FPErrorCode(code_raw)
                    message = fp.get("message")
                    details = fp.get("details", {})
                    retryable = bool(fp.get("retryable", False))
                    return FPError(code=code, message=message, details=dict(details), retryable=retryable)
        return FPError(
            FPErrorCode.INTERNAL_ERROR,
            message=error_payload.get("message", "remote call failed"),
            details={"remote_error": error_payload},
        )


class NetworkResolver:
    """Resolve entity -> FP server card -> remote client."""

    def __init__(self, directory: InMemoryDirectory) -> None:
        self._directory = directory

    def discover(self, entity_id: str) -> FPServerCard:
        return self._directory.resolve(entity_id)

    def connect(self, entity_id: str, *, timeout_seconds: float = 10.0) -> RemoteFPClient:
        card = self.discover(entity_id)
        return RemoteFPClient(card.rpc_url, timeout_seconds=timeout_seconds)


def fetch_server_card(well_known_url: str, *, timeout_seconds: float = 10.0) -> FPServerCard:
    request = Request(well_known_url, method="GET")
    try:
        with urlopen(request, timeout=timeout_seconds) as response:
            payload = response.read()
    except HTTPError as exc:
        raise FPError(
            FPErrorCode.NOT_FOUND,
            message="failed to fetch server card",
            details={"status": exc.code, "url": well_known_url},
        ) from exc
    except URLError as exc:
        raise FPError(
            FPErrorCode.INTERNAL_ERROR,
            message="failed to reach server card endpoint",
            details={"url": well_known_url, "detail": str(exc.reason)},
            retryable=True,
        ) from exc

    try:
        decoded = json.loads(payload.decode("utf-8"))
    except json.JSONDecodeError as exc:
        raise FPError(FPErrorCode.INTERNAL_ERROR, "server card response is not valid JSON") from exc
    return FPServerCard.from_dict(decoded)
