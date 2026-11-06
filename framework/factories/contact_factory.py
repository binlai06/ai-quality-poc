"""Builds unique, valid contact form data for tests."""

import uuid
from typing import Any

from faker import Faker

from framework.models.message import ContactPayload


class ContactFactory:
    """Creates contact form data. Name and subject carry a unique tag.

    The subject is what cleanup uses to find the message, so it must be unique per call.
    Field sizes follow the message service rules (phone 11-21, subject 5-100, body 20-2000).
    """

    _fake = Faker()

    @classmethod
    def build(cls, **overrides: Any) -> ContactPayload:
        tag = uuid.uuid4().hex[:8]
        fields: dict[str, Any] = {
            "name": f"qa-{tag}",
            "email": f"qa-{tag}@example.com",
            "phone": f"0{cls._fake.random_number(digits=10, fix_len=True)}",
            "subject": f"qa-subject-{tag}",
            "description": cls._fake.sentence(nb_words=12),
        }
        fields.update(overrides)
        return ContactPayload(**fields)
