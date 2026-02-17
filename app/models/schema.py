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
        "funding_agency": "",
        "organization_address": "",
        "organization_telephone": "",
        "organization_email": "",
        "organization_fax": "",
        "tender_document_date": "",
        "submission_instructions": "",
        "type_of_bid": "",
        "item_category": "",
        "total_quantity": "",
        "boq_title": ""
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
        "project_duration": "",
        "date_and_time_of_issue": "",
        "due_date_and_time_of_submission": ""
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
        "past_performance_requirement": "",
        "bidder_technical_infrastructure": "",
        "oem_turnover_requirement": "",
        "mse_relaxation": "",
        "startup_relaxation": "",
        "detailed_pre_qualification_criteria": ""
    },
    "financial_requirements": {
        "emd": "",
        "emd_exemption": "",
        "tender_fee": "",
        "performance_security": "",
        "retention_money": "",
        "payment_terms": "",
        "advance_payment": "",
        "mobilization_advance": "",
        "epbg_details": ""
    },
    "documents_required": [],
    "online_submission_documents": [],
    "offline_submission_documents": [],
    "legal_and_risk_clauses": {
        "blacklisting_clause": "",
        "arbitration_clause": "",
        "mediation_clause": "",
        "liquidated_damages": "",
        "force_majeure": "",
        "termination_clause": "",
        "warranty_period": "",
        "special_restrictions": "",
        "rejection_of_bid": "",
        "splitting_of_work": "",
        "mii_purchase_preference": "",
        "mse_purchase_preference": ""
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
        "detailed_evaluation_scoring_criteria": "",
        "buyer_added_atc": "",
        "technical_clarification_time": "",
        "evaluation_method": "",
        "bid_to_ra_enabled": "",
        "other_critical_info": ""
    },
    "pre_qualification_requirement": "",
    "executive_summary": ""
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
    funded_project: str = Field(default="", description="Name of the funded project if applicable")
    funding_agency: str = Field(default="", description="Name of the agency funding the project")
    organization_address: str = Field(default="", description="Address of the issuing organization (Corporate/Registered Office)")
    organization_telephone: str = Field(default="", description="Telephone number of the organization")
    organization_email: str = Field(default="", description="Email address of the organization")
    organization_fax: str = Field(default="", description="Fax number of the organization")
    tender_document_date: str = Field(default="", description="Date mentioned on the tender document (e.g. Dated: DD/MM/YYYY)")
    submission_instructions: str = Field(default="", description="Specific instructions for bid submission (e.g., envelope labels, offline address)")
    type_of_bid: str = Field(default="", description="Type of bid (e.g., Single Packet, Two Packet)")
    item_category: str = Field(default="", description="Main product category from GeM Bid Document")
    total_quantity: str = Field(default="", description="Total quantity of items required")
    boq_title: str = Field(default="", description="BOQ Title from GeM document")

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
    date_and_time_of_issue: str = Field(default="", description="Exact label from CPPP tenders: 'Date & time of issue'")
    due_date_and_time_of_submission: str = Field(default="", description="Exact label from CPPP tenders: 'Due Date & time of Submission'")

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
    bidder_technical_infrastructure: str = Field(default="", description="Minimum technical infrastructure required at bidder's end (e.g., Computer, Broadband, DSC)")
    oem_turnover_requirement: str = Field(default="", description="OEM Average Turnover Requirement")
    mse_relaxation: str = Field(default="", description="MSE Relaxation for Experience/Turnover")
    startup_relaxation: str = Field(default="", description="Startup Relaxation for Experience/Turnover")
    detailed_pre_qualification_criteria: str = Field(default="", description="Extended details from Pre-Qualification/Eligibility Criteria section")

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
    epbg_details: str = Field(default="")
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
    rejection_of_bid: str = Field(default="", description="Conditions for rejection of bid (See Section 4.6)")
    splitting_of_work: str = Field(default="", description="Whether the organization reserves the right to split the work among bidders")

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
    detailed_evaluation_scoring_criteria: str = Field(default="", description="Detailed points from Evaluation/Scoring criteria section")
    buyer_added_atc: str = Field(default="", description="Buyer Added Bid Specific Terms and Conditions (ATC)")
    technical_clarification_time: str = Field(default="", description="Time allowed for Technical Clarifications during technical evaluation")
    evaluation_method: str = Field(default="", description="GeM Evaluation Method (Total vs Item-wise)")
    bid_to_ra_enabled: str = Field(default="", description="Whether Reverse Auction is enabled")
    other_critical_info: str = Field(default="")

    @field_validator("*", mode="before")
    @classmethod
    def coerce_all(cls, v: Any) -> str:
        return coerce_to_string(v)


class TenderSummary(BaseModel):
    """Complete tender eligibility summary - Root Model"""
    tender_meta: TenderMeta = Field(default_factory=lambda: TenderMeta())
    scope_of_work: ScopeOfWork = Field(default_factory=lambda: ScopeOfWork())
    key_dates: KeyDates = Field(default_factory=lambda: KeyDates())
    eligibility_snapshot: EligibilitySnapshot = Field(default_factory=lambda: EligibilitySnapshot())
    financial_requirements: FinancialRequirements = Field(default_factory=lambda: FinancialRequirements())
    documents_required: List[str] = Field(default_factory=list)
    online_submission_documents: List[str] = Field(default_factory=list, description="Documents to be submitted ONLINE (scanned/pdf)")
    offline_submission_documents: List[str] = Field(default_factory=list, description="Documents to be submitted OFFLINE (physical/hardcopy)")
    legal_and_risk_clauses: LegalAndRiskClauses = Field(default_factory=lambda: LegalAndRiskClauses())
    vendor_decision_hint: VendorDecisionHint = Field(default_factory=lambda: VendorDecisionHint())
    additional_important_information: AdditionalInformation = Field(default_factory=lambda: AdditionalInformation())
    pre_qualification_requirement: str = Field(default="", description="GeM Portal specific pre-qualification requirement as single formatted string - only for GeM tenders")
    executive_summary: str = Field(default="", description="Brief high-level summary of the entire tender")
    external_links: List[str] = Field(default_factory=list, description="All external URLs/Hyperlinks found in the document")

    @field_validator("pre_qualification_requirement", mode="before")
    @classmethod
    def coerce_prequalification(cls, v: Any) -> str:
        return coerce_to_string(v)

    @field_validator("documents_required", "online_submission_documents", "offline_submission_documents", mode="before")
    @classmethod
    def coerce_documents_required(cls, v: Any) -> List[str]:
        if isinstance(v, str):
            return [v]
        if isinstance(v, list):
            return [str(i) for i in v]
        return []
