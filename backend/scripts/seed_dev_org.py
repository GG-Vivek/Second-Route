#!/usr/bin/env python
"""
Seed a development organisation.

The tenant-isolation policies refuse a write that names no organisation,
so a developer needs an organisation to act for. This creates one and
prints its id, which is what the ``X-Org-Id`` header takes.

It is idempotent: running it twice leaves one organisation, with the same
id, so the id a developer has noted down keeps working.
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from sqlalchemy import select  # noqa: E402

from secondroute.core.db import close_db, init_db  # noqa: E402
from secondroute.identity.organizations import (  # noqa: E402
    Organization,
    ROLE_INSPECTOR,
    User,
)

#: The organisation every developer machine gets.
DEFAULT_ORG_NAME = "SecondRoute Development"


async def main() -> None:
    """Create the development organisation and a user in it."""
    await init_db()
    try:
        from secondroute.core.db import get_session_context

        async with get_session_context() as session:
            result = await session.execute(
                select(Organization).where(Organization.name == DEFAULT_ORG_NAME)
            )
            org = result.scalars().first()

            if org is None:
                org = Organization(name=DEFAULT_ORG_NAME, risk_profile="balanced")
                session.add(org)
                await session.flush()
                await session.refresh(org)

            user_result = await session.execute(
                select(User).where(User.email == "dev@secondroute.local")
            )
            user = user_result.scalars().first()
            if user is None:
                user = User(
                    org_id=org.id,
                    email="dev@secondroute.local",
                    role=ROLE_INSPECTOR,
                )
                session.add(user)

            await session.commit()
            await session.refresh(org)

            print(f"organisation: {org.name}")
            print(f"org id:       {org.id}")
            print(f"user:         {user.email}")
            print()
            print("Send this header with every request:")
            print(f"  {DEV_ORG_HEADER}: {org.id}")
    finally:
        await close_db()


DEV_ORG_HEADER = "X-Org-Id"


if __name__ == "__main__":
    asyncio.run(main())
