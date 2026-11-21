"""16 张表的 ORM 模型（导入即注册到 Base.metadata）。"""

from workbench.db.models.admin_credential import AdminCredential
from workbench.db.models.ai_call_record import AiCallRecord
from workbench.db.models.analysis_session import AnalysisSession
from workbench.db.models.artifact import Artifact
from workbench.db.models.knowledge_base import KnowledgeBase
from workbench.db.models.knowledge_entry import KnowledgeEntry
from workbench.db.models.login_attempt import LoginAttempt
from workbench.db.models.login_session import LoginSession
from workbench.db.models.model_binding import ModelBinding
from workbench.db.models.project_context import ProjectContext
from workbench.db.models.provider_config import ProviderConfig
from workbench.db.models.repo_binding import RepoBinding
from workbench.db.models.repo_file_read_record import RepoFileReadRecord
from workbench.db.models.repo_metadata_snapshot import RepoMetadataSnapshot
from workbench.db.models.repo_sync_record import RepoSyncRecord
from workbench.db.models.session_event import SessionEvent

__all__ = [
    "AdminCredential",
    "AiCallRecord",
    "AnalysisSession",
    "Artifact",
    "KnowledgeBase",
    "KnowledgeEntry",
    "LoginAttempt",
    "LoginSession",
    "ModelBinding",
    "ProjectContext",
    "ProviderConfig",
    "RepoBinding",
    "RepoFileReadRecord",
    "RepoMetadataSnapshot",
    "RepoSyncRecord",
    "SessionEvent",
]
