"""21 张表的 ORM 模型（导入即注册到 Base.metadata）。"""

from vigil_workbench.db.models.admin_credential import AdminCredential
from vigil_workbench.db.models.ai_call_record import AiCallRecord
from vigil_workbench.db.models.analysis_session import AnalysisSession
from vigil_workbench.db.models.approval_request import ApprovalRequest
from vigil_workbench.db.models.artifact import Artifact
from vigil_workbench.db.models.knowledge_base import KnowledgeBase
from vigil_workbench.db.models.knowledge_entry import KnowledgeEntry
from vigil_workbench.db.models.login_attempt import LoginAttempt
from vigil_workbench.db.models.login_session import LoginSession
from vigil_workbench.db.models.model_binding import ModelBinding
from vigil_workbench.db.models.project_context import ProjectContext
from vigil_workbench.db.models.provider_config import ProviderConfig
from vigil_workbench.db.models.qa_skill import QaSkill
from vigil_workbench.db.models.qa_skill_version import QaSkillVersion
from vigil_workbench.db.models.repo_binding import RepoBinding
from vigil_workbench.db.models.repo_file_read_record import RepoFileReadRecord
from vigil_workbench.db.models.repo_metadata_snapshot import RepoMetadataSnapshot
from vigil_workbench.db.models.repo_sync_record import RepoSyncRecord
from vigil_workbench.db.models.session_event import SessionEvent
from vigil_workbench.db.models.test_case import TestCase
from vigil_workbench.db.models.test_case_design_plan import TestCaseDesignPlan

__all__ = [
    "AdminCredential",
    "AiCallRecord",
    "AnalysisSession",
    "ApprovalRequest",
    "Artifact",
    "KnowledgeBase",
    "KnowledgeEntry",
    "LoginAttempt",
    "LoginSession",
    "ModelBinding",
    "ProjectContext",
    "ProviderConfig",
    "QaSkill",
    "QaSkillVersion",
    "RepoBinding",
    "RepoFileReadRecord",
    "RepoMetadataSnapshot",
    "RepoSyncRecord",
    "SessionEvent",
    "TestCase",
    "TestCaseDesignPlan",
]
