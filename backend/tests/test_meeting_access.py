from __future__ import annotations

from app.models import Meeting, User
from app.routers.meetings import _can_access_meeting


def test_member_cannot_access_other_meeting():
    owner = User(name="Owner", email="o@bocaboca.pt", role="member")
    owner.id = "owner-1"
    other = User(name="Other", email="x@bocaboca.pt", role="member")
    other.id = "other-1"
    meeting = Meeting(client_name="C", title="T", owner_id=owner.id)

    assert _can_access_meeting(meeting, owner) is True
    assert _can_access_meeting(meeting, other) is False


def test_admin_can_access_any_meeting():
    admin = User(name="Admin", email="a@bocaboca.pt", role="admin")
    admin.id = "admin-1"
    meeting = Meeting(client_name="C", title="T", owner_id="someone-else")

    assert _can_access_meeting(meeting, admin) is True


def test_orphan_meeting_not_shared():
    member = User(name="M", email="m@bocaboca.pt", role="member")
    member.id = "m-1"
    meeting = Meeting(client_name="C", title="T", owner_id=None)

    assert _can_access_meeting(meeting, member) is False
