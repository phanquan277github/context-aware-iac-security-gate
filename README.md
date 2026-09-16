# Context-Aware IaC Security Gate

A research prototype for contextual security-risk prioritization
of Generative-AI-generated Terraform in DevSecOps pipelines.

## Research Focus

This project investigates whether contextual information can improve
the prioritization of Terraform security findings compared with
severity-only prioritization, and whether machine-learning models
can further improve contextual prioritization.

## Scope

- AWS
- Terraform
- Checkov
- Random Forest Regressor
- XGBoost Regressor
- GitHub Actions

## Architecture

Generative AI
    ↓
Terraform Scenarios
    ↓
Terraform Validation
    ↓
Checkov
    ↓
Finding Normalization
    ↓
Context & Feature Extraction
    ↓
ML Risk Prioritization
    ↓
Security Gate
