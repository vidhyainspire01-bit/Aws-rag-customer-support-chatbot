Enterprise Hybrid-Search RAG on AWS – Implementation Guide

A step-by-step, DevOps-ready implementation guide to build a production-grade Hybrid-Search Retrieval-Augmented Generation (RAG) System on AWS.
This README provides architecture context, phase-by-phase build instructions, and references for deploying a secure, scalable enterprise RAG stack using AWS-native components (OpenSearch, SageMaker, Bedrock, EKS, Glue, Aurora, MWAA, KMS, IAM, CloudWatch, etc.).

Table of Contents

Executive Summary

Project Goals & Success Metrics

Architecture Overview

Prerequisites & Accounts

Implementation Phases

Phase 0 — Repo & IaC Skeleton

Phase 1 — VPC, EKS, IAM, KMS (Terraform)

Phase 2 — OpenSearch & Aurora

Phase 3 — Ingest Pipeline (Glue/MWAA, Textract, Comprehend)

Phase 4 — Embedding Service (SageMaker) & Indexing

Phase 5 — Hybrid Retriever (EKS Service)

Phase 6 — Reranker (SageMaker Endpoint)

Phase 7 — Generator Adapter + Verifier (Bedrock / SageMaker LLM)

Phase 8 — CI/CD, Helm, Containers

Phase 9 — Monitoring, Logging, Metrics

Phase 10 — Testing, Evaluation, Rollout

Operational Concerns

Retention, Improvement Loop

Future Enhancements

License

Executive Summary

This project provides a full enterprise reference implementation of a Hybrid-Search RAG system running on AWS.
The design supports:

Multi-modal ingestion (PDFs, docs, structured/unstructured text)

Vector + keyword + semantic hybrid retrieval

LLM-based reasoning, verification, and grounding

Scalable, containerized infrastructure on EKS

Terraform-based IaC

Strong governance, security, and observability built-in

Project Goals & Success Metrics
Goals

Build a secure, production-ready RAG stack for enterprise use cases

Ensure hybrid-search performance using OpenSearch + vector embeddings

Provide retriever-reranker-generator pipeline with verifiers

Maintain infra-as-code (Terraform) and complete CI/CD

Make the system extensible for multi-department knowledge domains

Success Metrics

Retrieval latency < 300 ms for hybrid search

Overall RAG response < 2 seconds

Embedding throughput > 500 docs/min

Precision & grounding score > 90%

Full auditability (CloudWatch, OpenSearch logs, Bedrock guardrails)

Architecture Overview

Core components include:

AWS VPC + EKS → scalable compute for retriever, orchestrators, adapters

Amazon OpenSearch → keyword + vector + hybrid search

Aurora PostgreSQL → metadata, versioning, ingestion catalog

SageMaker → embedding models, reranker, custom LLMs

AWS Bedrock → generator (Jurassic2, Claude, Titan, Llama3)

Glue, MWAA, Textract, Comprehend → ingestion pipeline

KMS, IAM, Secrets Manager → enterprise security controls

CI/CD with GitHub Actions / CodePipeline

CloudWatch, X-Ray, OpenTelemetry → monitoring & tracing

Prerequisites & Accounts

AWS Account with admin access

Terraform v1.5+

kubectl, helm

Docker

AWS CLI v2

Access to SageMaker + Bedrock models

GitHub repository / CodeCommit for CI/CD

Folder structure recommendation:

/infra
  /terraform
/app
  /retriever
  /embedder
  /reranker
  /generator-adapter
  /verifier
/ingestion
/charts
/docs

Implementation Phases
Phase 0: Repo & IaC Skeleton

Create mono-repo / multi-repo structure

Add Terraform modules for networking, EKS, OpenSearch

Add Helm charts for all microservices

Add GitHub Actions workflows

Phase 1: VPC, EKS, IAM, KMS (Terraform)

Deploy:

VPC with public/private subnets

EKS cluster + nodegroups

KMS keys for OpenSearch, S3, Aurora

IAM roles for service accounts (IRSA)

Private link/VPC endpoints where needed

Phase 2: OpenSearch & Aurora

Create OpenSearch cluster (vector-enabled)

Create Aurora Postgres metadata DB

Secure via VPC-only, SSL, KMS encryption

Add dashboards & slow query logs

Phase 3: Ingest Pipeline

Using Glue/MWAA, Textract, Comprehend:

Document extraction

Chunking

Metadata tagging

Store embeddings in OpenSearch

Audit info stored in Aurora

Phase 4: Embedding Service (SageMaker) & Indexing

Deploy embedding model (e.g., bge-large, Titan-Embed, InstructorXL)

Create indexing lambda/cron job

Provide gRPC/REST endpoint for embedding

Phase 5: Hybrid Retriever (EKS)

Implements:

BM25 keyword search

Dense vector search

Sparse search (optional)

Fusion logic (RRR, weighted rank fusion)

Phase 6: Reranker (SageMaker Endpoint)

Use cross-encoder (bge-reranker, Cohere-rerank, Titan-reranker)

Returns final top-k context chunks

Phase 7: Generator Adapter + Verifier

Calls Bedrock (Claude, Titan, Llama3)

Adds grounding context

Applies safety filters

Final answer verified by:

grounding check

JSON schema validator

business guardrails

Phase 8: CI/CD, Helm, Containers

Docker builds for all services

Helm charts

GitHub Actions:

lint → test → build → deploy

Environment promotion: Dev → QA → Prod

Phase 9: Monitoring, Logging, Metrics

Observability stack:

CloudWatch Logs + Metrics

Traces via X-Ray / OpenTelemetry

OpenSearch Dashboards

Prometheus/Grafana (optional)

Cost breakdown dashboards

Phase 10: Testing, Evaluation, Rollout

Tests:

Retrieval accuracy

LLM hallucination tests

Load tests

Security posture (IAM, KMS, isolation)

Rollout:

Blue/green or canary deployments

Domain-based routing

Automated rollback

Operational Concerns

Data governance (classification, PII handling)

Model versioning

Ingestion versioning

Multi-tenant architecture

Guardrails & policy filtering

Backup & recovery

Retention & Improvement Loop

Continuous improvement using:

User feedback logs

Query-answer drift detection

Content freshness monitoring

Automatic re-indexing pipelines

Future Enhancements

Multi-agent workflows

Auto-evaluation pipelines

LangGraph orchestration

Distributed vector store integration

Cross-region HA deployment

License

MIT License (or your enterprise license)
