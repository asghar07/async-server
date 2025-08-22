"""
Module initializing clients that are used globally in the app.
"""

from typing import Optional

from src.async_module import AsyncClient
from src.email import EmailClient
from src.firebase import FirestoreClient, StorageClient
from src.github import GithubClient
from src.google import GcrClient, SecretClient
from src.payment import StripeClient

async_client: Optional[AsyncClient] = None
email_client: Optional[EmailClient] = None
firestore_client: Optional[FirestoreClient] = None
gcr_client: Optional[GcrClient] = None
github_client: Optional[GithubClient] = None
secret_client: Optional[SecretClient] = None
storage_client: Optional[StorageClient] = None
stripe_client: Optional[StripeClient] = None


async def initialize_clients_async():
    global \
        async_client, \
        email_client, \
        firestore_client, \
        gcr_client, \
        github_client, \
        secret_client, \
        storage_client, \
        stripe_client

    async_client = AsyncClient()
    email_client = EmailClient()
    firestore_client = FirestoreClient()
    gcr_client = GcrClient()
    secret_client = SecretClient()
    storage_client = StorageClient()
    github_client = GithubClient()
    stripe_client = StripeClient()


async def cleanup_clients_async():
    if github_client:
        await github_client.close_async()


def get_async_client() -> AsyncClient:
    if async_client is None:
        raise RuntimeError("Clients not initialized. Call init_clients() first.")
    return async_client


def get_email_client() -> EmailClient:
    if email_client is None:
        raise RuntimeError("Clients not initialized. Call init_clients() first.")
    return email_client


def get_firestore_client() -> FirestoreClient:
    if firestore_client is None:
        raise RuntimeError("Clients not initialized. Call init_clients() first.")
    return firestore_client


def get_gcr_client() -> GcrClient:
    if gcr_client is None:
        raise RuntimeError("Clients not initialized. Call init_clients() first.")
    return gcr_client


def get_github_client() -> GithubClient:
    if github_client is None:
        raise RuntimeError("Clients not initialized. Call init_clients() first.")
    return github_client


def get_secret_client() -> SecretClient:
    if secret_client is None:
        raise RuntimeError("Clients not initialized. Call init_clients() first.")
    return secret_client


def get_storage_client() -> StorageClient:
    if storage_client is None:
        raise RuntimeError("Clients not initialized. Call init_clients() first.")
    return storage_client


def get_stripe_client() -> StripeClient:
    if stripe_client is None:
        raise RuntimeError("Clients not initialized. Call init_clients() first.")
    return stripe_client
