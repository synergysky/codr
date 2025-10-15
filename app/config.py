from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Configuration via environment variables.
    
    For multiple repos, use comma-separated values:
    GITHUB_REPOS=org1/repo1,org2/repo2
    ZENHUB_WORKSPACE_IDS=workspace1,workspace2
    """
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # Mode: relay (repository_dispatch) or direct (create branch/PR directly)
    MODE: str = Field(default="relay", description="relay or direct")
    
    # GitHub configuration
    GITHUB_TOKEN: str = Field(..., description="GitHub PAT or App installation token")
    GITHUB_REPOS: str = Field(
        default="",
        description="Comma-separated list of repos (owner/repo format), e.g. 'myorg/repo1,myorg/repo2'"
    )
    
    # Zenhub configuration
    ZENHUB_TOKEN: str | None = Field(default=None, description="Zenhub API token (for direct mode)")
    ZENHUB_WORKSPACE_IDS: str = Field(
        default="",
        description="Comma-separated Zenhub workspace IDs to monitor"
    )
    ZENHUB_PIPELINE_NAME: str = Field(
        default="In Progress",
        description="Exact pipeline name in Zenhub that triggers automation"
    )
    
    # Webhook security
    WEBHOOK_TOKEN: str = Field(..., description="Shared secret for webhook authentication")
    
    # Dispatch event type
    DISPATCH_EVENT: str = Field(
        default="zenhub_in_progress",
        description="GitHub repository_dispatch event type"
    )
    
    # Server
    PORT: int = Field(default=8000, description="HTTP server port")
    
    # Branch strategy
    BASE_BRANCH_DEFAULT: str = Field(default="develop", description="Default base branch")
    BASE_BRANCH_HOTFIX: str = Field(default="hotfix_branch", description="Base branch for hotfixes")
    HOTFIX_LABEL: str = Field(default="hotfix", description="Label that marks an issue as hotfix")
    
    @field_validator("GITHUB_REPOS", mode="before")
    @classmethod
    def validate_repos(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("GITHUB_REPOS must contain at least one repo in owner/repo format")
        repos = [r.strip() for r in v.split(",")]
        for repo in repos:
            if "/" not in repo:
                raise ValueError(f"Invalid repo format: {repo}. Expected owner/repo")
        return v
    
    def get_repos(self) -> list[str]:
        """Returns list of repos in owner/repo format."""
        return [r.strip() for r in self.GITHUB_REPOS.split(",") if r.strip()]
    
    def get_workspace_ids(self) -> list[str]:
        """Returns list of Zenhub workspace IDs."""
        if not self.ZENHUB_WORKSPACE_IDS:
            return []
        return [w.strip() for w in self.ZENHUB_WORKSPACE_IDS.split(",") if w.strip()]


def get_settings() -> Settings:
    """Factory function to get settings instance.
    
    This allows for lazy initialization and easier testing.
    """
    return Settings()


# Global settings instance for convenience
# Note: This will fail if required env vars are not set
try:
    settings = Settings()
except Exception:
    # In test environment, settings will be mocked
    settings = None  # type: ignore[assignment]
