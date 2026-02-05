"""
Canonical Tender Schema and Pydantic Models
DO NOT CHANGE without updating dependent systems
"""

import json
from pydantic import BaseModel, Field, field_validator
from typing import List, Any
from datetime import datetime


# Canonical Schema Definition (for reference and prompt injection)
TENDER_SCHEMA = {
    "tender_meta": {
        "tender_id": "",
        "tender_title": "",
        "portal": "",
        "department": "",
        "issuing_authority": "",
        "country": "",
        "state": "",
        "funded_project": "",
        "funding_agency": ""
    },
    "scope_of_work": {
        "description": "",
        "deliverables": "",
        "quantity": "",
        "technical_specifications": "",
        "location": "",
        "duration": ""
    },
    "key_dates": {
        "publication_date": "",
        "bid_start": "",
        "bid_end": "",
        "pre_bid_meeting_date": "",
        "pre_bid_meeting_location": "",
        "technical_bid_opening": "",
        "financial_bid_opening": "",
        "contract_start": "",
        "bid_validity": "",
        "project_duration": ""
    },
    "eligibility_snapshot": {
        "who_can_bid": "",
        "experience_required": "",
        "turnover_requirement": "",
        "minimum_years_in_business": "",
        "local_content_requirement": "",
        "msme_startup_exemption": "",
        "consortium_or_jv_allowed": "",
        "international_bidders_allowed": "",
        "specific_licenses_required": "",
        "past_performance_requirement": ""
    },
    "financial_requirements": {
        "emd": "",
        "emd_exemption": "",
        "tender_fee": "",
        "performance_security": "",
        "retention_money": "",
        "payment_terms": "",
        "advance_payment": "",
        "mobilization_advance": ""
    },
    "documents_required": [],
    "legal_and_risk_clauses": {
        "blacklisting_clause": "",
        "arbitration_clause": "",
        "mediation_clause": "",
        "liquidated_damages": "",
        "force_majeure": "",
        "termination_clause": "",
        "warranty_period": "",
        "special_restrictions": ""
    },
    "vendor_decision_hint": {
        "eligible_if": "",
        "not_eligible_if": "",
        "key_risks": "",
        "competitive_advantage_if": ""
    },
    "additional_important_information": {
        "evaluation_criteria": "",
        "selection_method": "",
        "price_preference": "",
        "special_conditions": "",
        "contact_information": "",
        "clarification_process": "",
        "other_critical_info": ""
    },
    "pre_qualification_requirement": ""
}


def coerce_to_string(v: Any) -> str:
    """Helper to convert lists or dicts to strings for pydantic validation."""
    if isinstance(v, list):
        return "; ".join([str(i) for i in v])
    if isinstance(v, dict):
        return json.dumps(v)
    return str(v) if v is not None else ""


class BaseTenderModel(BaseModel):
    """Base model with string coercion for all fields to handle LLM format variability."""
    @field_validator("*", mode="before")
    @classmethod
    def validate_strings(cls, v: Any) -> Any:
        # We only want to coerce fields that are actually defined as str in the model
        # but for simplicity in a generic 'tender' context, we'll let the specific models handle it
        # or just coerce everything that isn't already the right type if it's meant to be a string.
        return v


class TenderMeta(BaseTenderModel):
    tender_id: str = Field(default="")
    tender_title: str = Field(default="")
    portal: str = Field(default="")
    department: str = Field(default="")
    issuing_authority: str = Field(default="")
    country: str = Field(default="")
    state: str = Field(default="")
    funded_project: str = Field(default="")
    funding_agency: str = Field(default="")

    @field_validator("*", mode="before")
    @classmethod
    def coerce_all(cls, v: Any) -> str:
        return coerce_to_string(v)


class ScopeOfWork(BaseTenderModel):
    description: str = Field(default="")
    deliverables: str = Field(default="")
    quantity: str = Field(default="")
    technical_specifications: str = Field(default="")
    location: str = Field(default="")
    duration: str = Field(default="")

    @field_validator("*", mode="before")
    @classmethod
    def coerce_all(cls, v: Any) -> str:
        return coerce_to_string(v)


class KeyDates(BaseTenderModel):
    publication_date: str = Field(default="")
    bid_start: str = Field(default="")
    bid_end: str = Field(default="")
    pre_bid_meeting_date: str = Field(default="")
    pre_bid_meeting_location: str = Field(default="")
    technical_bid_opening: str = Field(default="")
    financial_bid_opening: str = Field(default="")
    contract_start: str = Field(default="")
    bid_validity: str = Field(default="")
    project_duration: str = Field(default="")

    @field_validator("*", mode="before")
    @classmethod
    def coerce_all(cls, v: Any) -> str:
        return coerce_to_string(v)


class EligibilitySnapshot(BaseTenderModel):
    who_can_bid: str = Field(default="")
    experience_required: str = Field(default="")
    turnover_requirement: str = Field(default="")
    minimum_years_in_business: str = Field(default="")
    local_content_requirement: str = Field(default="")
    msme_startup_exemption: str = Field(default="")
    consortium_or_jv_allowed: str = Field(default="")
    international_bidders_allowed: str = Field(default="")
    specific_licenses_required: str = Field(default="")
    past_performance_requirement: str = Field(default="")

    @field_validator("*", mode="before")
    @classmethod
    def coerce_all(cls, v: Any) -> str:
        return coerce_to_string(v)


class FinancialRequirements(BaseTenderModel):
    emd: str = Field(default="")
    emd_exemption: str = Field(default="")
    tender_fee: str = Field(default="")
    performance_security: str = Field(default="")
    retention_money: str = Field(default="")
    payment_terms: str = Field(default="")
    advance_payment: str = Field(default="")
    mobilization_advance: str = Field(default="")

    @field_validator("*", mode="before")
    @classmethod
    def coerce_all(cls, v: Any) -> str:
        return coerce_to_string(v)


class LegalAndRiskClauses(BaseTenderModel):
    blacklisting_clause: str = Field(default="")
    arbitration_clause: str = Field(default="")
    mediation_clause: str = Field(default="")
    liquidated_damages: str = Field(default="")
    force_majeure: str = Field(default="")
    termination_clause: str = Field(default="")
    warranty_period: str = Field(default="")
    special_restrictions: str = Field(default="")

    @field_validator("*", mode="before")
    @classmethod
    def coerce_all(cls, v: Any) -> str:
        return coerce_to_string(v)


class VendorDecisionHint(BaseTenderModel):
    eligible_if: str = Field(default="")
    not_eligible_if: str = Field(default="")
    key_risks: str = Field(default="")
    competitive_advantage_if: str = Field(default="")

    @field_validator("*", mode="before")
    @classmethod
    def coerce_all(cls, v: Any) -> str:
        return coerce_to_string(v)


class AdditionalInformation(BaseTenderModel):
    evaluation_criteria: str = Field(default="")
    selection_method: str = Field(default="")
    price_preference: str = Field(default="")
    special_conditions: str = Field(default="")
    contact_information: str = Field(default="")
    clarification_process: str = Field(default="")
    other_critical_info: str = Field(default="")

    @field_validator("*", mode="before")
    @classmethod
    def coerce_all(cls, v: Any) -> str:
        return coerce_to_string(v)


class TenderSummary(BaseModel):
    """Complete tender eligibility summary - Root Model"""
    tender_meta: TenderMeta
    scope_of_work: ScopeOfWork
    key_dates: KeyDates
    eligibility_snapshot: EligibilitySnapshot
    financial_requirements: FinancialRequirements
    documents_required: List[str] = Field(default_factory=list)
    legal_and_risk_clauses: LegalAndRiskClauses
    vendor_decision_hint: VendorDecisionHint
    additional_important_information: AdditionalInformation
    pre_qualification_requirement: str = Field(default="", description="GeM Portal specific pre-qualification requirement as single formatted string - only for GeM tenders")

    @field_validator("pre_qualification_requirement", mode="before")
    @classmethod
    def coerce_prequalification(cls, v: Any) -> str:
        return coerce_to_string(v)

    @field_validator("documents_required", mode="before")
    @classmethod
    def validate_docs(cls, v: Any) -> List[str]:
        if isinstance(v, str):
            return [v]
        if isinstance(v, list):
            return [str(i) for i in v]
        return []
