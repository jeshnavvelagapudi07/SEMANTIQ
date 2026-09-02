"""
Synthetic Enterprise Knowledge Graph & Document Dataset for SEMANTIQ
Realistic Aerospace & Precision Manufacturing Engineering Domain
"""
from app.models.schemas import (
    Entity,
    EntityType,
    ClassificationLevel,
    Relationship,
    RelationType,
    Document,
    EvidenceChunk
)

# ---------------------------------------------------------------------------
# 1. ENTITIES (Projects, Systems, Incidents, Teams, Employees, Policies, Customers, Documents)
# ---------------------------------------------------------------------------

SEED_ENTITIES: list[Entity] = [
    # Projects
    Entity(
        id="PRJ-ALPHA",
        name="Project Alpha",
        type=EntityType.PROJECT,
        description="Autonomous precision milling line for titanium aero-structures.",
        classification=ClassificationLevel.INTERNAL,
        owner_team="TEAM-MFG-OPS",
        properties={"status": "Active", "priority": "High", "lead_engineer": "EMP-002"}
    ),
    Entity(
        id="PRJ-BETA",
        name="Project Beta",
        type=EntityType.PROJECT,
        description="High-frequency vibration & acoustic telemetry sensor array integration.",
        classification=ClassificationLevel.INTERNAL,
        owner_team="TEAM-RELIABILITY",
        properties={"status": "Testing", "priority": "Medium", "lead_engineer": "EMP-001"}
    ),
    Entity(
        id="PRJ-GAMMA",
        name="Project C",  # Also known as Project Gamma in specs
        type=EntityType.PROJECT,
        description="High-precision turbine blade milling project for next-generation turbofan engines.",
        classification=ClassificationLevel.INTERNAL,
        owner_team="TEAM-AERO-ENG",
        properties={"status": "Critical", "priority": "Urgent", "risk_level": "High", "lead_engineer": "EMP-003", "alias": "Project C"}
    ),
    Entity(
        id="PRJ-DELTA",
        name="Project Delta",
        type=EntityType.PROJECT,
        description="Single-crystal superalloy induction sintering and thermal barrier coating.",
        classification=ClassificationLevel.INTERNAL,
        owner_team="TEAM-AERO-ENG",
        properties={"status": "Active", "priority": "High", "lead_engineer": "EMP-004"}
    ),
    Entity(
        id="PRJ-EPSILON",
        name="Project Epsilon",
        type=EntityType.PROJECT,
        description="ISO-5 cleanroom robotics transfer arm deployment for optical assemblies.",
        classification=ClassificationLevel.INTERNAL,
        owner_team="TEAM-AUTOMATION",
        properties={"status": "Deployment", "priority": "Medium", "lead_engineer": "EMP-005"}
    ),
    Entity(
        id="PRJ-ZETA",
        name="Project Zeta",
        type=EntityType.PROJECT,
        description="Laser interferometer inline surface roughness and dimensional metrology rig.",
        classification=ClassificationLevel.INTERNAL,
        owner_team="TEAM-QUALITY",
        properties={"status": "Active", "priority": "Medium", "lead_engineer": "EMP-004"}
    ),
    Entity(
        id="PRJ-ETA",
        name="Project Eta",
        type=EntityType.PROJECT,
        description="Ultra-high pressure 350-bar hydraulic servo valve validation.",
        classification=ClassificationLevel.INTERNAL,
        owner_team="TEAM-RELIABILITY",
        properties={"status": "Validation", "priority": "Low", "lead_engineer": "EMP-001"}
    ),
    Entity(
        id="PRJ-THETA",
        name="Project Theta",
        type=EntityType.PROJECT,
        description="Plant-wide SCADA telemetry time-series synchronization & fault prediction.",
        classification=ClassificationLevel.INTERNAL,
        owner_team="TEAM-AUTOMATION",
        properties={"status": "Active", "priority": "High", "lead_engineer": "EMP-005"}
    ),

    # Systems
    Entity(
        id="SYS-CNC-07",
        name="CNC-07",
        type=EntityType.SYSTEM,
        description="5-Axis High-Speed DMG Mori CNC Milling Center #07 with HSK-A63 spindle.",
        classification=ClassificationLevel.INTERNAL,
        owner_team="TEAM-MFG-OPS",
        properties={"bay": "Bay-4B", "max_rpm": 24000, "criticality": "Critical"}
    ),
    Entity(
        id="SYS-CNC-04",
        name="CNC-04",
        type=EntityType.SYSTEM,
        description="3-Axis Roughing CNC Milling Center #04.",
        classification=ClassificationLevel.INTERNAL,
        owner_team="TEAM-MFG-OPS",
        properties={"bay": "Bay-2A", "max_rpm": 12000, "criticality": "Medium"}
    ),
    Entity(
        id="SYS-COOL-02",
        name="Coolant Chiller 02",
        type=EntityType.SYSTEM,
        description="Closed-loop industrial chiller providing chilled fluid to Bay-4B CNC machines.",
        classification=ClassificationLevel.INTERNAL,
        owner_team="TEAM-RELIABILITY",
        properties={"capacity_kw": 45, "nominal_temp_c": 18.0}
    ),
    Entity(
        id="SYS-PLC-88",
        name="Siemens S7-1500 PLC #88",
        type=EntityType.SYSTEM,
        description="Main machine controller & interlock safety PLC for Bay-4B.",
        classification=ClassificationLevel.INTERNAL,
        owner_team="TEAM-AUTOMATION",
        properties={"ip": "192.168.14.88", "firmware": "v3.1.2"}
    ),
    Entity(
        id="SYS-FURN-05",
        name="Induction Furnace 05",
        type=EntityType.SYSTEM,
        description="High-vacuum induction sintering furnace with inert argon purge.",
        classification=ClassificationLevel.INTERNAL,
        owner_team="TEAM-AERO-ENG",
        properties={"max_temp_c": 1650, "vacuum_mbar": 0.001}
    ),
    Entity(
        id="SYS-ARM-02",
        name="Robotic Transfer Arm 02",
        type=EntityType.SYSTEM,
        description="6-axis articulated cleanroom industrial robot arm.",
        classification=ClassificationLevel.INTERNAL,
        owner_team="TEAM-AUTOMATION",
        properties={"payload_kg": 20, "reach_mm": 1600}
    ),
    Entity(
        id="SYS-OPT-09",
        name="Laser Metrology Scanner 09",
        type=EntityType.SYSTEM,
        description="Coordinate measuring laser scanner with 0.5-micron volumetric precision.",
        classification=ClassificationLevel.INTERNAL,
        owner_team="TEAM-QUALITY",
        properties={"precision_um": 0.5, "calibrated_until": "2026-12-31"}
    ),
    Entity(
        id="SYS-HYDR-01",
        name="Hydraulic Test Rig 01",
        type=EntityType.SYSTEM,
        description="Dynamic pressure pulse test bench up to 400 bar.",
        classification=ClassificationLevel.INTERNAL,
        owner_team="TEAM-RELIABILITY",
        properties={"max_bar": 400}
    ),
    Entity(
        id="SYS-AIR-04",
        name="Cleanroom HEPA Unit 04",
        type=EntityType.SYSTEM,
        description="Laminar flow filtration module maintaining ISO Class 5 air purity.",
        classification=ClassificationLevel.INTERNAL,
        owner_team="TEAM-FACILITIES",
        properties={"class": "ISO-5"}
    ),
    Entity(
        id="SYS-SCADA-01",
        name="Core SCADA Gateway",
        type=EntityType.SYSTEM,
        description="Unified OPC-UA telemetry ingestion hub.",
        classification=ClassificationLevel.CONFIDENTIAL,
        owner_team="TEAM-AUTOMATION",
        properties={"protocol": "OPC-UA / MQTT"}
    ),
    Entity(
        id="SYS-SENS-01",
        name="Acoustic Emission Array 01",
        type=EntityType.SYSTEM,
        description="High-frequency 100kHz acoustic sensor array mounted on CNC spindles.",
        classification=ClassificationLevel.INTERNAL,
        owner_team="TEAM-RELIABILITY",
        properties={"frequency_khz": 100}
    ),
    Entity(
        id="SYS-POWER-03",
        name="Substation 3 Transformer",
        type=EntityType.SYSTEM,
        description="480V 3-phase industrial power distribution transformer.",
        classification=ClassificationLevel.INTERNAL,
        owner_team="TEAM-FACILITIES",
        properties={"kva": 750}
    ),

    # Incidents
    Entity(
        id="INC-104",
        name="Incident 104",
        type=EntityType.INCIDENT,
        description="Active High-Severity Thermal Excursion on CNC-07 Spindle Bearing (74.2°C).",
        classification=ClassificationLevel.INTERNAL,
        owner_team="TEAM-MFG-OPS",
        properties={"severity": "Severity 2 (High)", "status": "Active Investigation", "timestamp": "2026-03-01T08:14:00Z", "sensor_temp_c": 74.2}
    ),
    Entity(
        id="INC-101",
        name="Incident 101",
        type=EntityType.INCIDENT,
        description="Chiller 02 secondary loop pressure drop (resolved).",
        classification=ClassificationLevel.INTERNAL,
        owner_team="TEAM-RELIABILITY",
        properties={"severity": "Severity 3", "status": "Closed", "timestamp": "2026-01-12T14:30:00Z"}
    ),
    Entity(
        id="INC-102",
        name="Incident 102",
        type=EntityType.INCIDENT,
        description="PLC-88 Profinet communication timeout during rapid tool change.",
        classification=ClassificationLevel.INTERNAL,
        owner_team="TEAM-AUTOMATION",
        properties={"severity": "Severity 3", "status": "Closed", "timestamp": "2026-01-28T09:15:00Z"}
    ),
    Entity(
        id="INC-103",
        name="Incident 103",
        type=EntityType.INCIDENT,
        description="Cleanroom HEPA differential pressure filter threshold breach.",
        classification=ClassificationLevel.INTERNAL,
        owner_team="TEAM-FACILITIES",
        properties={"severity": "Severity 4", "status": "Closed", "timestamp": "2026-02-14T11:00:00Z"}
    ),
    Entity(
        id="INC-105",
        name="Incident 105",
        type=EntityType.INCIDENT,
        description="Hydraulic pressure spike on Test Rig 01 valve manifold.",
        classification=ClassificationLevel.INTERNAL,
        owner_team="TEAM-RELIABILITY",
        properties={"severity": "Severity 3", "status": "Under Review", "timestamp": "2026-02-27T16:45:00Z"}
    ),
    Entity(
        id="INC-106",
        name="Incident 106",
        type=EntityType.INCIDENT,
        description="Furnace 05 argon purge regulator calibration drift.",
        classification=ClassificationLevel.INTERNAL,
        owner_team="TEAM-AERO-ENG",
        properties={"severity": "Severity 3", "status": "Resolved", "timestamp": "2026-02-18T10:20:00Z"}
    ),
    Entity(
        id="INC-107",
        name="Incident 107",
        type=EntityType.INCIDENT,
        description="Laser Scanner 09 optics dust contamination alert.",
        classification=ClassificationLevel.INTERNAL,
        owner_team="TEAM-QUALITY",
        properties={"severity": "Severity 4", "status": "Closed", "timestamp": "2026-02-22T08:00:00Z"}
    ),
    Entity(
        id="INC-108",
        name="Incident 108",
        type=EntityType.INCIDENT,
        description="CNC-04 X-axis ball screw backlash warning.",
        classification=ClassificationLevel.INTERNAL,
        owner_team="TEAM-MFG-OPS",
        properties={"severity": "Severity 3", "status": "Under Review", "timestamp": "2026-02-25T13:10:00Z"}
    ),
    Entity(
        id="INC-109",
        name="Incident 109",
        type=EntityType.INCIDENT,
        description="Substation 3 harmonic distortion warning during furnace startup.",
        classification=ClassificationLevel.INTERNAL,
        owner_team="TEAM-FACILITIES",
        properties={"severity": "Severity 4", "status": "Closed", "timestamp": "2026-01-05T07:30:00Z"}
    ),
    Entity(
        id="INC-110",
        name="Incident 110",
        type=EntityType.INCIDENT,
        description="Robotic Arm 02 joint 4 torque limit threshold tripped.",
        classification=ClassificationLevel.INTERNAL,
        owner_team="TEAM-AUTOMATION",
        properties={"severity": "Severity 3", "status": "Resolved", "timestamp": "2026-02-10T15:00:00Z"}
    ),

    # Teams
    Entity(
        id="TEAM-MFG-OPS",
        name="Manufacturing Operations",
        type=EntityType.TEAM,
        description="Shop floor CNC machining, production scheduling, and tool management.",
        classification=ClassificationLevel.PUBLIC,
        properties={"department": "Operations", "lead": "EMP-002", "members_count": 28}
    ),
    Entity(
        id="TEAM-RELIABILITY",
        name="Site Reliability Engineering",
        type=EntityType.TEAM,
        description="Equipment health monitoring, predictive maintenance, and vibration analysis.",
        classification=ClassificationLevel.PUBLIC,
        properties={"department": "Engineering", "lead": "EMP-001", "members_count": 12}
    ),
    Entity(
        id="TEAM-AERO-ENG",
        name="Aerospace Engineering",
        type=EntityType.TEAM,
        description="Turbine blade design, finite element analysis, and materials qualification.",
        classification=ClassificationLevel.PUBLIC,
        properties={"department": "R&D", "lead": "EMP-003", "members_count": 16}
    ),
    Entity(
        id="TEAM-QUALITY",
        name="Quality Assurance & Metrology",
        type=EntityType.TEAM,
        description="CMM inspection, AS9100 compliance, and surface metrology.",
        classification=ClassificationLevel.PUBLIC,
        properties={"department": "Quality", "lead": "EMP-004", "members_count": 10}
    ),
    Entity(
        id="TEAM-AUTOMATION",
        name="Automation & Controls",
        type=EntityType.TEAM,
        description="PLC programming, robotic cell integration, and SCADA telemetry.",
        classification=ClassificationLevel.PUBLIC,
        properties={"department": "Engineering", "lead": "EMP-005", "members_count": 8}
    ),
    Entity(
        id="TEAM-SAFETY",
        name="Environmental Health & Safety",
        type=EntityType.TEAM,
        description="Workplace machinery safety, LOTO protocols, and hazard audits.",
        classification=ClassificationLevel.PUBLIC,
        properties={"department": "EHS", "lead": "EMP-006", "members_count": 6}
    ),
    Entity(
        id="TEAM-FACILITIES",
        name="Plant Facilities & Power",
        type=EntityType.TEAM,
        description="Cleanroom HVAC, industrial chillers, and high-voltage power distribution.",
        classification=ClassificationLevel.PUBLIC,
        properties={"department": "Facilities", "members_count": 14}
    ),
    Entity(
        id="TEAM-EXECUTIVE",
        name="Executive Leadership & Legal",
        type=EntityType.TEAM,
        description="Strategic contracts, executive compensation, and enterprise governance.",
        classification=ClassificationLevel.RESTRICTED,
        properties={"department": "Executive", "members_count": 5}
    ),

    # Employees
    Entity(
        id="EMP-001",
        name="Dr. Kenji Sato",
        type=EntityType.EMPLOYEE,
        description="Principal Reliability Engineer & Vibration Diagnostics Specialist.",
        classification=ClassificationLevel.PUBLIC,
        owner_team="TEAM-RELIABILITY",
        properties={"title": "Principal Reliability Engineer", "badge": "ENG-SATO-01", "certifications": ["ISO-18436-CatIV", "ASME-Fellow"]}
    ),
    Entity(
        id="EMP-002",
        name="Elena Rostova",
        type=EntityType.EMPLOYEE,
        description="Head of Manufacturing Operations and Shop Floor Supervisor.",
        classification=ClassificationLevel.PUBLIC,
        owner_team="TEAM-MFG-OPS",
        properties={"title": "Operations Director", "badge": "OPS-ROST-02"}
    ),
    Entity(
        id="EMP-003",
        name="Marcus Vance",
        type=EntityType.EMPLOYEE,
        description="Project Gamma Director and Lead Aero-Thermal Engineer.",
        classification=ClassificationLevel.PUBLIC,
        owner_team="TEAM-AERO-ENG",
        properties={"title": "Project Director", "badge": "DIR-VANC-03"}
    ),
    Entity(
        id="EMP-004",
        name="Aoi Tanaka",
        type=EntityType.EMPLOYEE,
        description="Senior Quality Assurance Manager and AS9100 Lead Auditor.",
        classification=ClassificationLevel.PUBLIC,
        owner_team="TEAM-QUALITY",
        properties={"title": "QA Manager", "badge": "QUAL-TANA-04"}
    ),
    Entity(
        id="EMP-005",
        name="Takeshi Yamamoto",
        type=EntityType.EMPLOYEE,
        description="Automation & SCADA Principal Architect.",
        classification=ClassificationLevel.PUBLIC,
        owner_team="TEAM-AUTOMATION",
        properties={"title": "Principal Automation Architect", "badge": "AUTO-YAMA-05"}
    ),
    Entity(
        id="EMP-006",
        name="Sarah Jenkins",
        type=EntityType.EMPLOYEE,
        description="Director of Workplace Safety and Machine Emergency Protocols.",
        classification=ClassificationLevel.PUBLIC,
        owner_team="TEAM-SAFETY",
        properties={"title": "Safety Director", "badge": "SAFE-JENK-06"}
    ),

    # Policies
    Entity(
        id="POL-SAFE-01",
        name="Workplace Critical Machinery Safety Standard",
        type=EntityType.POLICY,
        description="Mandatory emergency shutdown, thermal trip interlocks, and perimeter guard rules.",
        classification=ClassificationLevel.PUBLIC,
        owner_team="TEAM-SAFETY",
        properties={"policy_code": "POL-SAFE-01", "enforcement": "Strict"}
    ),
    Entity(
        id="POL-ESCAL-02",
        name="Incident Escalation Hierarchy Policy",
        type=EntityType.POLICY,
        description="SLA thresholds and required multi-team alerts for Severity-1 and Severity-2 plant incidents.",
        classification=ClassificationLevel.PUBLIC,
        owner_team="TEAM-MFG-OPS",
        properties={"policy_code": "POL-ESCAL-02", "sla_sev1_mins": 15}
    ),
    Entity(
        id="POL-DATA-03",
        name="Organizational Data Classification & Access Control Policy",
        type=EntityType.POLICY,
        description="Zero-trust access tiers for Public, Internal, Confidential, and Restricted materials.",
        classification=ClassificationLevel.PUBLIC,
        owner_team="TEAM-EXECUTIVE",
        properties={"policy_code": "POL-DATA-03"}
    ),
    Entity(
        id="POL-MAINT-04",
        name="Preventative Maintenance Schedule Compliance Policy",
        type=EntityType.POLICY,
        description="Operating hour limits and vibration-triggered overhaul criteria for high-speed spindles.",
        classification=ClassificationLevel.PUBLIC,
        owner_team="TEAM-RELIABILITY",
        properties={"policy_code": "POL-MAINT-04"}
    ),
    Entity(
        id="POL-QUAL-05",
        name="Aerospace AS9100 Quality Traceability Protocol",
        type=EntityType.POLICY,
        description="Material batch traceability and tooling calibration certification requirements.",
        classification=ClassificationLevel.INTERNAL,
        owner_team="TEAM-QUALITY",
        properties={"policy_code": "POL-QUAL-05"}
    ),

    # Customers
    Entity(
        id="CUST-AERO-GLOBAL",
        name="Global Aerospace Dynamics",
        type=EntityType.CUSTOMER,
        description="Prime tier-1 commercial turbofan engine manufacturer and primary sponsor of Project Gamma.",
        classification=ClassificationLevel.CONFIDENTIAL,
        properties={"tier": "Strategic Prime", "region": "North America / Global"}
    ),
    Entity(
        id="CUST-TURBO-TECH",
        name="TurboTech Propulsion Ltd",
        type=EntityType.CUSTOMER,
        description="Defense and space propulsion system integrator.",
        classification=ClassificationLevel.CONFIDENTIAL,
        properties={"tier": "Key Account", "region": "Europe"}
    ),
    Entity(
        id="CUST-ORBITAL-SYS",
        name="Orbital Dynamics International",
        type=EntityType.CUSTOMER,
        description="Satellite launch vehicle propulsion contractor.",
        classification=ClassificationLevel.CONFIDENTIAL,
        properties={"tier": "Tier-2 Subcontractor", "region": "Asia-Pacific"}
    ),
    Entity(
        id="CUST-NIPPON-AERO",
        name="Nippon Aero Precision Corp",
        type=EntityType.CUSTOMER,
        description="Precision aerospace components integrator for regional jets.",
        classification=ClassificationLevel.CONFIDENTIAL,
        properties={"tier": "Strategic Partner", "region": "Japan"}
    ),
    Entity(
        id="CUST-DEFENSE-CORP",
        name="Apex Defense Systems",
        type=EntityType.CUSTOMER,
        description="Military grade avionics and structural airframe client.",
        classification=ClassificationLevel.CONFIDENTIAL,
        properties={"tier": "Defense Prime", "clearance_req": "Top Level"}
    ),

    # Document & SOP Entities (Searchable in Knowledge Graph & Entity Explorer)
    Entity(
        id="SOP-017",
        name="SOP-017: Spindle Thermal Emergency Protocol",
        type=EntityType.DOCUMENT,
        description="Standard Operating Procedure for High-Speed Spindle Bearing Overheat and Emergency LOTO Tag-Out.",
        classification=ClassificationLevel.INTERNAL,
        owner_team="TEAM-SAFETY",
        properties={"doc_code": "SOP-017", "version": "4.2", "owner": "TEAM-SAFETY", "status": "Active"}
    ),
    Entity(
        id="DOC-023",
        name="DOC-023: Spindle Overhaul Maintenance Log",
        type=EntityType.DOCUMENT,
        description="Ceramic bearing telemetry, runout logs, and preventative maintenance records for CNC-07.",
        classification=ClassificationLevel.INTERNAL,
        owner_team="TEAM-RELIABILITY",
        properties={"doc_code": "DOC-023", "version": "3.1"}
    ),
    Entity(
        id="DOC-031",
        name="DOC-031: Project Gamma Tooling Specification",
        type=EntityType.DOCUMENT,
        description="High-precision turbine blade machining dependencies and CNC-07 process qualification.",
        classification=ClassificationLevel.INTERNAL,
        owner_team="TEAM-AERO-ENG",
        properties={"doc_code": "DOC-031", "version": "2.0"}
    ),
    Entity(
        id="DOC-041",
        name="DOC-041: Incident Escalation Protocol & SLA",
        type=EntityType.DOCUMENT,
        description="Multi-team notification matrix and response timelines for Severity 1/2 manufacturing outages.",
        classification=ClassificationLevel.INTERNAL,
        owner_team="TEAM-MFG-OPS",
        properties={"doc_code": "DOC-041", "version": "1.5"}
    ),
    Entity(
        id="DOC-055",
        name="DOC-055: Production Thermal Safety Manual",
        type=EntityType.DOCUMENT,
        description="Mandatory thermal trip interlocks and EHS hazard containment standards.",
        classification=ClassificationLevel.INTERNAL,
        owner_team="TEAM-SAFETY",
        properties={"doc_code": "DOC-055", "version": "5.0"}
    ),
    Entity(
        id="DOC-062",
        name="DOC-062: Turbine Blade CMM Quality Protocol",
        type=EntityType.DOCUMENT,
        description="Sub-5-micron aerodynamic profile tolerance criteria and laser scanning procedure on SYS-OPT-09.",
        classification=ClassificationLevel.INTERNAL,
        owner_team="TEAM-QUALITY",
        properties={"doc_code": "DOC-062", "version": "2.4"}
    ),
    Entity(
        id="CONTRACT-22",
        name="CONTRACT-22: Prime Master Agreement (Customer X)",
        type=EntityType.DOCUMENT,
        description="Commercial pricing matrix, delivery schedules, and liquidated damage penalty clauses for Customer X.",
        classification=ClassificationLevel.RESTRICTED,
        owner_team="TEAM-EXECUTIVE",
        properties={"doc_code": "CONTRACT-22", "confidentiality": "RESTRICTED"}
    ),
    Entity(
        id="PAYROLL-2026",
        name="PAYROLL-2026: Executive Compensation Plan",
        type=EntityType.DOCUMENT,
        description="Executive base salaries, retention packages, and performance incentive bonuses.",
        classification=ClassificationLevel.RESTRICTED,
        owner_team="TEAM-EXECUTIVE",
        properties={"doc_code": "PAYROLL-2026", "confidentiality": "RESTRICTED"}
    )
]


# ---------------------------------------------------------------------------
# 2. RELATIONSHIPS (Connecting the Graph)
# ---------------------------------------------------------------------------

SEED_RELATIONSHIPS: list[Relationship] = [
    # Project Dependencies (Core Graph Facts)
    Relationship(id="REL-001", source_id="PRJ-GAMMA", target_id="SYS-CNC-07", relation_type=RelationType.DEPENDS_ON, description="Project C depends solely on CNC-07 for 5-axis turbine blade blisk machining.", weight=1.0),
    Relationship(id="REL-002", source_id="PRJ-ALPHA", target_id="SYS-CNC-07", relation_type=RelationType.DEPENDS_ON, description="Project Alpha uses CNC-07 for titanium aero-structure milling.", weight=0.9),
    Relationship(id="REL-003", source_id="PRJ-DELTA", target_id="SYS-FURN-05", relation_type=RelationType.DEPENDS_ON, description="Project Delta relies on Induction Furnace 05 for superalloy sintering.", weight=1.0),
    Relationship(id="REL-004", source_id="PRJ-EPSILON", target_id="SYS-ARM-02", relation_type=RelationType.DEPENDS_ON, description="Project Epsilon requires Robotic Arm 02 for optical cell handling.", weight=0.9),
    Relationship(id="REL-005", source_id="PRJ-EPSILON", target_id="SYS-AIR-04", relation_type=RelationType.DEPENDS_ON, description="Project Epsilon operates within ISO-5 cleanroom HEPA airflow.", weight=0.8),
    Relationship(id="REL-006", source_id="PRJ-ZETA", target_id="SYS-OPT-09", relation_type=RelationType.DEPENDS_ON, description="Project Zeta relies on Laser Scanner 09 for sub-micron surface metrology.", weight=1.0),
    Relationship(id="REL-007", source_id="PRJ-ETA", target_id="SYS-HYDR-01", relation_type=RelationType.DEPENDS_ON, description="Project Eta uses Hydraulic Test Rig 01 for 350-bar valve cycling.", weight=0.9),
    Relationship(id="REL-008", source_id="PRJ-THETA", target_id="SYS-SCADA-01", relation_type=RelationType.DEPENDS_ON, description="Project Theta aggregates telemetry through Core SCADA Gateway.", weight=1.0),
    Relationship(id="REL-009", source_id="PRJ-BETA", target_id="SYS-SENS-01", relation_type=RelationType.DEPENDS_ON, description="Project Beta processes telemetry from Acoustic Sensor Array 01.", weight=0.9),

    # System Dependencies & Facilities
    Relationship(id="REL-010", source_id="SYS-CNC-07", target_id="SYS-COOL-02", relation_type=RelationType.DEPENDS_ON, description="CNC-07 spindle cooling jacket is supplied by Chiller 02.", weight=1.0),
    Relationship(id="REL-011", source_id="SYS-CNC-07", target_id="SYS-PLC-88", relation_type=RelationType.DEPENDS_ON, description="CNC-07 motion and interlocks are controlled by Siemens PLC #88.", weight=1.0),
    Relationship(id="REL-012", source_id="SYS-CNC-04", target_id="SYS-COOL-02", relation_type=RelationType.DEPENDS_ON, description="CNC-04 shares cooling loop with Chiller 02.", weight=0.7),
    Relationship(id="REL-013", source_id="SYS-SENS-01", target_id="SYS-CNC-07", relation_type=RelationType.USES, description="Acoustic sensor array is physically mounted on CNC-07 spindle housing.", weight=0.8),
    Relationship(id="REL-014", source_id="SYS-PLC-88", target_id="SYS-SCADA-01", relation_type=RelationType.USES, description="PLC #88 transmits telemetry packets to Core SCADA hub.", weight=0.8),
    Relationship(id="REL-015", source_id="SYS-FURN-05", target_id="SYS-POWER-03", relation_type=RelationType.DEPENDS_ON, description="Induction Furnace 05 requires 480V high current feed from Substation 3.", weight=0.9),

    # Incident Impacts & Connections
    Relationship(id="REL-016", source_id="SYS-CNC-07", target_id="INC-104", relation_type=RelationType.AFFECTED_BY, description="CNC-07 is the focal machine undergoing thermal bearing excursion under Incident 104.", weight=1.0),
    Relationship(id="REL-017", source_id="SYS-COOL-02", target_id="INC-101", relation_type=RelationType.AFFECTED_BY, description="Chiller 02 experienced secondary loop pressure drop under Incident 101.", weight=0.7),
    Relationship(id="REL-018", source_id="SYS-PLC-88", target_id="INC-102", relation_type=RelationType.AFFECTED_BY, description="PLC #88 experienced bus timeout under Incident 102.", weight=0.7),
    Relationship(id="REL-019", source_id="SYS-AIR-04", target_id="INC-103", relation_type=RelationType.AFFECTED_BY, description="Cleanroom HEPA unit experienced pressure drop under Incident 103.", weight=0.6),
    Relationship(id="REL-020", source_id="SYS-HYDR-01", target_id="INC-105", relation_type=RelationType.AFFECTED_BY, description="Hydraulic test rig had pressure spike under Incident 105.", weight=0.7),

    # Incident to Procedures & Policies
    Relationship(id="REL-021", source_id="INC-104", target_id="SOP-017", relation_type=RelationType.RELATED_TO, description="Incident 104 triggers emergency spindle response protocol SOP-017.", weight=1.0),
    Relationship(id="REL-022", source_id="INC-104", target_id="POL-ESCAL-02", relation_type=RelationType.GOVERNED_BY, description="Incident 104 requires 30-minute escalation under POL-ESCAL-02.", weight=0.9),
    Relationship(id="REL-023", source_id="INC-104", target_id="TEAM-MFG-OPS", relation_type=RelationType.ESCALATED_TO, description="Incident 104 alerts Manufacturing Operations for machine isolation.", weight=1.0),
    Relationship(id="REL-024", source_id="INC-104", target_id="TEAM-RELIABILITY", relation_type=RelationType.ESCALATED_TO, description="Incident 104 alerts Reliability Engineering for spindle diagnostics.", weight=1.0),
    Relationship(id="REL-025", source_id="INC-104", target_id="TEAM-SAFETY", relation_type=RelationType.ESCALATED_TO, description="Incident 104 notifies Safety for machine lockout verification.", weight=0.8),

    # SOP & Document Connections
    Relationship(id="REL-026", source_id="SOP-017", target_id="POL-SAFE-01", relation_type=RelationType.GOVERNED_BY, description="SOP-017 operates under Workplace Critical Machinery Safety Standard POL-SAFE-01.", weight=1.0),
    Relationship(id="REL-027", source_id="SOP-017", target_id="TEAM-SAFETY", relation_type=RelationType.OWNED_BY, description="SOP-017 is authored and owned by the Safety Team.", weight=1.0),
    Relationship(id="REL-028", source_id="SOP-017", target_id="DOC-055", relation_type=RelationType.RELATED_TO, description="SOP-017 references Production Thermal Safety Manual DOC-055.", weight=0.9),
    Relationship(id="REL-029", source_id="DOC-031", target_id="PRJ-GAMMA", relation_type=RelationType.DOCUMENTED_BY, description="DOC-031 defines Project Gamma technical dependencies.", weight=1.0),
    Relationship(id="REL-030", source_id="DOC-023", target_id="SYS-CNC-07", relation_type=RelationType.DOCUMENTED_BY, description="DOC-023 records CNC-07 spindle overhaul history.", weight=0.9),
    Relationship(id="REL-031", source_id="DOC-062", target_id="PRJ-GAMMA", relation_type=RelationType.RELATED_TO, description="DOC-062 mandates 100% CMM inspection for turbine blades.", weight=0.9),
    Relationship(id="REL-032", source_id="DOC-062", target_id="SYS-OPT-09", relation_type=RelationType.USES, description="Quality protocol DOC-062 requires Laser Scanner 09.", weight=0.9),

    # Team & Personnel Ownership
    Relationship(id="REL-033", source_id="EMP-001", target_id="TEAM-RELIABILITY", relation_type=RelationType.MEMBER_OF, description="Dr. Kenji Sato leads Site Reliability Engineering.", weight=1.0),
    Relationship(id="REL-034", source_id="EMP-002", target_id="TEAM-MFG-OPS", relation_type=RelationType.MEMBER_OF, description="Elena Rostova leads Manufacturing Operations.", weight=1.0),
    Relationship(id="REL-035", source_id="EMP-003", target_id="TEAM-AERO-ENG", relation_type=RelationType.MEMBER_OF, description="Marcus Vance directs Aerospace Engineering.", weight=1.0),
    Relationship(id="REL-036", source_id="EMP-004", target_id="TEAM-QUALITY", relation_type=RelationType.MEMBER_OF, description="Aoi Tanaka leads Quality Assurance.", weight=1.0),
    Relationship(id="REL-037", source_id="EMP-005", target_id="TEAM-AUTOMATION", relation_type=RelationType.MEMBER_OF, description="Takeshi Yamamoto is Principal Automation Architect.", weight=1.0),
    Relationship(id="REL-038", source_id="EMP-006", target_id="TEAM-SAFETY", relation_type=RelationType.MEMBER_OF, description="Sarah Jenkins is Director of Safety.", weight=1.0),
    Relationship(id="REL-039", source_id="TEAM-RELIABILITY", target_id="SYS-CNC-07", relation_type=RelationType.MAINTAINED_BY, description="Reliability Engineering oversees CNC-07 health and vibration.", weight=0.9),

    # Customer & Commercial Contracts
    Relationship(id="REL-040", source_id="CUST-AERO-GLOBAL", target_id="PRJ-GAMMA", relation_type=RelationType.USES, description="Global Aerospace Dynamics is the customer sponsor for Project Gamma blisks.", weight=1.0),
    Relationship(id="REL-041", source_id="CUST-AERO-GLOBAL", target_id="CONTRACT-22", relation_type=RelationType.DOCUMENTED_BY, description="Governed by Master Supply Agreement CONTRACT-22.", weight=1.0),
    Relationship(id="REL-042", source_id="CONTRACT-22", target_id="TEAM-EXECUTIVE", relation_type=RelationType.OWNED_BY, description="CONTRACT-22 is managed by Executive Leadership.", weight=1.0),
    Relationship(id="REL-043", source_id="PAYROLL-2026", target_id="TEAM-EXECUTIVE", relation_type=RelationType.OWNED_BY, description="Executive compensation ledger is strictly restricted.", weight=1.0),
]


# ---------------------------------------------------------------------------
# 3. TECHNICAL DOCUMENTS
# ---------------------------------------------------------------------------

SEED_DOCUMENTS: list[Document] = [
    Document(
        id="SOP-017",
        title="CNC High-Speed Spindle Temperature Incident Response & Shutdown Procedure",
        doc_type="SOP",
        classification=ClassificationLevel.INTERNAL,
        owner_team="TEAM-SAFETY",
        version="4.2",
        created_at="2025-11-10",
        entity_ids=["SYS-CNC-07", "INC-104", "TEAM-MFG-OPS", "TEAM-RELIABILITY", "TEAM-SAFETY", "POL-SAFE-01"],
        content="""STANDARD OPERATING PROCEDURE: SOP-017 (Rev 4.2)
TITLE: High-Speed Spindle Bearing Thermal Excursion & Emergency Response Protocol
OWNER: Environmental Health & Safety (TEAM-SAFETY) / Site Reliability (TEAM-RELIABILITY)

1. PURPOSE & SCOPE:
This procedure defines mandatory emergency protocols when 5-axis DMG Mori CNC milling machines (e.g. SYS-CNC-07) experience spindle bearing temperature anomalies exceeding baseline operating parameters.

2. TRIGGER THRESHOLDS:
- Warning Level 1: Bearing temp 60.0°C - 67.9°C (Alert operator, log chiller delta-T).
- Critical Level 2 (Incident 104): Bearing temp >= 68.0°C (Immediate emergency controlled spindle halt).

3. MANDATORY OPERATOR ACTIONS:
- Step 1: Engage immediate Feed Hold on CNC controller. Retract cutting tool on Z-axis (+50mm clearance).
- Step 2: Decelerate spindle from operating RPM to 500 RPM ramp-down for 60 seconds to prevent ceramic bearing seizure, then command Spindle Stop.
- Step 3: Tag out machine electrical disconnect per LOTO (Lockout/Tagout) Standard POL-SAFE-01.
- Step 4: Verify secondary coolant flow on Chiller 02 (SYS-COOL-02).
- Step 5: Notify Lead Reliability Engineer Dr. Kenji Sato (EMP-001) and Operations Lead Elena Rostova (EMP-002).

4. POST-INCIDENT RESTART REQUIREMENTS:
- Spindle runout must be verified with dial indicator (allowable runout < 2.0 microns).
- Acoustic vibration spectrum analysis must be completed on SYS-SENS-01 prior to authorizing spindle restart.
- All turbine blades machined during the thermal excursion must be quarantined for 100% laser CMM inspection per DOC-062."""
    ),

    Document(
        id="DOC-023",
        title="CNC-07 Spindle Maintenance History & Ceramic Bearing Overhaul Log",
        doc_type="Maintenance Log",
        classification=ClassificationLevel.INTERNAL,
        owner_team="TEAM-RELIABILITY",
        version="3.1",
        created_at="2026-02-28",
        entity_ids=["SYS-CNC-07", "TEAM-RELIABILITY", "EMP-001"],
        content="""MAINTENANCE LOG: DOC-023
ASSET: SYS-CNC-07 (DMG Mori 5-Axis Milling Center, Bay-4B)
LEAD ENGINEER: Dr. Kenji Sato (EMP-001)

LOG ENTRIES:
- 2025-08-15: Complete replacement of front hybrid ceramic angular contact ball bearings (Set #HBC-7014).
- 2025-11-20: High-pressure coolant nozzle alignment and Chiller 02 flow rate balancing.
- 2026-02-28: Minor acoustic anomaly detected in high-RPM harmonics (24,000 RPM range). Thermocouple telemetry on front ceramic bearing showed intermittent +4°C offset relative to rear bearing. Scheduled for full vibration spectrum inspection on 2026-03-05."""
    ),

    Document(
        id="DOC-031",
        title="Project Gamma (Project C) System Architecture and Tooling Dependency Specification",
        doc_type="Specification",
        classification=ClassificationLevel.INTERNAL,
        owner_team="TEAM-AERO-ENG",
        version="2.0",
        created_at="2025-09-01",
        entity_ids=["PRJ-GAMMA", "SYS-CNC-07", "TEAM-AERO-ENG", "EMP-003", "CUST-AERO-GLOBAL"],
        content="""TECHNICAL SPECIFICATION: DOC-031
PROJECT: Project Gamma (Internal code: Project C - Commercial Turbofan Blisk Milling)
DIRECTOR: Marcus Vance (EMP-003)

SYSTEM DEPENDENCIES:
1. Primary Milling Cell: SYS-CNC-07 is the sole certified 5-axis machine capable of achieving the required 3.5-micron contour accuracy on Inconel-718 turbine blade root serrations.
2. Risk Impact: Any unplanned stoppage of SYS-CNC-07 creates an immediate critical path halt for Project C. No secondary machine has achieved AS9100 tooling qualification.
3. Thermal Sensitivity: Dimensional tolerance is extremely sensitive to spindle thermal growth. Thermal excursions above 68°C cause dimensional drift up to 12 microns, exceeding allowable blade aerodynamic tolerances (+/- 3.5 microns)."""
    ),

    Document(
        id="DOC-041",
        title="Manufacturing Incident Escalation Protocol & SLA Policy",
        doc_type="Policy Document",
        classification=ClassificationLevel.INTERNAL,
        owner_team="TEAM-MFG-OPS",
        version="1.5",
        created_at="2025-04-12",
        entity_ids=["POL-ESCAL-02", "INC-104", "TEAM-MFG-OPS", "TEAM-RELIABILITY"],
        content="""POLICY SPECIFICATION: DOC-041 / POL-ESCAL-02
TITLE: Plant Incident Classification and Severity SLA Hierarchy
AUTHOR: Elena Rostova (EMP-002)

SEVERITY 2 (CRITICAL PRODUCTION LINE HALT):
- Definition: Any machine stoppage on critical path assets (e.g. SYS-CNC-07) affecting active delivery projects.
- Notification SLA: Mandatory automated page to Maintenance Lead (EMP-001) and affected Project Directors within 15 minutes.
- Containment Action: Responsible operations team must confirm machine halt and lock work in progress within 30 minutes."""
    ),

    Document(
        id="DOC-055",
        title="Production Safety Procedure: Critical Thermal Runaway & High-Speed Spindle Protection",
        doc_type="SOP",
        classification=ClassificationLevel.INTERNAL,
        owner_team="TEAM-SAFETY",
        version="5.0",
        created_at="2025-01-20",
        entity_ids=["POL-SAFE-01", "SYS-CNC-07", "TEAM-SAFETY", "EMP-006"],
        content="""SAFETY STANDARD: DOC-055
TITLE: High-Speed Spindle Thermal Trip & Lockout Procedures
DIRECTOR: Sarah Jenkins (EMP-006)

CRITICAL MANDATES:
1. Spindle thermal trip interlocks on Siemens S7-1500 (SYS-PLC-88) must never be bypassed under operating load.
2. In the event of spindle bearing temperature exceeding 68°C (Incident 104 conditions), emergency shutdown is automated. Manual restart is strictly prohibited until a certified Level-2 Safety Clearance is signed by EHS."""
    ),

    Document(
        id="DOC-062",
        title="Turbine Blade Aerodynamic Tolerance and Quality Inspection Criteria",
        doc_type="Specification",
        classification=ClassificationLevel.INTERNAL,
        owner_team="TEAM-QUALITY",
        version="2.4",
        created_at="2025-08-14",
        entity_ids=["PRJ-GAMMA", "SYS-OPT-09", "TEAM-QUALITY", "EMP-004"],
        content="""QUALITY PROTOCOL: DOC-062
TITLE: In-Process & Post-Machining CMM Inspection Requirements for Blisk Blades
QA LEAD: Aoi Tanaka (EMP-004)

TOLERANCE SPECIFICATIONS:
1. Leading edge profile tolerance: +/- 0.0035 mm (+/- 3.5 microns).
2. Inspection Procedure: 100% volumetric laser coordinate measuring on Laser Metrology Scanner 09 (SYS-OPT-09).
3. Non-Conformance Containment: If a machine undergoes a thermal excursion (such as Incident 104 on CNC-07), all parts produced during the preceding 4-hour production window must be quarantined."""
    ),

    Document(
        id="DOC-FURN-05",
        title="Project Delta Superalloy Induction Sintering Operational Specification",
        doc_type="Specification",
        classification=ClassificationLevel.INTERNAL,
        owner_team="TEAM-AERO-ENG",
        version="1.8",
        created_at="2025-10-05",
        entity_ids=["PRJ-DELTA", "SYS-FURN-05", "TEAM-AERO-ENG"],
        content="""PROJECT DELTA SPECIFICATION: DOC-FURN-05
TITLE: Single-Crystal Superalloy Sintering Dependencies
DIRECTOR: Marcus Vance (EMP-003) / Lead Engineer: Aoi Tanaka (EMP-004)

1. SYSTEM DEPENDENCY:
Project Delta single-crystal superalloy turbine vane blanks depend directly on Induction Furnace 05 (SYS-FURN-05) for high-vacuum thermal sintering at 1650°C and argon atmosphere homogenization.

2. PROCESS QUALIFICATION:
Induction Furnace 05 is the sole qualified thermal processing unit with AS9100 vacuum integrity qualification for Project Delta sintering cycles."""
    ),

    Document(
        id="DOC-ZETA-01",
        title="Project Zeta Metrology Rig System Specification",
        doc_type="Specification",
        classification=ClassificationLevel.INTERNAL,
        owner_team="TEAM-QUALITY",
        version="1.2",
        created_at="2025-11-15",
        entity_ids=["PRJ-ZETA", "SYS-OPT-09", "TEAM-QUALITY"],
        content="""PROJECT ZETA SPECIFICATION: DOC-ZETA-01
TITLE: Inline Laser Metrology Scanner Dependency
QA LEAD: Aoi Tanaka (EMP-004)

1. SYSTEM DEPENDENCY:
Project Zeta is the enterprise inline metrology validation initiative. It depends directly on Laser Metrology Scanner 09 (SYS-OPT-09) to perform sub-micron optical roughness and dimensional verification on aerospace blisks and vanes."""
    ),

    Document(
        id="DOC-EPSILON-01",
        title="Project Epsilon Cleanroom Optical Cell Deployment Specification",
        doc_type="Specification",
        classification=ClassificationLevel.INTERNAL,
        owner_team="TEAM-AUTOMATION",
        version="1.1",
        created_at="2025-12-01",
        entity_ids=["PRJ-EPSILON", "SYS-ARM-02", "SYS-AIR-04", "TEAM-AUTOMATION"],
        content="""PROJECT EPSILON SPECIFICATION: DOC-EPSILON-01
TITLE: Cleanroom Robotic Assembly Dependencies
LEAD: Takeshi Yamamoto (EMP-005)

1. SYSTEM DEPENDENCY:
Project Epsilon requires Robotic Transfer Arm 02 (SYS-ARM-02) for 6-axis optical payload handling and operates strictly inside the clean air envelope maintained by Cleanroom HEPA Unit 04 (SYS-AIR-04)."""
    ),

    Document(
        id="DOC-ALPHA-01",
        title="Project Alpha Precision Titanium Machining Architecture",
        doc_type="Specification",
        classification=ClassificationLevel.INTERNAL,
        owner_team="TEAM-MFG-OPS",
        version="2.0",
        created_at="2025-07-20",
        entity_ids=["PRJ-ALPHA", "SYS-CNC-07", "SYS-COOL-02", "TEAM-MFG-OPS"],
        content="""PROJECT ALPHA SPECIFICATION: DOC-ALPHA-01
TITLE: Autonomous Precision Titanium Line Tooling
LEAD: Elena Rostova (EMP-002)

1. SYSTEM DEPENDENCY:
Project Alpha utilizes CNC-07 (SYS-CNC-07) and CNC-04 for high-speed titanium aero-structure milling, supported by chilled coolant delivery from Chiller 02 (SYS-COOL-02)."""
    ),

    Document(
        id="CONTRACT-22",
        title="Aerospace Prime Master Supply Agreement - Customer X",
        doc_type="Contract",
        classification=ClassificationLevel.RESTRICTED,
        owner_team="TEAM-EXECUTIVE",
        version="FINAL-EXEC",
        created_at="2025-01-01",
        entity_ids=["CUST-AERO-GLOBAL", "PRJ-GAMMA", "TEAM-EXECUTIVE", "CONTRACT-22"],
        content="""STRICTLY CONFIDENTIAL & PROPRIETARY CONTRACT: CONTRACT-22
PARTIES: Global Aerospace Dynamics (Customer X) & Precision Aero Machining Ltd.
CLEARANCE: RESTRICTED (Executive Clearance Only)

1. COMMERCIAL PRICING & VOLUME:
- Project Gamma Turbine Blisks unit delivery price: $42,500 per unit.
- Annual committed procurement volume: 240 units ($10.2M contract value).

2. LIQUIDATED DAMAGES & PENALTY CLAUSES:
- Any delivery delay exceeding 14 calendar days incurs liquidated damages of $15,000 per day.
- Unplanned machine downtime causing line stoppage must not be disclosed to customer engineering without Executive VP approval.
- All pricing terms and volume margins are strictly trade secrets."""
    ),

    Document(
        id="PAYROLL-2026",
        title="Engineering Executive Compensation & Specialist Bonus Allocations 2026",
        doc_type="Compensation Matrix",
        classification=ClassificationLevel.RESTRICTED,
        owner_team="TEAM-EXECUTIVE",
        version="1.0",
        created_at="2026-01-01",
        entity_ids=["TEAM-EXECUTIVE", "EMP-001", "EMP-002", "EMP-003", "PAYROLL-2026"],
        content="""STRICTLY RESTRICTED HR COMPENSATION: PAYROLL-2026
Classification: RESTRICTED (Executive Clearance Only)

Executive Base Salaries and Annual Retention Bonuses:
- Dr. Kenji Sato (EMP-001): Base $210,000, Retention Equity $45,000.
- Elena Rostova (EMP-002): Base $165,000, Operational KPI Bonus $30,000.
- Marcus Vance (EMP-003): Base $225,000, Delivery Bonus $50,000."""
    ),

    Document(
        id="DOC-SYS-CNC07-SPEC",
        title="CNC-07 5-Axis Milling Center Technical Data Sheet & Thermal Limits",
        doc_type="Specification",
        classification=ClassificationLevel.INTERNAL,
        owner_team="TEAM-RELIABILITY",
        version="1.0",
        created_at="2025-06-01",
        entity_ids=["SYS-CNC-07", "TEAM-RELIABILITY", "TEAM-MFG-OPS"],
        content="""TECHNICAL SPECIFICATION: DOC-SYS-CNC07-SPEC
Machine Model: DMG Mori DMU 80 eVo (Asset: SYS-CNC-07)
Location: Bay-4B, Main Machining Hall
Spindle: HSK-A63 24,000 RPM Motor Spindle with integrated thermistor array.
Critical Limits: Spindle jacket liquid cooling nominal 18°C. Bearing temperature trip point: 68.0°C.
Operating Projects: CNC-07 is actively assigned to Project Gamma (Project C) for turbine blisk serrations and Project Alpha for titanium frames."""
    ),

    Document(
        id="DOC-ORG-CHART",
        title="Organizational Directory and Escalation Roster 2026",
        doc_type="Directory",
        classification=ClassificationLevel.PUBLIC,
        owner_team="TEAM-MFG-OPS",
        version="2.0",
        created_at="2026-01-01",
        entity_ids=["TEAM-MFG-OPS", "TEAM-RELIABILITY", "TEAM-AERO-ENG", "TEAM-QUALITY", "TEAM-SAFETY", "TEAM-AUTOMATION"],
        content="""ORGANIZATIONAL ROSTER: DOC-ORG-CHART
Plant Departments:
- Manufacturing Operations (TEAM-MFG-OPS): Lead Elena Rostova (EMP-002)
- Site Reliability (TEAM-RELIABILITY): Lead Dr. Kenji Sato (EMP-001)
- Aerospace Engineering (TEAM-AERO-ENG): Lead Marcus Vance (EMP-003)
- Quality Assurance (TEAM-QUALITY): Lead Aoi Tanaka (EMP-004)
- Safety & EHS (TEAM-SAFETY): Lead Sarah Jenkins (EMP-006)
- Automation Core (TEAM-AUTOMATION): Lead Takeshi Yamamoto (EMP-005)"""
    )
]


# ---------------------------------------------------------------------------
# 4. PRE-INDEXED EVIDENCE CHUNKS
# ---------------------------------------------------------------------------

SEED_EVIDENCE_CHUNKS: list[EvidenceChunk] = [
    # CNC-07 & Incident 104 Evidence
    EvidenceChunk(
        id="EVID-017-01",
        doc_id="SOP-017",
        doc_title="CNC High-Speed Spindle Temperature Incident Response & Shutdown Procedure",
        doc_type="SOP",
        classification=ClassificationLevel.INTERNAL,
        source_type="SOP",
        relevant_entities=["SYS-CNC-07", "INC-104", "TEAM-MFG-OPS", "TEAM-SAFETY", "SOP-017"],
        supported_relationships=["SYS-CNC-07:AFFECTED_BY:INC-104", "INC-104:RELATED_TO:SOP-017"],
        relevance_score=0.95,
        excerpt="Critical Level 2 (Thermal Excursion Alarm / Incident 104): Spindle temperature >= 68.0°C requires immediate controlled feed hold, cutting tool retraction on Z-axis, and 60-second ramp-down to complete spindle shutdown."
    ),
    EvidenceChunk(
        id="EVID-017-02",
        doc_id="SOP-017",
        doc_title="CNC High-Speed Spindle Temperature Incident Response & Shutdown Procedure",
        doc_type="SOP",
        classification=ClassificationLevel.INTERNAL,
        source_type="SOP",
        relevant_entities=["SYS-CNC-07", "INC-104", "TEAM-RELIABILITY", "EMP-001", "SOP-017"],
        supported_relationships=["INC-104:ESCALATED_TO:TEAM-RELIABILITY", "EMP-001:MEMBER_OF:TEAM-RELIABILITY"],
        relevance_score=0.90,
        excerpt="The machine must be tagged OUT-OF-SERVICE. Dr. Kenji Sato (EMP-001) or designated reliability engineer must perform dial indicator runout and acoustic vibration spectrum analysis before restarting production."
    ),
    EvidenceChunk(
        id="EVID-023-01",
        doc_id="DOC-023",
        doc_title="CNC-07 Spindle Maintenance History & Ceramic Bearing Overhaul Log",
        doc_type="Maintenance Log",
        classification=ClassificationLevel.INTERNAL,
        source_type="Maintenance Log",
        relevant_entities=["SYS-CNC-07", "TEAM-RELIABILITY", "EMP-001", "DOC-023"],
        supported_relationships=["SYS-CNC-07:MAINTAINED_BY:TEAM-RELIABILITY"],
        relevance_score=0.82,
        excerpt="2026-02-28: Minor acoustic anomaly detected in high-RPM harmonics (24,000 RPM range). Thermocouple telemetry on front ceramic bearing showed intermittent +4°C offset relative to rear bearing."
    ),
    EvidenceChunk(
        id="EVID-CNC07-SPEC-01",
        doc_id="DOC-SYS-CNC07-SPEC",
        doc_title="CNC-07 5-Axis Milling Center Technical Data Sheet & Thermal Limits",
        doc_type="Specification",
        classification=ClassificationLevel.INTERNAL,
        source_type="Specification",
        relevant_entities=["SYS-CNC-07", "PRJ-GAMMA", "PRJ-ALPHA", "TEAM-MFG-OPS"],
        supported_relationships=["PRJ-GAMMA:DEPENDS_ON:SYS-CNC-07", "PRJ-ALPHA:DEPENDS_ON:SYS-CNC-07"],
        relevance_score=0.92,
        excerpt="SYS-CNC-07 is a 5-Axis DMG Mori DMU 80 eVo high-speed milling center with HSK-A63 24,000 RPM spindle in Bay-4B. It is actively assigned to Project Gamma (Project C) for turbine blisk serrations and Project Alpha for titanium frames."
    ),

    # Project Gamma (Project C) Evidence
    EvidenceChunk(
        id="EVID-031-01",
        doc_id="DOC-031",
        doc_title="Project Gamma (Project C) System Architecture and Tooling Dependency Specification",
        doc_type="Specification",
        classification=ClassificationLevel.INTERNAL,
        source_type="Specification",
        relevant_entities=["PRJ-GAMMA", "SYS-CNC-07", "TEAM-AERO-ENG", "EMP-003", "DOC-031"],
        supported_relationships=["PRJ-GAMMA:DEPENDS_ON:SYS-CNC-07"],
        relevance_score=0.94,
        excerpt="Project Gamma (Project C) manufactures 5th-generation turbine blades. SYS-CNC-07 is the sole certified 5-axis milling center with high-speed micro-milling qualification. Any stoppage on SYS-CNC-07 directly halts Project C."
    ),
    EvidenceChunk(
        id="EVID-031-02",
        doc_id="DOC-031",
        doc_title="Project Gamma (Project C) System Architecture and Tooling Dependency Specification",
        doc_type="Specification",
        classification=ClassificationLevel.INTERNAL,
        source_type="Specification",
        relevant_entities=["PRJ-GAMMA", "SYS-CNC-07", "INC-104", "DOC-031"],
        supported_relationships=["PRJ-GAMMA:DEPENDS_ON:SYS-CNC-07", "SYS-CNC-07:AFFECTED_BY:INC-104"],
        relevance_score=0.88,
        excerpt="Because thermal spindle expansion above 68°C exceeds allowable 3-micron blade profile tolerance, all turbine blades milled during thermal excursion must be quarantined for 100% CMM laser inspection."
    ),

    # Escalation & Safety Policies
    EvidenceChunk(
        id="EVID-041-01",
        doc_id="DOC-041",
        doc_title="Manufacturing Incident Escalation Protocol & SLA Policy",
        doc_type="Policy Document",
        classification=ClassificationLevel.INTERNAL,
        source_type="Policy",
        relevant_entities=["POL-ESCAL-02", "INC-104", "TEAM-MFG-OPS", "TEAM-RELIABILITY", "DOC-041"],
        supported_relationships=["INC-104:GOVERNED_BY:POL-ESCAL-02"],
        relevance_score=0.80,
        excerpt="Severity 2 Incident Response SLA < 30 minutes. Mandatory alert to Maintenance Lead (EMP-001) and affected Project Directors. Responsible operations team must confirm machine halt and lock work in progress."
    ),
    EvidenceChunk(
        id="EVID-055-01",
        doc_id="DOC-055",
        doc_title="Production Safety Procedure: Critical Thermal Runaway & High-Speed Spindle Protection",
        doc_type="SOP",
        classification=ClassificationLevel.INTERNAL,
        source_type="SOP",
        relevant_entities=["POL-SAFE-01", "SYS-CNC-07", "TEAM-SAFETY", "DOC-055", "SOP-017"],
        supported_relationships=["SOP-017:GOVERNED_BY:POL-SAFE-01", "SOP-017:OWNED_BY:TEAM-SAFETY"],
        relevance_score=0.85,
        excerpt="When spindle housing temperature exceeds 68°C, the controller MUST initiate an emergency controlled shutdown sequence. Overriding thermal interlocks without formal authorization from TEAM-SAFETY is strictly prohibited."
    ),
    EvidenceChunk(
        id="EVID-062-01",
        doc_id="DOC-062",
        doc_title="Turbine Blade Aerodynamic Tolerance and Quality Inspection Criteria",
        doc_type="Specification",
        classification=ClassificationLevel.INTERNAL,
        source_type="Specification",
        relevant_entities=["PRJ-GAMMA", "SYS-OPT-09", "TEAM-QUALITY", "DOC-062"],
        supported_relationships=["DOC-062:USES:SYS-OPT-09"],
        relevance_score=0.78,
        excerpt="Leading edge profile tolerance is +/- 0.0035 mm (+/- 3.5 microns). Blades produced during thermal excursion must undergo 100% laser interferometer CMM scan on SYS-OPT-09."
    ),

    # Project Delta Evidence (Documentary Evidence)
    EvidenceChunk(
        id="EVID-DELTA-01",
        doc_id="DOC-FURN-05",
        doc_title="Project Delta Superalloy Induction Sintering Operational Specification",
        doc_type="Specification",
        classification=ClassificationLevel.INTERNAL,
        source_type="Specification",
        relevant_entities=["PRJ-DELTA", "SYS-FURN-05", "TEAM-AERO-ENG"],
        supported_relationships=["PRJ-DELTA:DEPENDS_ON:SYS-FURN-05"],
        relevance_score=0.95,
        excerpt="Project Delta single-crystal superalloy turbine vane blanks depend directly on Induction Furnace 05 (SYS-FURN-05) for high-vacuum thermal sintering at 1650°C and argon atmosphere homogenization."
    ),

    # Project Zeta Evidence (Documentary Evidence)
    EvidenceChunk(
        id="EVID-ZETA-01",
        doc_id="DOC-ZETA-01",
        doc_title="Project Zeta Metrology Rig System Specification",
        doc_type="Specification",
        classification=ClassificationLevel.INTERNAL,
        source_type="Specification",
        relevant_entities=["PRJ-ZETA", "SYS-OPT-09", "TEAM-QUALITY"],
        supported_relationships=["PRJ-ZETA:DEPENDS_ON:SYS-OPT-09"],
        relevance_score=0.95,
        excerpt="Project Zeta is the enterprise inline metrology validation initiative. It depends directly on Laser Metrology Scanner 09 (SYS-OPT-09) to perform sub-micron optical roughness and dimensional verification on aerospace blisks and vanes."
    ),

    # Project Epsilon Evidence
    EvidenceChunk(
        id="EVID-EPSILON-01",
        doc_id="DOC-EPSILON-01",
        doc_title="Project Epsilon Cleanroom Optical Cell Deployment Specification",
        doc_type="Specification",
        classification=ClassificationLevel.INTERNAL,
        source_type="Specification",
        relevant_entities=["PRJ-EPSILON", "SYS-ARM-02", "SYS-AIR-04", "TEAM-AUTOMATION"],
        supported_relationships=["PRJ-EPSILON:DEPENDS_ON:SYS-ARM-02", "PRJ-EPSILON:DEPENDS_ON:SYS-AIR-04"],
        relevance_score=0.92,
        excerpt="Project Epsilon requires Robotic Transfer Arm 02 (SYS-ARM-02) for 6-axis optical payload handling and operates strictly inside the clean air envelope maintained by Cleanroom HEPA Unit 04 (SYS-AIR-04)."
    ),

    # Project Alpha Evidence
    EvidenceChunk(
        id="EVID-ALPHA-01",
        doc_id="DOC-ALPHA-01",
        doc_title="Project Alpha Precision Titanium Machining Architecture",
        doc_type="Specification",
        classification=ClassificationLevel.INTERNAL,
        source_type="Specification",
        relevant_entities=["PRJ-ALPHA", "SYS-CNC-07", "SYS-COOL-02", "TEAM-MFG-OPS"],
        supported_relationships=["PRJ-ALPHA:DEPENDS_ON:SYS-CNC-07", "SYS-CNC-07:DEPENDS_ON:SYS-COOL-02"],
        relevance_score=0.90,
        excerpt="Project Alpha utilizes CNC-07 (SYS-CNC-07) and CNC-04 for high-speed titanium aero-structure milling, supported by chilled coolant delivery from Chiller 02 (SYS-COOL-02)."
    ),

    # Restricted Evidence
    EvidenceChunk(
        id="EVID-CTR22-01",
        doc_id="CONTRACT-22",
        doc_title="Aerospace Prime Master Supply Agreement - Customer X",
        doc_type="Contract",
        classification=ClassificationLevel.RESTRICTED,
        source_type="Contract",
        relevant_entities=["CUST-AERO-GLOBAL", "PRJ-GAMMA", "TEAM-EXECUTIVE", "CONTRACT-22"],
        supported_relationships=["CUST-AERO-GLOBAL:DOCUMENTED_BY:CONTRACT-22"],
        relevance_score=0.98,
        excerpt="Project Gamma Turbine Blisks unit delivery price: $42,500 per unit. Delivery delays exceeding 14 calendar days incur liquidated damages of $15,000 per day."
    ),
    EvidenceChunk(
        id="EVID-SAL01-01",
        doc_id="PAYROLL-2026",
        doc_title="Engineering Executive Compensation & Specialist Bonus Allocations 2026",
        doc_type="Compensation Matrix",
        classification=ClassificationLevel.RESTRICTED,
        source_type="Compensation",
        relevant_entities=["TEAM-EXECUTIVE", "EMP-001", "EMP-002", "EMP-003", "PAYROLL-2026"],
        supported_relationships=["PAYROLL-2026:OWNED_BY:TEAM-EXECUTIVE"],
        relevance_score=0.90,
        excerpt="Executive base salaries and retention packages: Dr. Kenji Sato $210,000 base, Elena Rostova $165,000 base, Marcus Vance $225,000 base."
    )
]
