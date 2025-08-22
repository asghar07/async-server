from pydantic import BaseModel


class OnboardingGithubRequest(BaseModel):
    user_id: str
    code: str
    installation_id: int
    is_dev: bool = False


class OnboardingGithubResponse(BaseModel):
    pass
