"""Single source of truth for API documentation structure.

Sections are grouped by the backing model tables (``app_label.Model``) and
ordered by the numbered API specification serial. Tag names are zero-padded
so Swagger UI and ReDoc render sections in spec order. Views reference
``SECTION_TAGS`` (never hand-written strings) so the docs stay modular and
aligned with the models in ``apps/``.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class ApiSection:
    number: int
    name: str
    description: str
    models: tuple = ()

    @property
    def tag(self) -> str:
        return f"{self.number:02d}. {self.name}"


SECTIONS = {
    "users-auth": ApiSection(
        1,
        "Users & Auth",
        "Registration, email verification, OTP resend, login, token refresh, "
        "logout, current user and password change.",
        ("users.User", "users.OTP"),
    ),
    "kaazbir-profiles": ApiSection(
        2,
        "KaazBir Profiles",
        "KaazBir (worker) profiles plus kasbir discovery and search.",
        ("users.KaazbirProfile",),
    ),
    "kyc-verification": ApiSection(
        3,
        "KYC Verification",
        "Know-Your-Customer verification submission for kaazbirs.",
        ("users.KYCVerification", "users.KYCSelfie"),
    ),
    "services-subservices": ApiSection(
        4,
        "Services & Subservices",
        "Browse the service category tree.",
        ("catalog.Service", "catalog.Subservice"),
    ),
    "custom-fields": ApiSection(
        5,
        "Service Custom Fields",
        "Dynamic custom fields attached to subservices.",
        ("catalog.CustomField", "catalog.SubserviceCustomField"),
    ),
    "kaazbir-services": ApiSection(
        6,
        "KaazBir Services",
        "Manage the services a kaazbir offers.",
        ("catalog.KasbirService",),
    ),
    "campaigns": ApiSection(
        7,
        "Campaigns & Offers",
        "Current and featured campaigns and offers.",
        ("catalog.Campaign",),
    ),
    "missions-bids": ApiSection(
        8,
        "Missions & Bids",
        "Create, browse, bid for and confirm missions, direct offers and "
        "mission activity.",
        ("missions.Mission", "missions.MissionPicture", "missions.MissionApplication"),
    ),
    "reviews": ApiSection(
        9,
        "Reviews",
        "Kaazbir review ratings and lists.",
        ("missions.Review",),
    ),
    "earnings-stats": ApiSection(
        10,
        "Earnings & Stats",
        "Kaazbir earnings and acceptance-ratio statistics.",
        ("missions.Earning",),
    ),
    "hirer-profiles": ApiSection(
        11,
        "Hirer Profiles & Media",
        "Hirer (employer) profile, media, profile picture and notification "
        "settings.",
        ("hirer.HirerProfile", "hirer.HirerMedia"),
    ),
    "system": ApiSection(
        12,
        "System",
        "Infrastructure endpoints such as health checks.",
        (),
    ),
}

SECTION_TAGS = {key: section.tag for key, section in SECTIONS.items()}


def build_tag_list():
    """Top-level OpenAPI ``tags`` array, in API specification (serial) order."""
    tags = []
    for section in SECTIONS.values():
        entry = {"name": section.tag, "description": section.description}
        if section.models:
            entry["description"] += f" Backed by tables: {', '.join(section.models)}."
        tags.append(entry)
    return tags
