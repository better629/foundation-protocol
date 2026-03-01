"""Profile exports."""

from .core_minimal import CoreMinimalProfile
from .core_streaming import CoreStreamingProfile
from .governed import GovernedProfile

PROFILE_REGISTRY = {
    CoreMinimalProfile().profile_id: CoreMinimalProfile(),
    CoreStreamingProfile().profile_id: CoreStreamingProfile(),
    GovernedProfile().profile_id: GovernedProfile(),
}

__all__ = [
    "CoreMinimalProfile",
    "CoreStreamingProfile",
    "GovernedProfile",
    "PROFILE_REGISTRY",
]
