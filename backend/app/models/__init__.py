# Models package — all model imports trigger SQLAlchemy table registration.
# Import order matters: parents before children (FK constraints).
from app.models.organization import Organization          # noqa: F401
from app.models.project import Project                    # noqa: F401
from app.models.application import Application            # noqa: F401
from app.models.asset import Asset                        # noqa: F401
from app.models.scan import Scan                          # noqa: F401
from app.models.finding import CryptoFinding              # noqa: F401
from app.models.risk_assessment import RiskAssessment     # noqa: F401
from app.models.roadmap import MigrationRecommendation, RoadmapItem  # noqa: F401
from app.models.report import Report                      # noqa: F401
