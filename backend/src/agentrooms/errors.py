"""Centralized HTTPException factories so router code stays clean."""

from fastapi import HTTPException, status


def bad_signature() -> HTTPException:
    return HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid signature")


def not_a_participant() -> HTTPException:
    return HTTPException(status.HTTP_403_FORBIDDEN, "not a participant of this room")


def not_turn_owner() -> HTTPException:
    return HTTPException(status.HTTP_403_FORBIDDEN, "not your turn")


def room_not_found() -> HTTPException:
    return HTTPException(status.HTTP_404_NOT_FOUND, "room not found")


def room_closed() -> HTTPException:
    return HTTPException(status.HTTP_409_CONFLICT, "room is closed or expired")


def turn_conflict(expected: int, got: int) -> HTTPException:
    return HTTPException(
        status.HTTP_409_CONFLICT, f"turn_n conflict: expected {expected}, got {got}"
    )


def stale_timestamp() -> HTTPException:
    return HTTPException(status.HTTP_400_BAD_REQUEST, "created_at outside acceptable window")


def body_too_large() -> HTTPException:
    return HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "message body too large")


def invalid_pubkey() -> HTTPException:
    return HTTPException(status.HTTP_400_BAD_REQUEST, "invalid pubkey")
