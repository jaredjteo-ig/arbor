"""Domain specialist agents for the HR advisory pipeline.

Eight specialists, each scoped to a single Singapore HR regulatory domain:
  - EmploymentActAgent  (Employment Act)
  - CPFAgent            (Central Provident Fund)
  - ForeignManpowerAgent (Employment of Foreign Manpower Act)
  - FairEmploymentAgent (TAFEP / Workplace Fairness Legislation)
  - TaxAgent            (IRAS employer tax obligations)
  - WSHAgent            (Workplace Safety and Health Act)
  - PDPAAgent           (Personal Data Protection Act)
  - ComplianceAgent     (Cross-domain compliance checker)
"""

from hr_advisory.agents.specialists.compliance import ComplianceAgent
from hr_advisory.agents.specialists.cpf import CPFAgent
from hr_advisory.agents.specialists.employment_act import EmploymentActAgent
from hr_advisory.agents.specialists.fair_employment import FairEmploymentAgent
from hr_advisory.agents.specialists.foreign_manpower import ForeignManpowerAgent
from hr_advisory.agents.specialists.pdpa import PDPAAgent
from hr_advisory.agents.specialists.tax import TaxAgent
from hr_advisory.agents.specialists.wsh import WSHAgent

__all__ = [
    "EmploymentActAgent",
    "CPFAgent",
    "ForeignManpowerAgent",
    "FairEmploymentAgent",
    "TaxAgent",
    "WSHAgent",
    "PDPAAgent",
    "ComplianceAgent",
]
