from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from agentrooms.models import Message, Participant, Room

PUBKEY_A = bytes(range(32))
PUBKEY_B = bytes(range(32, 64))
SIG_64 = bytes(range(64))


async def test_room_roundtrip(session):
    room = Room(
        topic="auth-ui integration",
        creator_pubkey=PUBKEY_A,
        turn_owner_pubkey=PUBKEY_A,
        ttl_until=datetime.now(UTC) + timedelta(hours=24),
    )
    session.add(room)
    await session.flush()
    room_id = room.id

    fetched = (await session.execute(select(Room).where(Room.id == room_id))).scalar_one()
    assert fetched.topic == "auth-ui integration"
    assert fetched.creator_pubkey == PUBKEY_A
    assert fetched.turn_owner_pubkey == PUBKEY_A
    assert fetched.status == "open"
    assert fetched.turn_n == 0
    assert fetched.max_turns == 40
    assert fetched.created_at is not None
    assert fetched.ttl_until > fetched.created_at


async def test_participant_roundtrip(session):
    room = Room(topic="t", creator_pubkey=PUBKEY_A)
    session.add(room)
    await session.flush()

    p = Participant(
        room_id=room.id,
        agent_pubkey=PUBKEY_B,
        owner_pubkey=PUBKEY_B,
        invited_by_pubkey=PUBKEY_A,
    )
    session.add(p)
    await session.flush()

    fetched = (
        await session.execute(select(Participant).where(Participant.id == p.id))
    ).scalar_one()
    assert fetched.agent_pubkey == PUBKEY_B
    assert fetched.invited_by_pubkey == PUBKEY_A
    assert fetched.accepted_at is None
    assert fetched.accept_sig is None


async def test_participant_unique_per_room(session):
    room = Room(topic="t", creator_pubkey=PUBKEY_A)
    session.add(room)
    await session.flush()

    session.add(
        Participant(
            room_id=room.id,
            agent_pubkey=PUBKEY_B,
            owner_pubkey=PUBKEY_B,
            invited_by_pubkey=PUBKEY_A,
        )
    )
    await session.flush()

    session.add(
        Participant(
            room_id=room.id,
            agent_pubkey=PUBKEY_B,
            owner_pubkey=PUBKEY_B,
            invited_by_pubkey=PUBKEY_A,
        )
    )
    import pytest
    from sqlalchemy.exc import IntegrityError

    with pytest.raises(IntegrityError):
        await session.flush()


async def test_message_roundtrip(session):
    room = Room(topic="t", creator_pubkey=PUBKEY_A)
    session.add(room)
    await session.flush()

    msg = Message(
        room_id=room.id,
        author_pubkey=PUBKEY_A,
        turn_n=1,
        body="hello",
        sig=SIG_64,
    )
    session.add(msg)
    await session.flush()

    fetched = (await session.execute(select(Message).where(Message.id == msg.id))).scalar_one()
    assert fetched.body == "hello"
    assert fetched.turn_n == 1
    assert fetched.sig == SIG_64
    assert fetched.created_at is not None


async def test_message_unique_turn_per_room(session):
    room = Room(topic="t", creator_pubkey=PUBKEY_A)
    session.add(room)
    await session.flush()

    session.add(
        Message(room_id=room.id, author_pubkey=PUBKEY_A, turn_n=1, body="a", sig=SIG_64)
    )
    await session.flush()

    session.add(
        Message(room_id=room.id, author_pubkey=PUBKEY_B, turn_n=1, body="b", sig=SIG_64)
    )
    import pytest
    from sqlalchemy.exc import IntegrityError

    with pytest.raises(IntegrityError):
        await session.flush()
