"""
Sign-up and sign-in for retailers and their staff (F11.1).

A retailer signs up and becomes an organisation with an administrator. A person
joins that organisation with its code. Both then sign in with a password.
"""

import uuid

import pytest
from httpx import AsyncClient

RETAILER = {
    "organisation_name": "Harbour Electronics",
    "display_name": "Ada Okafor",
    "email": "Ada@Harbour.example",
    "password": "correct horse 42",
    "risk_profile": "balanced",
}


@pytest.mark.asyncio
async def test_retailer_sign_up_makes_an_organisation_and_an_administrator(
    client: AsyncClient,
) -> None:
    response = await client.post("/api/v1/auth/signup/retailer", json=RETAILER)
    assert response.status_code == 201
    body = response.json()
    assert body["role"] == "admin"
    assert body["organisation_name"] == "Harbour Electronics"
    # Email addresses are kept in one case, so a sign-in in another still matches.
    assert body["email"] == "ada@harbour.example"
    assert "password" not in body and "password_hash" not in body


@pytest.mark.asyncio
async def test_retailer_sign_up_refuses_an_email_already_in_use(client: AsyncClient) -> None:
    await client.post("/api/v1/auth/signup/retailer", json=RETAILER)
    again = await client.post(
        "/api/v1/auth/signup/retailer", json={**RETAILER, "organisation_name": "Other Shop"}
    )
    assert again.status_code == 409


@pytest.mark.asyncio
async def test_password_needs_a_letter_and_a_number(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/auth/signup/retailer", json={**RETAILER, "password": "onlyletterslong"}
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_short_password_is_refused(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/auth/signup/retailer", json={**RETAILER, "password": "a1"}
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_user_joins_a_retailer_with_its_code_as_an_inspector(client: AsyncClient) -> None:
    retailer = (await client.post("/api/v1/auth/signup/retailer", json=RETAILER)).json()
    response = await client.post(
        "/api/v1/auth/signup/user",
        json={
            "invite_code": retailer["org_id"],
            "display_name": "Kwame",
            "email": "kwame@harbour.example",
            "password": "another pass 7",
        },
    )
    assert response.status_code == 201
    body = response.json()
    assert body["role"] == "inspector"
    assert body["org_id"] == retailer["org_id"]
    assert body["organisation_name"] == "Harbour Electronics"


@pytest.mark.asyncio
async def test_unknown_retailer_code_is_refused(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/auth/signup/user",
        json={
            "invite_code": str(uuid.uuid4()),
            "display_name": "Kwame",
            "email": "kwame@example.com",
            "password": "another pass 7",
        },
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_sign_in_returns_the_account_and_its_organisation(client: AsyncClient) -> None:
    await client.post("/api/v1/auth/signup/retailer", json=RETAILER)
    response = await client.post(
        "/api/v1/auth/signin",
        json={"email": "ADA@harbour.example ", "password": RETAILER["password"]},
    )
    assert response.status_code == 200
    assert response.json()["organisation_name"] == "Harbour Electronics"


@pytest.mark.asyncio
async def test_wrong_password_and_unknown_email_give_the_same_answer(
    client: AsyncClient,
) -> None:
    await client.post("/api/v1/auth/signup/retailer", json=RETAILER)
    wrong = await client.post(
        "/api/v1/auth/signin", json={"email": RETAILER["email"], "password": "wrong pass 1"}
    )
    unknown = await client.post(
        "/api/v1/auth/signin", json={"email": "nobody@example.com", "password": "wrong pass 1"}
    )
    assert wrong.status_code == unknown.status_code == 401
    assert wrong.json() == unknown.json()
